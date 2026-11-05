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
    const areas = ["#kstrip", "#pane", "#rank", "#legend", "#mapsel", "#s-name", "#fsum", "#cnt"];
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
      for (const yt of ["typical", "hot", "extreme"])
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
  // Year = Extreme (D62): the extreme reference year in today's climate and adjusted to 2050
  await click('#ctl-yt button[data-v="extreme"]');
  paneText = await page.$eval("#pane", e => e.innerText);
  if (!/Extreme year \d{4} \(today's climate\)/.test(paneText) || !/weather in 2050/.test(paneText)) fail("extreme charts", "temperature tab does not show the extreme year");
  await click('#ctl-yt button[data-v="typical"]');
  paneText = await page.$eval("#pane", e => e.innerText);
  if (/weather in 2050/.test(paneText)) fail("typical charts", "typical view still shows the hot-year series");

  // 1b'. The working-time tile follows the filter: with one site in view it shows that site's own hours
  const oneSite = await page.evaluate(() => { const keep = new Set(S.sel), was = S.site; S.sel = new Set(["TLS"]); afterFilter();
    const tile = document.querySelector("#kstrip .kstat:nth-child(2) .val").childNodes[0].textContent.trim();
    const own = fmt(kpiVal("TLS", EXPO().hours)[0]); S.sel = keep; afterFilter(); selectSite(was); return [tile, own]; });
  if (oneSite[0] !== oneSite[1]) fail("tile follows filter", `one site in view: tile ${oneSite[0]} h, site ${oneSite[1]} h`);
  // 1c. Summary tab: comfort-shift year pickers and the hours chart (consistent with the Indicators table)
  await click('.tabs button[data-tab="summary"]');
  await page.selectOption('select[data-cmp="cmpB"]', "hotref");
  paneText = await page.$eval("#pane", e => e.innerText);
  if (!/Today, hot year against Today, typical year/.test(paneText)) fail("comfort pickers", "comfort sentence does not follow the picked years");
  const opts = await page.$$eval('select[data-cmp="cmpB"] option', os => os.map(o => o.textContent));
  if (opts.length !== 9 || !opts.some(t => /^2040, hot year/.test(t)) || !opts.some(t => /^2050, extreme year/.test(t))) fail("comfort pickers", `year options: ${opts.join(" | ")}`);
  await page.selectOption('select[data-cmp="cmpA"]', "hotref");
  paneText = await page.$eval("#pane", e => e.innerText);
  if (!/Pick two different years/.test(paneText)) fail("comfort pickers", "same year twice not handled");
  if ((await page.$$("#pane .sc:first-child svg text.val")).length !== 9) fail("summary bars", "expected nine year bars");
  // charts are drawn at their pixel size: SVG text must not be scaled up, and charts fill the panel
  for (const tab of ["summary", "temp", "stress"]) {
    await click(`.tabs button[data-tab="${tab}"]`);
    const fit = await page.$$eval("#pane svg.chart", ss => ss.map(e => [e.getBoundingClientRect().width / e.viewBox.baseVal.width, e.getBoundingClientRect().width / document.querySelector("#pane").clientWidth]));
    if (fit.some(([sc]) => sc > 1.02)) fail(`${tab} charts`, `chart scaled up: ${fit.map(f => f[0].toFixed(2)).join(", ")}`);
    if (fit.some(([, share]) => share < 0.8)) fail(`${tab} charts`, `chart narrower than the panel: ${fit.map(f => f[1].toFixed(2)).join(", ")}`);
  }
  await click('.tabs button[data-tab="summary"]');
  const barToday = await page.$eval("#pane .sc svg .val", e => e.textContent.split(" h")[0]);
  await click('.tabs button[data-tab="data"]');
  const tableToday = await page.$$eval("#pane table tbody tr", trs => {
    /* textContent: the table sits in a collapsed "Exact values" section */
    const tr = trs.find(t => /^Working hours above WBGT \d+ °C/.test(t.querySelector("th").textContent) && !/acclimatised workforce/.test(t.querySelector("th").textContent));
    return tr.querySelector("td").firstChild.textContent.trim();
  });
  if (barToday !== tableToday) fail("summary vs data", `today bar ${barToday} h, table ${tableToday} h`);
  for (const yt of ["typical", "hot", "extreme"]) {
    await click(`#ctl-yt button[data-v="${yt}"]`);
    await click('.tabs button[data-tab="data"]');
    const ind = await page.$$eval("#pane table tbody tr", trs => { const tr = trs.find(t => /^Working hours above WBGT \d+ °C/.test(t.querySelector("th").textContent) && !/acclimatised workforce/.test(t.querySelector("th").textContent));
      return [...tr.querySelectorAll("td")].map(td => td.firstChild.textContent.trim()); });
    await click('.tabs button[data-tab="stress"]');
    const st = await page.$$eval("#pane table tbody tr", trs => { const tr = trs.find(t => /^All working hours .* WBGT above \d+ °C$/.test(t.querySelector("th").textContent));
      return tr ? [...tr.querySelectorAll("td")].map(td => td.firstChild.textContent.trim()) : []; });
    if (ind.join("|") !== st.join("|")) fail(`heat stress vs indicators (${yt})`, `stress ${st.join(" / ")} vs indicators ${ind.join(" / ")}`);
  }
  await click('#ctl-yt button[data-v="typical"]');

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

  // 1e. Process lens (D66): every view x run mode x process layer x tab; monotonic in the limit, hall gain and run mode;
  //     summary bars agree with the Indicators table; presets, stepper, free entry and clamping
  await click('#ctl-lens button[data-v="proc"]');
  const procLayers = await page.$$eval("#ctl-layer option", os => os.map(o => o.value));
  if (!procLayers.includes("proc_hours") || procLayers.includes("worker_days")) fail("process lens", `map layers: ${procLayers.join(", ")}`);
  if (await page.isVisible("#ctl-prof") || !(await page.isVisible("#ctl-lim"))) fail("process lens", "worker controls shown or limit hidden");
  if ((await page.$eval('.tabs button[data-tab="stress"]', e => e.textContent)) !== "Process") fail("process lens", "tab not renamed to Process");
  for (const scen of ["ssp245", "ssp585"])
    for (const period of ["hist", "2040", "2050"])
      for (const yt of ["typical", "hot", "extreme"])
          for (const hall of ["0", "4"]) {
            await click(`#ctl-scen button[data-v="${scen}"]`); await click(`#ctl-period button[data-v="${period}"]`);
            await click(`#ctl-yt button[data-v="${yt}"]`); await click(`#ctl-hall button[data-v="${hall}"]`);
            for (const layer of procLayers) {
              await page.selectOption("#ctl-layer", layer);
              const where = `proc ${scen}/${period}/${yt}+${hall}/${layer}`, rr = await check(page, where), isChange = ["d_proc_hours", "warming"].includes(layer);
              if (period === "hist" && isChange && !rr.noteShown) fail(where, "change layer in Today without explanation");
              if (!(period === "hist" && isChange) && rr.fills.some(f => f === "rgb(201, 196, 211)")) fail(where, "grey (no value) marker");
              states++;
            }
            for (const tab of ["summary", "data", "temp", "stress", "about"]) {
              await click(`.tabs button[data-tab="${tab}"]`);
              await check(page, `proc ${scen}/${period}/${yt}+${hall}/tab:${tab}`);
              states++;
            }
          }
  await click('#ctl-scen button[data-v="ssp245"]'); await click('#ctl-period button[data-v="2050"]'); await click('#ctl-yt button[data-v="typical"]');
  await click('#ctl-hall button[data-v="0"]');
  const limVal = () => page.$eval("#ctl-lim", e => Number(e.value));
  await page.selectOption("#ctl-proc", "paint");
  if (await limVal() !== 35) fail("presets", `paint preset gives ${await limVal()} °C`);
  const procHours = await tileHours();
  // raising the limit never adds downtime; a warmer hall never removes any
  let prev = Infinity;
  for (const d of [-5, 1, 1, 1, 1, 1]) {
    for (let k = 0; k < Math.abs(d) * 2; k++) await click(`.stepper button[data-d="${d < 0 ? "-0.5" : "0.5"}"]`);
    const h = await tileHours();
    if (d > 0 && h > prev) fail("limit stepper", `downtime rose from ${prev} to ${h} h as the limit went up`);
    prev = h;
  }
  await click('.stepper button[data-d="0.5"]');   // 35.5 °C matches no preset
  if (await page.$eval("#ctl-proc", e => e.value) !== "custom") fail("limit stepper", "preset not switched to custom after stepping");
  await page.selectOption("#ctl-proc", "paint");
  await click('#ctl-hall button[data-v="4"]');
  if (await tileHours() < procHours) fail("hall gain", "a warmer hall gave less downtime");
  await click('#ctl-hall button[data-v="0"]');
  if (await page.$("#ctl-run")) fail("process lens", "the running-hours toggle is back (D70: one running window for both lenses)");
  for (const [typed, want] of [["33.4", 33.5], ["99", 45], ["5", 20]]) {
    await page.fill("#ctl-lim", typed); await page.press("#ctl-lim", "Enter"); await page.$eval("#ctl-lim", e => e.blur());
    if (await limVal() !== want) fail("limit entry", `typed ${typed}, limit ${await limVal()}, expected ${want}`);
  }
  await page.selectOption("#ctl-proc", "paint");
  // the histograms keep their bars when the limit moves: same positions and heights, only the colouring changes;
  // at a half-degree limit the bin it falls in is split in two
  await click('.tabs button[data-tab="summary"]');
  const bars = () => page.$$eval("#pane .sc:nth-child(2) svg.chart rect", rs => rs.map(r => `${(+r.getAttribute("x")).toFixed(1)}:${(+r.getAttribute("y")).toFixed(1)}:${(+r.getAttribute("height")).toFixed(1)}`));
  const b35 = await bars();
  await click('.stepper button[data-d="0.5"]'); await click('.stepper button[data-d="0.5"]');
  const b36 = await bars();
  if (b35.join("|") !== b36.join("|")) fail("histogram", "bars change size or position when the limit moves by 1 °C");
  await click('.stepper button[data-d="-0.5"]');
  if ((await bars()).length !== b35.length + 3) fail("histogram", "a half-degree limit should split one bin in each of the three panels");
  const tilesVsHist = await page.evaluate(() => {
    const tiles = [...document.querySelectorAll("#pane .dtstrip .dt .v")].slice(0, 3).map(e => e.childNodes[0].textContent.trim());
    const hist = [...document.querySelectorAll("#pane .sc:nth-child(2) svg.chart text.val")].map(e => e.textContent.replace(" h above", "").trim());
    return [tiles, hist]; });
  if (tilesVsHist[0].join("|") !== tilesVsHist[1].join("|")) fail("histogram vs tiles", `tiles ${tilesVsHist[0].join(" / ")}, histograms ${tilesVsHist[1].join(" / ")}`);
  await page.selectOption("#ctl-proc", "paint");
  // the summary's today bar equals the Indicators table (same 11-year statistic)
  await click('.tabs button[data-tab="summary"]');
  const procBar = await page.$eval("#pane .sc svg .val", e => e.textContent.split(" h")[0]);
  if ((await page.$$("#pane .sc:first-child svg text.val")).length !== 9) fail("process summary", "expected nine year bars");
  if ((await page.$$("#pane .dtstrip .dt")).length !== 4) fail("process summary", "downtime strip should have four tiles");
  await click('.tabs button[data-tab="data"]');
  const procTable = await page.$$eval("#pane table tbody tr", trs => trs.find(t => /^Downtime hours/.test(t.querySelector("th").textContent)).querySelector("td").firstChild.textContent.trim());
  if (procBar !== procTable) fail("process summary vs data", `today bar ${procBar} h, table ${procTable} h`);
  for (const tab of ["summary", "temp", "stress"]) {
    await click(`.tabs button[data-tab="${tab}"]`);
    const fit = await page.$$eval("#pane svg.chart", ss => ss.map(e => e.getBoundingClientRect().width / e.viewBox.baseVal.width));
    if (fit.some(sc => sc > 1.02)) fail(`process ${tab} charts`, `chart scaled up: ${fit.map(f => f.toFixed(2)).join(", ")}`);
  }
  for (const id of ["XFW", "TLS", "SVQ"]) {   // cool, temperate and hot sites
    await page.click(`#sites circle[data-id="${id}"]`, { force: true });
    for (const tab of ["summary", "data", "stress"]) { await click(`.tabs button[data-tab="${tab}"]`); await check(page, `proc site ${id}/${tab}`); states++; }
  }
  // the URL carries the whole view and wins over remembered settings
  await page.goto(PAGE + "?lens=work&scen=ssp585&period=2040&yt=extreme&expo=sun&prof=heavy&tab=data#TLS"); await page.waitForTimeout(300);
  const st2 = await page.evaluate(() => [...["ctl-scen", "ctl-period", "ctl-yt", "ctl-expo"].map(i => document.querySelector(`#${i} button[aria-pressed="true"]`).dataset.v), document.querySelector("#ctl-prof").value, document.querySelector('.tabs button[aria-selected="true"]').dataset.tab, location.hash]);
  if (st2.join(",") !== "ssp585,2040,extreme,sun,heavy,data,#TLS") fail("url state", `opened as ${st2.join(",")}`);
  await click('#ctl-period button[data-v="2050"]');
  if (!(await page.evaluate(() => location.search)).includes("period=2050")) fail("url state", "the URL does not follow a change");
  if (!(await page.isVisible("#copylink"))) fail("copy link", "button hidden on an unframed page");
  // shareable link and back to the worker lens
  await page.goto(PAGE + "?lens=proc&lim=32#TLS"); await page.waitForTimeout(300);
  if (await limVal() !== 32 || !(await page.isVisible("#ctl-lim"))) fail("link", "?lens=proc&lim=32 not applied");
  await click('#ctl-lens button[data-v="work"]');
  if (!(await page.isVisible("#ctl-prof")) || await page.isVisible("#ctl-lim")) fail("worker lens", "controls not restored");
  const wl = await page.$eval("#ctl-layer", e => [e.value, [...e.options].map(o => o.value)]);
  if (wl[0].includes("proc") || !wl[1].includes("worker_days") || wl[1].some(v => v.includes("proc"))) fail("worker lens", `map layers not restored: ${wl[0]} of ${wl[1].join(", ")}`);
  if ((await page.$eval('.tabs button[data-tab="stress"]', e => e.textContent)) !== "Heat stress") fail("worker lens", "tab label not restored");
  await page.goto(PAGE + "#SVQ"); await page.waitForTimeout(300);

  // 1f. Group view: with no site picked the panel shows the sites in view (Europe), totals agree with the tile, clicking off a
  //     site clears the name tag, a country row filters to that country, a single-site filter opens that site
  await page.goto(PAGE); await page.waitForTimeout(400);
  if (!(await page.$eval("#s-name", e => e.textContent)).startsWith("Europe")) fail("group view", "does not start at Europe without a site in the link");
  if (!(await page.isHidden("#mapsel"))) fail("group view", "a name tag shows with no site picked");
  for (const tab of ["summary", "data", "temp", "stress", "about"]) { await click(`.tabs button[data-tab="${tab}"]`); await check(page, `group/tab:${tab}`); states++; }
  await click('.tabs button[data-tab="summary"]');
  const gt = await page.evaluate(() => [document.querySelector("#kstrip .kstat:nth-child(2) .val").childNodes[0].textContent.trim(),
    document.querySelector("#pane table.grp tr.tot td:nth-child(4)").textContent.trim(), document.querySelectorAll('#pane table.grp tr[data-site]').length]);
  if (gt[0] !== gt[1]) fail("group view", `Europe total ${gt[1]} h does not match the tile ${gt[0]} h`);
  if (gt[2] !== 15) fail("group view", `site table has ${gt[2]} rows`);
  await page.click('#sites circle[data-id="TLS"]', { force: true });
  if ((await page.$eval("#s-name", e => e.textContent)) !== "Toulouse (Blagnac)" || await page.isHidden("#mapsel")) fail("deselect", "clicking a site did not open it");
  const mb = await page.$eval("#map", e => { const r = e.getBoundingClientRect(); return [r.left + 6, r.bottom - 6]; });
  await page.mouse.click(mb[0], mb[1]); await page.waitForTimeout(100);
  if (!(await page.isHidden("#mapsel")) || !(await page.$eval("#s-name", e => e.textContent)).startsWith("Europe")) fail("deselect", "clicking off a site did not clear the tag and return to Europe");
  await page.click('#sites circle[data-id="SVQ"]', { force: true }); await page.keyboard.press("Escape"); await page.waitForTimeout(100);
  if (!(await page.$eval("#s-name", e => e.textContent)).startsWith("Europe")) fail("deselect", "Esc did not clear the site");
  await page.click('#pane tr[data-country="ES"]'); await page.waitForTimeout(150);
  const es = await page.evaluate(() => [document.querySelector("#s-name").textContent, document.querySelectorAll('#pane table.grp tr[data-site]').length, document.querySelectorAll("#sites circle:not(.off)").length]);
  if (!es[0].startsWith("Spain") || es[1] !== 3 || es[2] !== 3) fail("country filter", `after clicking Spain: ${es.join(" / ")}`);
  for (const tab of ["summary", "data"]) { await click(`.tabs button[data-tab="${tab}"]`); await check(page, `group Spain/tab:${tab}`); states++; }
  await click('#ctl-lens button[data-v="proc"]'); await click('.tabs button[data-tab="summary"]'); await check(page, "group Spain/process"); states++;
  if ((await page.$$("#pane .dtstrip .dt")).length !== 4) fail("group view", "process lens: no downtime tiles for the group");
  const gh = await page.evaluate(() => [[...document.querySelectorAll("#pane .dtstrip .dt .v")].slice(0, 3).map(e => e.childNodes[0].textContent.trim()),
    [...document.querySelectorAll("#pane .sc svg.chart text.val")].filter(e => / h above$/.test(e.textContent)).map(e => e.textContent.replace(" h above", "").trim())]);
  if (gh[0].join("|") !== gh[1].join("|")) fail("group histograms", `tiles ${gh[0].join(" / ")}, histograms ${gh[1].join(" / ")}`);
  await click('#ctl-lens button[data-v="work"]');
  await page.evaluate(() => { S.sel = new Set(["GET"]); afterFilter(); });
  if ((await page.$eval("#s-name", e => e.textContent)) !== "Getafe") fail("country filter", "a one-site filter did not open that site");
  await page.goto(PAGE + "#SVQ"); await page.waitForTimeout(300);

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
  await page.evaluate(() => { for (const [k, v] of Object.entries({ "cr-tab": "bogus", "cr-layer": "op_wbgt_prov_degree_hours_gt_base", "cr-expo": "in0", "cr-hall": "7", "cr-period": "2099", "cr-prof": "bogus",
    "cr-lens": "proc", "cr-lim": "999", "cr-run": "night", "cr-proc": "bogus" })) localStorage.setItem(k, v); });
  await page.goto(PAGE + "#NOPE");
  await page.waitForTimeout(300);
  r = await check(page, "stale settings");
  const name = await page.$eval("#s-name", e => e.textContent);
  if (!name) fail("stale settings", "site card empty");
  await page.evaluate(() => localStorage.clear());

  // 6. Desktop one-screen layout: the page itself must not scroll at common laptop / monitor sizes
  for (const [w, h] of [[1440, 900], [1600, 900], [1920, 1080], [1500, 800], [1280, 760]]) {
    const d = await browser.newPage({ viewport: { width: w, height: h } });
    d.on("pageerror", e => errors.push(`${w}x${h}: ` + e.message));
    await d.goto(PAGE + (w === 1280 ? "?lens=proc" : "") + "#SVQ");
    await d.waitForTimeout(300);
    for (const tab of ["summary", "data", "temp", "stress", "about"]) {
      await d.click(`.tabs button[data-tab="${tab}"]`);
      const over = await d.evaluate(() => [document.documentElement.scrollHeight - document.documentElement.clientHeight,
        document.documentElement.scrollWidth - document.documentElement.clientWidth]);
      const oneScreen = w >= 1360 && h >= 820;   /* one-screen layout only where it fits (D56 relaxed) */
      if ((oneScreen && over[0] > 1) || over[1] > 0) fail(`desktop ${w}x${h}/${tab}`, `page scrolls (vertical ${over[0]}px, horizontal ${over[1]}px)`);
      const cut = await d.evaluate(() => { const box = document.querySelector(".mapbox").getBoundingClientRect();
        return [...document.querySelectorAll("#sites circle:not(.off)")].filter(c => { const q = c.getBoundingClientRect();
          return q.top < box.top - 0.5 || q.bottom > box.bottom + 0.5 || q.left < box.left - 0.5 || q.right > box.right + 0.5; }).map(c => c.dataset.id); });
      if (cut.length) fail(`desktop ${w}x${h}/${tab}`, `map markers outside the map: ${cut.join(", ")}`);
      const mapH = await d.$eval("#map", e => e.getBoundingClientRect().height);
      const vbW = await d.$eval("#map", e => e.getAttribute("viewBox"));
      await d.click(`#ctl-lens button[data-v="${await d.$eval('#ctl-lens button[aria-pressed="true"]', e => e.dataset.v) === "work" ? "proc" : "work"}"]`);
      await d.waitForTimeout(150);
      const vbP = await d.$eval("#map", e => e.getAttribute("viewBox"));
      if (vbW !== vbP) fail(`desktop ${w}x${h}/${tab}`, `map zoom changes with the lens: ${vbW} vs ${vbP}`);
      await d.click('#ctl-lens button[aria-pressed="false"]'); await d.waitForTimeout(100);
      if (mapH < (oneScreen ? 200 : 280)) fail(`desktop ${w}x${h}`, `map only ${Math.round(mapH)}px tall`);
    }
    await d.close();
  }

  // 7. Phone width: no sideways scrolling
  const phone = await browser.newPage({ viewport: { width: 390, height: 860 } });
  phone.on("pageerror", e => errors.push("phone: " + e.message));
  for (const lens of ["work", "proc"]) {
    await phone.goto(PAGE + "?lens=" + lens);
    await phone.waitForTimeout(300);
    for (const tab of ["summary", "data", "temp", "stress", "about"]) {
      await phone.click(`.tabs button[data-tab="${tab}"]`);
      const over = await phone.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (over > 0) fail(`phone/${lens}/${tab}`, `page scrolls sideways by ${over}px`);
    }
  }

  for (const e of errors) fail("console", e);
  await browser.close();
  console.log(`${states} states checked, ${failures.length} problems`);
  for (const f of failures.slice(0, 40)) console.log(" - " + f);
  process.exit(failures.length ? 1 : 0);
})();
