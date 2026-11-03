/*
 * Functional check of the built dashboard (dashboard/index.html) in headless Chromium.
 *
 *   node tests/dashboard_check.js            (from the repository root)
 *
 * Drives every view control and tab, the filters, search, hash navigation and stale
 * stored settings, and fails on: page errors, "undefined"/"NaN"/"[object" text, map
 * markers without a colour, missing explanations for change layers in "Today",
 * horizontal overflow at phone width.
 */
const path = require("path");
const { chromium } = require("playwright");

const PAGE = "file://" + path.resolve(__dirname, "..", "dashboard", "index.html");
const BAD_TEXT = /undefined|NaN|\[object|Infinity/;
const failures = [];
const fail = (where, msg) => failures.push(`${where}: ${msg}`);

async function check(p, where) {
  const res = await p.evaluate(() => {
    const txt = sel => (document.querySelector(sel) || {}).innerText || "";
    const areas = ["#kstrip", "#pane", "#rank", "#legend", "#map-sub", "#mapsel", "#s-name", "#s-chips", "#fsum", "#cnt"];
    const text = Object.fromEntries(areas.map(a => [a, txt(a)]));
    const visible = [...document.querySelectorAll("#sites circle")].filter(c => !c.classList.contains("off"));
    const fills = visible.map(c => c.style.fill);
    const note = document.querySelector("#mapnote");
    return { text, fills, noteShown: note && !note.hidden, sel: document.querySelectorAll("#sites circle:not(.off)").length };
  });
  for (const [area, t] of Object.entries(res.text)) if (BAD_TEXT.test(t)) fail(where, `bad text in ${area}: ${t.match(BAD_TEXT)[0]}`);
  if (res.fills.some(f => !f)) fail(where, "a visible marker has no fill colour");
  return res;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(PAGE + "#SVQ");
  await page.waitForTimeout(400);

  const click = sel => page.click(sel);
  const layers = await page.$$eval("#ctl-layer option", os => os.map(o => o.value));
  const changeLayers = ["d_days30", "warming"];
  let states = 0;

  // 1. Every view combination x every tab (one site)
  for (const scen of ["ssp245", "ssp585"])
    for (const period of ["hist", "2040", "2050"])
      for (const yt of ["typical", "hot"])
        for (const expo of ["in", "sun"])
          for (const hall of expo === "in" ? ["0", "2", "4"] : ["0"]) {
            await click(`#ctl-scen button[data-v="${scen}"]`);
            await click(`#ctl-period button[data-v="${period}"]`);
            await click(`#ctl-yt button[data-v="${yt}"]`);
            await click(`#ctl-expo button[data-v="${expo}"]`);
            if (expo === "in") await click(`#ctl-hall button[data-v="${hall}"]`);
            for (const layer of layers) {
              await page.selectOption("#ctl-layer", layer);
              const where = `${scen}/${period}/${yt}/${expo}${expo === "in" ? "+" + hall : ""}/${layer}`;
              const r = await check(page, where);
              const isChange = changeLayers.includes(layer);
              if (period === "hist" && isChange && !r.noteShown) fail(where, "change layer in Today without explanation");
              if (!(period === "hist" && isChange) && r.noteShown) fail(where, "explanation shown when values exist");
              if (!(period === "hist" && isChange) && r.fills.some(f => f === "rgb(201, 196, 211)")) fail(where, "grey (no value) marker");
              states++;
            }
            for (const tab of ["summary", "data", "temp", "stress", "about"]) {
              await click(`.tabs button[data-tab="${tab}"]`);
              await check(page, `${scen}/${period}/${yt}/${expo}+${hall}/tab:${tab}`);
              states++;
            }
          }

  // 1b. Year = Hot: charts show the hot reference year adjusted to 2040 / 2050
  await click('#ctl-yt button[data-v="hot"]');
  await click('#ctl-period button[data-v="2050"]');
  await click('.tabs button[data-tab="temp"]');
  let paneText = await page.$eval("#pane", e => e.innerText);
  if (!/weather in 2050/.test(paneText)) fail("hot charts", "temperature tab does not show the hot year adjusted to 2050");
  await click('#ctl-yt button[data-v="typical"]');
  paneText = await page.$eval("#pane", e => e.innerText);
  if (/weather in 2050/.test(paneText)) fail("typical charts", "typical view still shows the hot-year series");

  // 1c. Summary tab: comparison year pickers and consistency with the Data summary table
  await click('.tabs button[data-tab="summary"]');
  await page.selectOption('select[data-cmp="cmpB"]', "hotref");
  paneText = await page.$eval("#pane", e => e.innerText);
  if (!/Today, hot year \(\d{4} as it happened\) against Today, typical year/.test(paneText)) fail("summary pickers", "comfort sentence does not follow the picked years");
  const opts = await page.$$eval('select[data-cmp="cmpB"] option', os => os.map(o => o.textContent));
  if (opts.length !== 6 || !opts.some(t => /^2040, hot year/.test(t)) || !opts.some(t => /^2050, hot year/.test(t))) fail("summary pickers", `year options: ${opts.join(" | ")}`);
  if ((await page.$$("#pane .sc:first-child svg text.val")).length !== 6) fail("summary bars", "expected six year bars");
  await page.selectOption('select[data-cmp="cmpA"]', "hotref");
  paneText = await page.$eval("#pane", e => e.innerText);
  if (!/Pick two different years/.test(paneText)) fail("summary pickers", "same year twice not handled");
  const barToday = await page.$eval("#pane .sc svg .val", e => e.textContent.split(" h")[0]);
  await click('.tabs button[data-tab="data"]');
  const tableToday = await page.$$eval("#pane table tbody tr", trs => {
    const tr = trs.find(t => /^Working hours above WBGT 28/.test(t.querySelector("th").innerText));
    return tr.querySelectorAll("td")[0].innerText.trim();
  });
  if (barToday !== tableToday) fail("summary vs data", `today bar ${barToday} h, table ${tableToday} h`);

  // 1d. Worker profiles: every profile x exposure renders on every tab, and a lower reference never gives fewer hours
  const profs = await page.$$eval("#ctl-prof option", os => os.map(o => o.value));
  if (profs.length !== 4) fail("profiles", `expected 4 worker profiles, got ${profs.length}`);
  const tileHours = async () => Number((await page.$eval("#kstrip .kstat:nth-child(2) .val", e => e.childNodes[0].textContent)).replace(/[^0-9.]/g, ""));
  for (const [expo, hall] of [["in", "0"], ["in", "4"], ["sun", "0"]]) {
    await click(`#ctl-expo button[data-v="${expo}"]`);
    if (expo === "in") await click(`#ctl-hall button[data-v="${hall}"]`);
    const hoursBy = {};
    for (const prof of profs) {
      await page.selectOption("#ctl-prof", prof);
      for (const tab of ["summary", "data", "stress", "about"]) {
        await click(`.tabs button[data-tab="${tab}"]`);
        await check(page, `profile ${prof}/${expo}+${hall}/tab:${tab}`);
        states++;
      }
      hoursBy[prof] = await tileHours();
    }
    if (!(hoursBy.light <= hoursBy.moderate && hoursBy.moderate <= hoursBy.ppe && hoursBy.ppe <= hoursBy.heavy))
      fail(`profiles ${expo}+${hall}`, `hours not ordered light <= moderate <= ppe <= heavy: ${JSON.stringify(hoursBy)}`);
  }
  await page.selectOption("#ctl-prof", "moderate");
  await click('#ctl-expo button[data-v="in"]');
  await click('#ctl-hall button[data-v="0"]');

  // 2. Every site, every tab (default view)
  const ids = await page.$$eval("#sites circle", cs => cs.map(c => c.dataset.id));
  for (const id of ids) {
    await page.click(`#sites circle[data-id="${id}"]`, { force: true });
    for (const tab of ["summary", "data", "temp", "stress", "about"]) {
      await click(`.tabs button[data-tab="${tab}"]`);
      const r = await check(page, `site ${id}/${tab}`);
      states++;
    }
    const hash = await page.evaluate(() => location.hash);
    if (hash !== "#" + id) fail(`site ${id}`, `hash is ${hash}`);
  }

  // 3. Filters: only one country, none, reset
  await click('.tabs button[data-tab="summary"]');
  const only = await page.$$eval("#tree .fo.l1", fos => fos.map(f => f.dataset.key));
  for (const key of only) {
    await page.hover(`#tree .fo[data-key="${key}"]`);
    await page.click(`#tree .fo[data-key="${key}"] .only`);
    const r = await check(page, `filter only ${key}`);
    const expected = await page.$eval(`#tree .fo[data-key="${key}"]`, f => f.dataset.ids.split(",").length);
    if (r.sel !== expected) fail(`filter only ${key}`, `${r.sel} markers visible, expected ${expected}`);
  }
  await page.click('#tree .fo[data-key="EU"]');            // toggle all on
  await page.click('#tree .fo[data-key="EU"]');            // all off
  let r = await check(page, "filter none");
  if (r.sel !== 0) fail("filter none", `${r.sel} markers still visible`);
  const rankText = await page.$eval("#rank", el => el.innerText);
  if (!/No sites in view/.test(rankText)) fail("filter none", "no empty-state message in ranking");
  await page.click("#freset");
  r = await check(page, "filter reset");
  if (r.sel !== ids.length) fail("filter reset", `${r.sel} markers visible after reset`);

  // 4. Search, including text that looks like HTML
  await page.fill("#fsearch", "<img src=x onerror=alert(1)>");
  const injected = await page.$("#sres img");
  if (injected) fail("search", "search text was inserted as HTML");
  await page.fill("#fsearch", "tou");
  await page.click("#sres button");
  if ((await page.$eval("#s-name", e => e.textContent)) !== "Toulouse (Blagnac)") fail("search", "selecting a result did not open Toulouse");

  // 5. Stale settings from older versions + bad hash
  await page.evaluate(() => { for (const [k, v] of Object.entries({ "cr-tab": "bogus", "cr-layer": "op_wbgt_prov_degree_hours_gt_base", "cr-expo": "in0", "cr-hall": "7", "cr-period": "2099", "cr-prof": "bogus" })) localStorage.setItem(k, v); });
  await page.goto(PAGE + "#NOPE");
  await page.waitForTimeout(300);
  r = await check(page, "stale settings");
  const name = await page.$eval("#s-name", e => e.textContent);
  if (!name) fail("stale settings", "site card empty");
  await page.evaluate(() => localStorage.clear());

  // 6. Desktop one-screen layout: the page itself must not scroll at common laptop / monitor sizes
  for (const [w, h] of [[1440, 900], [1920, 1080], [1280, 760]]) {
    const d = await browser.newPage({ viewport: { width: w, height: h } });
    d.on("pageerror", e => errors.push(`${w}x${h}: ` + e.message));
    await d.goto(PAGE + "#SVQ");
    await d.waitForTimeout(300);
    for (const tab of ["summary", "data", "temp", "stress", "about"]) {
      await d.click(`.tabs button[data-tab="${tab}"]`);
      const over = await d.evaluate(() => [document.documentElement.scrollHeight - document.documentElement.clientHeight,
        document.documentElement.scrollWidth - document.documentElement.clientWidth]);
      if (over[0] > 1 || over[1] > 0) fail(`desktop ${w}x${h}/${tab}`, `page scrolls (vertical ${over[0]}px, horizontal ${over[1]}px)`);
      const mapH = await d.$eval("#map", e => e.getBoundingClientRect().height);
      if (mapH < 140) fail(`desktop ${w}x${h}`, `map only ${Math.round(mapH)}px tall`);
    }
    await d.close();
  }

  // 7. Phone width: no sideways scrolling
  const phone = await browser.newPage({ viewport: { width: 390, height: 860 } });
  phone.on("pageerror", e => errors.push("phone: " + e.message));
  await phone.goto(PAGE);
  await phone.waitForTimeout(300);
  for (const tab of ["summary", "data", "temp", "stress", "about"]) {
    await phone.click(`.tabs button[data-tab="${tab}"]`);
    const over = await phone.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (over > 0) fail(`phone/${tab}`, `page scrolls sideways by ${over}px`);
  }

  for (const e of errors) fail("console", e);
  await browser.close();
  console.log(`${states} states checked, ${failures.length} problems`);
  for (const f of failures.slice(0, 40)) console.log(" - " + f);
  process.exit(failures.length ? 1 : 0);
})();
