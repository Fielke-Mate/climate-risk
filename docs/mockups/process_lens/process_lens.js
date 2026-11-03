/* Process-limit lens: MOCK-UP overlay on the built dashboard. Values are computed in the browser from hourly dry bulb
   (typical meteorological year, hot and extreme reference years; futures = the same years shifted by the dashboard's
   month x hour mean change). The real build would use the multi-year pipeline with model ranges. */
(() => {
const MD = window.__MOCK;
const dec = b => Uint8Array.from(atob(b), c => c.charCodeAt(0));
const HR = {};
for (const [sid, o] of Object.entries(MD)) {
  const loc = {};
  for (const b of ["hist", "hotref", "extref"]) {
    const mh = dec(o.loc[b]), n = mh.length / 2, db = dec(o.loc[b + "_day"]);
    loc[b] = { m: mh.subarray(0, n), h: mh.subarray(n), d: new Uint16Array(db.buffer, 0, n) };
  }
  HR[sid] = { loc, t: {} };
  for (const [k, b] of Object.entries(o.v)) { const u = dec(b), f = new Float32Array(u.length); for (let i = 0; i < u.length; i++) f[i] = u[i] / 4 - 10; HR[sid].t[k] = f; }
}
const baseOf = k => k === "hist" || k.startsWith("ssp") ? "hist" : k.startsWith("hot") ? "hotref" : "extref";

const PRESETS = {
  paint: { label: "Paint / coating application", lim: 35 },
  sealant: { label: "Sealant / adhesive application", lim: 30 },
  composite: { label: "Composite layup room (cooling design)", lim: 32 },
  chiller: { label: "Chiller plant rated ambient", lim: 38 },
  custom: { label: "Custom process", lim: null },
};
const qs = new URLSearchParams(location.search);
const P = { on: qs.get("lens") !== "work", proc: "paint", lim: 35, run: qs.get("run") === "24" ? "24" : "op", alt: qs.get("alt") === "1" };
const thr = () => P.lim - Number(S.hall);
const procName = () => P.proc === "custom" ? "custom limit" : PRESETS[P.proc].label;
const runText = () => P.run === "op" ? `runs ${DATA.meta.operating_hours.start}–${DATA.meta.operating_hours.end}` : "runs 24 h";
const hallText = () => S.hall === "0" ? "hall = outside" : `hall +${S.hall} °C`;
const limText = () => `${fmt(P.lim, 1)} °C`;

/* ---------- statistics for one site and year ---------- */
const CACHE = new Map();
function stats(sid, key) {
  const ck = `${sid}|${key}|${thr()}|${P.run}`;
  if (CACHE.has(ck)) return CACHE.get(ck);
  const t = HR[sid].t[key], L = HR[sid].loc[baseOf(key)], th = thr(), op = P.run === "op";
  let hours = 0, early = 0, late = 0, night = 0, dh = 0, mx = -99;
  const days = new Set(), mh = Array.from({ length: 12 }, () => new Array(24).fill(0)), cnt = [];
  for (let i = 0; i < t.length; i++) {
    const h = L.h[i], sh = h >= 6 && h < 14 ? "e" : h >= 14 && h < 22 ? "l" : "n", counted = !op || sh !== "n", v = t[i];
    if (!counted) { if (v > th) night++; continue; }
    cnt.push(v); if (v > mx) mx = v;
    if (v > th) { hours++; dh += v - th; mh[L.m[i]][h]++; days.add(L.d[i]); if (sh === "e") early++; else if (sh === "l") late++; else night++; }
  }
  const dl = [...days].sort((a, b) => a - b), runs = [];
  for (let i = 0; i < dl.length; i++) { if (i && dl[i] === dl[i - 1] + 1) runs[runs.length - 1]++; else runs.push(1); }
  const sorted = Float32Array.from(cnt).sort();
  const r = { hours, early, late, night: op ? night : night, days: dl.length, dh, mx: mx + Number(S.hall), mh, runs, longest: runs.length ? Math.max(...runs) : 0, sorted,
    p99: sorted[Math.floor(sorted.length * 0.99)] + Number(S.hall) };
  CACHE.set(ck, r); return r;
}
/* hours above a limit L (outdoor threshold L - hall gain) from the sorted counted temperatures */
function above(st, L) { const th = L - Number(S.hall), a = st.sorted; let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] > th) hi = m; else lo = m + 1; } return a.length - lo; }
const varKey = (per = S.period, yt = S.yt) => per === "hist" ? { typical: "hist", hot: "hotref", extreme: "extref" }[yt] : `${{ typical: "", hot: "hot_", extreme: "ext_" }[yt]}${S.scen}_${per}`;

/* ---------- header + View bar ---------- */
const pbarSp = $(".pbar .sp");
pbarSp.insertAdjacentHTML("beforebegin", `<div class="vgrp lens" style="margin-left:18px"><span>Heat risk to</span><div class="toggle" id="ctl-lens"><button data-v="work">Workers</button><button data-v="proc">Processes</button></div></div>`);
$(".pbar .ktag.k-edit").insertAdjacentHTML("beforebegin", `<span class="ktag k-look" title="Values computed from single weather years for the mock-up"><i class="d"></i>Mock-up · illustrative values</span>`);
const vbar = $(".vbar"), expoG = $("#ctl-expo").closest(".vgrp"), profG = $("#ctl-prof").closest(".vgrp");
profG.insertAdjacentHTML("afterend", `
  <div class="vgrp pl"><span>Process</span><select class="ksel" id="ctl-proc" aria-label="Process">${Object.entries(PRESETS).map(([k, q]) => `<option value="${k}">${q.label}${q.lim ? ` · ${q.lim} °C` : ""}</option>`).join("")}</select></div>
  <div class="vgrp pl"><span title="Dry-bulb air temperature above which the process cannot run">Limit</span><div class="toggle stepper"><button data-d="-0.5" aria-label="Lower the limit">−</button><input id="ctl-lim" type="number" step="0.5" min="20" max="45" aria-label="Process limit, °C"><span class="u">°C</span><button data-d="0.5" aria-label="Raise the limit">+</button></div></div>
  <div class="vgrp pl"><span title="When the process runs">Runs</span><div class="toggle" id="ctl-run"><button data-v="op">06–22</button><button data-v="24">24 h</button></div></div>`);
document.head.insertAdjacentHTML("beforeend", `<style>
  .stepper { align-items: center; } .stepper button { width: 26px; padding: 0; font-size: 15px; }
  .stepper input { width: 52px; height: 26px; border: 0; border-radius: 6px; background: #fff; box-shadow: 0 1px 2px rgba(28,16,44,.14); font: inherit; font-size: var(--fs-125); font-weight: 600; text-align: right; padding: 0 2px 0 4px; font-variant-numeric: tabular-nums; -moz-appearance: textfield; }
  .stepper input::-webkit-inner-spin-button { -webkit-appearance: none; } .stepper .u { font-size: var(--fs-12); color: var(--ink-2); padding: 0 4px 0 3px; }
  .vgrp.pl select.ksel { width: auto; flex: none; max-width: 300px; }
  .sc svg text.halo { paint-order: stroke; stroke: #fff; stroke-width: 4px; stroke-linejoin: round; }
  .proc-off .pl { display: none !important; } .proc-on .wk { display: none !important; }
  .sc svg .lim { stroke: var(--ink); stroke-width: 1.25; stroke-dasharray: 3 3; }
  .sc svg .eq { stroke: #D91877; stroke-width: 1.5; }
  .sc svg text.eqt { fill: #D91877; font-weight: 600; }
</style>`);
expoG.classList.add("wk"); profG.classList.add("wk");
function syncControls() {
  document.body.classList.toggle("proc-on", P.on); document.body.classList.toggle("proc-off", !P.on);
  for (const b of $$("#ctl-lens button")) b.setAttribute("aria-pressed", (b.dataset.v === "proc") === P.on);
  for (const b of $$("#ctl-run button")) b.setAttribute("aria-pressed", b.dataset.v === P.run);
  $("#ctl-proc").value = P.proc; $("#ctl-lim").value = P.lim.toFixed(1);
  /* hall gain applies to an indoor process at all times; exposure (sun) does not apply to air temperature */
  if (P.on) { $("#hallgrp").style.opacity = 1; for (const b of $$("#ctl-hall button")) b.disabled = false; }
  const sel = $("#ctl-layer");
  sel.innerHTML = (P.on ? PROC_OPTS : WORK_OPTS);
  if (![...sel.options].some(o => o.value === S.layer)) S.layer = P.on ? "proc_days" : "worker_days";
  sel.value = S.layer;
}
const WORK_OPTS = $("#ctl-layer").innerHTML;
const PROC_OPTS = `<option value="proc_days">Process-stop days (an operating hour above the limit)</option>
  <option value="proc_hours">Operating hours above the limit</option>
  <option value="d_proc_days">Extra process-stop days vs today (2040 / 2050)</option>
  <option value="days_tmax_gt30">Days above 30 °C</option>
  <option value="warming">Warming in annual mean temperature (2040 / 2050)</option>`;
const setLim = v => { P.lim = Math.min(45, Math.max(20, Math.round(v * 2) / 2)); };
$$("#ctl-lens button").forEach(b => b.addEventListener("click", () => { P.on = b.dataset.v === "proc"; syncControls(); renderAll(); }));
$$("#ctl-run button").forEach(b => b.addEventListener("click", () => { P.run = b.dataset.v; syncControls(); renderAll(); }));
$("#ctl-proc").addEventListener("change", e => { P.proc = e.target.value; if (PRESETS[P.proc].lim) setLim(PRESETS[P.proc].lim); syncControls(); renderAll(); });
$$(".stepper button").forEach(b => b.addEventListener("click", () => { setLim(P.lim + Number(b.dataset.d)); P.proc = Object.keys(PRESETS).find(k => PRESETS[k].lim === P.lim) || "custom"; syncControls(); renderAll(); }));
$("#ctl-lim").addEventListener("change", e => { setLim(Number(e.target.value)); P.proc = Object.keys(PRESETS).find(k => PRESETS[k].lim === P.lim) || "custom"; syncControls(); renderAll(); });

/* ---------- map layers ---------- */
Object.assign(LAYER, {
  proc_days: { unit: "days", d: 0, short: "Process-stop days", breaks: [1, 5, 15, 35, 70] },
  proc_hours: { unit: "h", d: 0, short: "Operating hours above the limit", breaks: [10, 50, 150, 400, 800] },
  d_proc_days: { unit: "days", d: 0, plus: true, short: "Extra process-stop days", breaks: [2, 5, 10, 20, 40] },
});
const _layerVal = layerVal;
layerVal = function (site, period = S.period, scen = S.scen) {
  if (S.layer === "proc_days") return stats(site, varKey(period)).days;
  if (S.layer === "proc_hours") return stats(site, varKey(period)).hours;
  if (S.layer === "d_proc_days") return period === "hist" ? null : stats(site, varKey(period)).days - stats(site, varKey("hist")).days;
  return _layerVal(site, period, scen);
};
const _updateMap = updateMap;
updateMap = function () {
  _updateMap();
  if (!P.on || !S.layer.includes("proc")) return;
  const per = S.period === "hist" ? `Today (${B0}–${B1})` : `${S.period} · ${SCEN[S.scen]}`;
  $("#map-sub").textContent = `${per} · ${YT_TEXT[S.yt]} · ${procName()}, limit ${limText()} dry bulb · ${hallText()} · ${runText()} · click a site for its card`;
};

/* ---------- KPI strip ---------- */
const _renderStrip = renderStrip;
renderStrip = function () {
  if (!P.on) return _renderStrip();
  const v = inView(), n = v.length, k = varKey(), k0 = varKey("hist", S.yt);
  const per = `${S.period === "hist" ? "today" : `${S.period}, ${SCEN[S.scen]}`}, ${S.yt} year`;
  const HIGH = 15, VHIGH = 35, d = (s, key) => stats(s.id, key).days;
  const nHigh = v.filter(s => d(s, k) >= HIGH && d(s, k) < VHIGH).length, nVHigh = v.filter(s => d(s, k) >= VHIGH).length, nToday = v.filter(s => d(s, k0) >= HIGH).length;
  const hNow = v.reduce((a, s) => a + stats(s.id, k).hours, 0), hToday = v.reduce((a, s) => a + stats(s.id, k0).hours, 0), dPct = hToday > 0 ? 100 * (hNow - hToday) / hToday : null;
  const tile = (ic, lab, val, foot) => `<div class="kstat"><div class="lab"><span class="ic">${ICON[ic]}</span>${lab}</div><div class="val">${val}</div><div class="foot">${foot}</div></div>`;
  $("#kstrip").innerHTML =
    tile("therm", "Sites at high risk · process-stop days", `${nHigh + nVHigh}<small>of ${n}${n ? ` (${fmt(100 * (nHigh + nVHigh) / n)} %)` : ""}</small>`,
      `High (15–34 days) ${nHigh} · Very high (35+) ${nVHigh} · limit ${limText()} · ${hallText()} · ${per}${S.period !== "hist" ? `<br>Today: ${nToday} of ${n} sites` : ""}`) +
    tile("up", "Operating time over the process limit", `${fmt(hNow)}<small>hours a year</small>`,
      `Operating hours above ${limText()} dry bulb (${procName().toLowerCase()}), summed over ${n} ${n === 1 ? "site" : "sites"} (one line per site) · ${hallText()} · ${runText()} · ${per}${S.period !== "hist" && dPct != null ? `<br>${sgn(dPct)} % vs today (${fmt(hToday)} h)` : ""}`);
};

/* ---------- Summary tab ---------- */
const _renderStory = renderStory;
renderStory = function () {
  if (!P.on) return _renderStory();
  return `<div class="story">${card1()}${P.alt ? altSpells() + altCooling() : sensitivity() + whenGrid()}</div>
    <p class="note">${SCEN[S.scen]} · ${runText()} local · limit applies to hall air (${hallText()}) · <b>Mock-up:</b> values from single weather years (typical meteorological year, hot and extreme years), futures shifted by the median month × hour change; the build uses the ${NY}-year statistics and model ranges.</p>`;
};
const YC = { early: 0.5, late: 1, night: 0.15 };
function card1() {
  const id = S.site, sc = S.scen, s = byId[id], per = futPer(), YRS = storyYears(), W0 = paneW(30), op = P.run === "op";
  const rows = YRS.map(y => { const st = stats(id, y.key); return { ...y, st, early: st.early, late: st.late, night: st.night, tot: st.hours }; });
  const gw = 46, lw = 150, rh = 20, gap = 8, bh = 11, W = Math.max(80, W0 - lw - 112);
  const mx = Math.max(...rows.map(r => r.tot + (op ? r.night : 0)), 1), yOf = i => i * rh + Math.floor(i / 3) * gap;
  let o = `<svg class="chart" width="${W0}" viewBox="0 0 ${W0} ${yOf(8) + rh}" style="max-width:${W0}px" role="img" aria-label="Operating hours above the process limit by shift">`;
  rows.forEach((r, i) => {
    const y = yOf(i); let x = lw;
    if (i % 3 === 0) o += `<text class="grp" x="0" y="${y + 14}">${r.grp}</text>`;
    o += `<text class="lab" x="${gw}" y="${y + 14}">${r.sub}</text>`;
    for (const k of ["early", "late", "night"]) {
      const len = W * r[k] / mx, outside = op && k === "night";
      if (len > 0) o += `<rect x="${x}" y="${y + 5}" width="${Math.max(len - 1, 0.5)}" height="${bh}" rx="2" fill="${r.color}" fill-opacity="${outside ? 0.15 : k === "night" ? 0.75 : YC[k]}" ${outside ? `stroke="${r.color}" stroke-width="1"` : ""}/>`;
      x += len;
    }
    o += `<text class="val" x="${x + 6}" y="${y + 14}">${fmt(r.tot)} h${op && r.night >= 0.5 ? `<tspan style="fill:var(--ink-3)"> +${fmt(r.night)} night</tspan>` : ""}</text>`;
  });
  o += `</svg>`;
  const sw = (a, extra = "") => `<i style="background:rgba(74,77,87,${a});${extra}"></i>`;
  const keys = `<div class="keys"><span>${sw(0.5)}Early 06–14</span><span>${sw(1)}Late 14–22</span>${op ? `<span>${sw(0.15, "outline:1px solid #4A4D57")}Night 22–06 (process not running, not in the total)</span>` : `<span>${sw(0.75)}Night 22–06</span>`}<span>Colour = period: today grey, 2040 teal, 2050 ochre; darker = hotter year</span></div>`;
  const g = k => rows.find(r => r.key === k).st;
  const tN = g("hist").days, hN = g("hotref").days, xN = g("extref").days, tF = g(`${sc}_${per}`).days, hF = g(`hot_${sc}_${per}`).days, xFs = g(`ext_${sc}_${per}`), rF = rows.find(r => r.key === `${sc}_${per}`);
  const latePct = rF.tot ? Math.round(100 * rF.late / rF.tot) : 0;
  const none = Math.max(...rows.map(r => r.tot)) < 0.5;
  const head = none ? `<i>No operating hour goes above ${limText()}</i> today or by 2050, even in a hot or extreme year (${hallText()}).${S.hall !== "4" ? " A larger hall heat gain (View bar) shows how sensitive this is." : ""}`
    : `By ${per}, a typical year brings <b>${plural(tF, "process-stop day", "process-stop days")}</b> (today ${fmt(tN)}). A hot year brings <b>${fmt(hF)}</b> (today ${fmt(hN)}); an extreme year, with ${s.extreme_year} weather, brings <b>${fmt(xFs.days)}</b> (today ${fmt(xN)})${xFs.longest >= 2 ? `, up to <b>${fmt(xFs.longest)} days in a row</b>` : ""}. ${rF.tot >= 0.5 ? `<b>${latePct} %</b> of the operating hours above the limit fall on the late shift.` : ""}`;
  return `<div class="sc"><div class="t">${head}</div>
    <div class="sub">Operating hours above ${limText()} dry bulb by shift (${esc(procName().toLowerCase())}); a process-stop day is a day with at least one of these hours · ${hallText()} · ${runText()}</div>${o}${keys}
    <div class="fn"><b>Typical</b>: the median of the last ${NY} years (${B0}–${B1}). <b>Hot year</b>: the site's hottest year in the last ${NY} years, as it happened. <b>Extreme</b>: the site's hottest year since ${E0}, adjusted to a current-day climate baseline. The 2040 and 2050 rows are the same years adjusted to those climates.</div></div>`;
}

/* Recommended card 2: how much headroom the limit has (exceedance curve) */
function sensitivity() {
  const id = S.site, sc = S.scen, per = futPer(), yt = S.yt, W0 = paneW(30), H = 210, m = { l: 44, r: 96, t: 12, b: 28 };
  const ser = [{ key: varKey("hist", yt), name: "Today", color: yt === "typical" ? "var(--c-today)" : yt === "hot" ? "var(--c-hot)" : "var(--c-ext)" },
               { key: varKey("2040", yt), name: "2040", color: yt === "typical" ? "var(--c-2040)" : `var(--c-2040-${yt === "hot" ? "hot" : "ext"})` },
               { key: varKey("2050", yt), name: "2050", color: yt === "typical" ? "var(--c-2050)" : `var(--c-2050-${yt === "hot" ? "hot" : "ext"})` }];
  const x0 = P.lim - 4, x1 = P.lim + 4, xs = []; for (let x = x0; x <= x1 + 1e-9; x += 0.25) xs.push(x);
  ser.forEach(s => { s.st = stats(id, s.key); s.v = xs.map(x => above(s.st, x)); });
  const hi0 = Math.max(...ser.flatMap(s => s.v), 1), st = niceStep(hi0 / 4), hi = Math.ceil(hi0 / st) * st;
  const X = x => m.l + (W0 - m.l - m.r) * (x - x0) / (x1 - x0), Y = v => m.t + (H - m.t - m.b) * (1 - v / hi);
  let o = `<svg class="chart" width="${W0}" viewBox="0 0 ${W0} ${H}" style="max-width:${W0}px" role="img" aria-label="Operating hours above the limit for a range of limits">`;
  for (let v = 0; v <= hi + 1e-9; v += st) o += `<line class="gridl" x1="${m.l}" x2="${W0 - m.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${m.l - 6}" y="${Y(v) + 4}" text-anchor="end">${fmt(v)}</text>`;
  for (let x = Math.ceil(x0); x <= x1; x += 1) o += `<text x="${X(x)}" y="${H - 10}" text-anchor="middle">${x} °C</text>`;
  o += `<line class="axis" x1="${m.l}" x2="${W0 - m.r}" y1="${Y(0)}" y2="${Y(0)}"/>`;
  o += `<line class="lim" x1="${X(P.lim)}" x2="${X(P.lim)}" y1="${m.t - 4}" y2="${Y(0)}"/><text x="${X(P.lim) + 4}" y="${m.t + 2}" style="fill:var(--ink)">limit ${limText()}</text>`;
  ser.forEach(s => {
    o += `<path d="${s.v.map((v, i) => `${i ? "L" : "M"}${X(xs[i]).toFixed(1)},${Y(v).toFixed(1)}`).join("")}" fill="none" stroke="${s.color}" stroke-width="2.5" stroke-linejoin="round"/>`;
    const at = above(s.st, P.lim);
    o += `<circle cx="${X(P.lim)}" cy="${Y(at)}" r="3.5" fill="${s.color}"/>`;
    const lv = s.v[Math.round((x1 - 1.5 - x0) / 0.25)];
  });
  /* right-hand labels: value at the limit */
  const lab = ser.map(s => ({ s, at: above(s.st, P.lim) })).sort((a, b) => b.at - a.at);
  let ly = -99; lab.forEach(({ s, at }) => { let y = Math.max(Y(at) + 4, ly + 13); ly = y; o += `<text x="${W0 - m.r + 8}" y="${y}" style="fill:${s.color};font-weight:600">${s.name} ${fmt(at)} h</text>`; });
  /* equivalent limit: the limit at which the future year matches today's hours */
  const today = above(ser[0].st, P.lim), fut = ser.find(s => s.name === per), futAt = above(fut.st, P.lim);
  let eq = null;
  if (today > 0 && futAt > today) { for (let x = P.lim; x <= P.lim + 15; x += 0.1) if (above(fut.st, x) <= today) { eq = x; break; } }
  if (eq != null && eq <= x1) o += `<line class="eq" x1="${X(P.lim)}" x2="${X(eq)}" y1="${Y(today)}" y2="${Y(today)}" marker-end="url(#ar)"/><text class="eqt halo" x="${X(eq) + 6}" y="${Y(today) + 4}">${sgn(eq - P.lim, 1)} °C</text>`;
  o += `<defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#D91877"/></marker></defs></svg>`;
  const plus2 = above(fut.st, P.lim + 2), ytn = yt === "typical" ? "typical year" : yt === "hot" ? "hot year" : "extreme year";
  const head = futAt < 0.5 ? `Even in ${per} (${ytn}) no operating hour reaches ${limText()}; the hottest is <i>${fmt(fut.st.mx, 1)} °C</i>, leaving <i>${fmt(P.lim - fut.st.mx, 1)} °C</i> of headroom.`
    : today < 0.5 ? `Today the limit is never reached in ${ytn === "extreme year" ? "an" : "a"} ${ytn}; by ${per} it is exceeded for <b>${fmt(futAt)} hours</b>. Staying clear would need a limit of <b>${fmt(fut.st.mx, 1)} °C</b> (the hottest ${per} operating hour), or that much cooling.`
    : `At ${limText()}, ${per} brings <b>${fmt(futAt)} operating hours</b> above the limit in ${ytn === "extreme year" ? "an" : "a"} ${ytn} (today ${fmt(today)}). Holding today's level needs <b>${eq == null ? "more than 15 °C" : `${sgn(eq - P.lim, 1)} °C`}</b> of headroom: a limit of ${eq == null ? "–" : `<b>${fmt(eq, 1)} °C</b>`}, or that much cooling. With 2 °C more tolerance, ${per} drops to <i>${fmt(plus2)} h</i>.`;
  return `<div class="sc"><div class="t">${head}</div>
    <div class="sub">Operating hours a year above each possible limit, ${ytn} · the dashed line is the limit in the View bar; the arrow is the climate change in °C of headroom · ${hallText()} · ${runText()}</div>${o}</div>`;
}

/* Recommended card 3: when the limit is exceeded (month x hour of day) */
function whenGrid() {
  const id = S.site, YRS = storyYears(), per = futPer(), yt = S.yt;
  const b = cmpKey(S.cmpB, varKey(per, yt)), y = YRS.find(x => x.key === b) || YRS[6], base = YRS.find(x => x.key === varKey("hist", yt));
  const st = stats(id, y.key), st0 = stats(id, base.key), d = st.mh, W0 = paneW(30);
  const l = 34, t = 4, rw = 70, cw = Math.min(22, (W0 - l - rw - 12) / 24), ch = 17, gw = cw * 24, gh = ch * 12, rx = l + gw + 10, bw = rw - 26;
  const mT = d.map(r => r.reduce((a, c) => a + c, 0)), hT = Array.from({ length: 24 }, (_, h) => d.reduce((a, r) => a + r[h], 0));
  const cmx = Math.max(1, ...d.flat()), mmx = Math.max(1, ...mT), hmx = Math.max(1, ...hT), op = P.run === "op";
  let o = `<svg class="chart" width="${W0}" viewBox="0 0 ${W0} ${t + gh + 62}" style="max-width:${W0}px" role="img" aria-label="Hours above the limit by month and hour of day">`;
  if (op) for (const [a, z] of [[0, 6], [22, 24]]) o += `<rect x="${l + a * cw - 1}" y="${t - 2}" width="${(z - a) * cw + 0.5}" height="${gh + 2}" fill="var(--bg-2)" fill-opacity=".6" rx="3"/>`;
  d.forEach((r, mi) => r.forEach((v, h) => {
    const isNew = v > 0 && st0.mh[mi][h] === 0, x = l + h * cw, yy = t + mi * ch;
    o += `<rect x="${x}" y="${yy}" width="${cw - 1.5}" height="${ch - 1.5}" rx="2" fill="${v ? y.color : "var(--bg-2)"}" fill-opacity="${v ? 0.18 + 0.82 * Math.sqrt(v / cmx) : op && (h < 6 || h >= 22) ? 0 : 0.55}" ${isNew ? `stroke="#D91877" stroke-width="1.5"` : ""} data-t="${MONTHS[mi]}, ${String(h).padStart(2, "0")}:00<br>${y.name}: ${v} h above the limit<br>${base.name}: ${st0.mh[mi][h]} h"/>`;
  }));
  MONTHS.forEach((mn, mi) => o += `<text x="${l - 6}" y="${t + mi * ch + 12}" text-anchor="end">${mn}</text>`);
  [0, 6, 12, 18, 23].forEach(h => o += `<text x="${l + h * cw + cw / 2}" y="${t + gh + 12}" text-anchor="middle">${String(h).padStart(2, "0")}h</text>`);
  mT.forEach((v, mi) => { const len = v / mmx * bw; if (v) o += `<rect x="${rx}" y="${t + mi * ch + 3}" width="${Math.max(len, 1)}" height="${ch - 7}" rx="2" fill="${y.color}"/><text x="${rx + len + 4}" y="${t + mi * ch + 12}">${v}</text>`; });
  o += `<text x="${rx}" y="${t + gh + 12}">h / month</text>`;
  const by = t + gh + 20, bh = 30;
  hT.forEach((v, h) => { const len = v / hmx * bh; if (v) o += `<rect x="${l + h * cw}" y="${by + bh - len}" width="${cw - 1.5}" height="${Math.max(len, 1)}" rx="2" fill="${y.color}" data-t="${String(h).padStart(2, "0")}:00: ${v} h a year"/>`; });
  o += `<text x="${l - 6}" y="${by + 12}" text-anchor="end">h /</text><text x="${l - 6}" y="${by + 24}" text-anchor="end">hour</text></svg>`;
  /* headline: the two busiest consecutive months and the hour window */
  const tot = st.hours; let best = [0, 0];
  for (let i = 0; i < 11; i++) if (mT[i] + mT[i + 1] > best[1]) best = [i, mT[i] + mT[i + 1]];
  const hs = hT.map((v, h) => v ? h : null).filter(v => v != null), newCells = d.flat().filter((v, i) => v && !st0.mh[Math.floor(i / 24)][i % 24]).length;
  const earlyPct = tot ? Math.round(100 * st.early / tot) : 0;
  const head = !tot ? `No hour above ${limText()} in ${y.name.toLowerCase()}.` : `In ${y.name.toLowerCase()}, <b>${Math.round(100 * best[1] / tot)} %</b> of the hours above the limit fall in <b>${MONTHS[best[0]]}–${MONTHS[best[0] + 1]}</b>, all between <b>${String(Math.min(...hs)).padStart(2, "0")}:00 and ${String(Math.max(...hs) + 1).padStart(2, "0")}:00</b>. The early shift takes <i>${earlyPct} %</i>; ${newCells} month-hour slots are new compared with ${base.name.toLowerCase()}.`;
  const sel = `<select class="ksel" data-cmp="cmpB" aria-label="Year to show">${YRS.map(x => `<option value="${x.key}" ${x.key === y.key ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select>`;
  return `<div class="sc"><div class="t">${head}</div><div class="cmp">Show ${sel}</div>
    <div class="sub">Hours a year above ${limText()} by month and hour of day; darker = more hours; magenta outline: slots that never exceed the limit ${esc(base.name.toLowerCase())}${op ? "; grey columns: process not running" : ""} · ${hallText()}</div>${o}</div>`;
}

/* Alternative A: how long the stoppages last (spell length) */
function altSpells() {
  const id = S.site, sc = S.scen, per = futPer(), YRS = storyYears(), W0 = paneW(30);
  const CL = [["1 day", r => r === 1], ["2 days", r => r === 2], ["3–4 days", r => r >= 3 && r <= 4], ["5+ days", r => r >= 5]], OP = [0.25, 0.5, 0.75, 1];
  const rows = YRS.map(y => { const st = stats(id, y.key); return { ...y, st, parts: CL.map(([, f]) => st.runs.filter(f).reduce((a, r) => a + r, 0)) }; });
  const gw = 46, lw = 150, rh = 20, gap = 8, bh = 11, W = Math.max(80, W0 - lw - 112), mx = Math.max(1, ...rows.map(r => r.st.days)), yOf = i => i * rh + Math.floor(i / 3) * gap;
  let o = `<svg class="chart" width="${W0}" viewBox="0 0 ${W0} ${yOf(8) + rh}" style="max-width:${W0}px" role="img">`;
  rows.forEach((r, i) => {
    const y = yOf(i); let x = lw;
    if (i % 3 === 0) o += `<text class="grp" x="0" y="${y + 14}">${r.grp}</text>`;
    o += `<text class="lab" x="${gw}" y="${y + 14}">${r.sub}</text>`;
    r.parts.forEach((v, k) => { const len = W * v / mx; if (len > 0) o += `<rect x="${x}" y="${y + 5}" width="${Math.max(len - 1, .5)}" height="${bh}" rx="2" fill="${r.color}" fill-opacity="${OP[k]}" data-t="${r.name}<br>${CL[k][0]} runs: ${v} days"/>`; x += len; });
    o += `<text class="val" x="${x + 6}" y="${y + 14}">${fmt(r.st.days)} d${r.st.longest >= 2 ? `<tspan style="fill:var(--ink-3)"> · longest ${r.st.longest}</tspan>` : ""}</text>`;
  });
  o += `</svg>`;
  const f = rows.find(r => r.key === `ext_${sc}_${per}`), t = rows.find(r => r.key === `${sc}_${per}`);
  const long = st => st.days ? Math.round(100 * st.runs.filter(r => r >= 3).reduce((a, r) => a + r, 0) / st.days) : 0;
  const keys = `<div class="keys">${CL.map(([n], k) => `<span><i style="background:rgba(74,77,87,${OP[k]})"></i>in runs of ${n}</span>`).join("")}</div>`;
  return `<div class="sc"><div class="t">In an extreme ${per} year the longest stoppage runs <b>${f.st.longest} days</b>, and <b>${long(f.st)} %</b> of process-stop days come in runs of 3 days or more (typical ${per} year: ${long(t.st)} %), too long to catch up by moving work to cooler days.</div>
    <div class="sub">Process-stop days a year by the length of the run they belong to · ${hallText()} · ${runText()}</div>${o}${keys}</div>`;
}

/* Alternative B: cooling needed to hold the limit */
function altCooling() {
  const id = S.site, sc = S.scen, per = futPer(), YRS = storyYears(), W0 = paneW(30);
  const rows = YRS.map(y => ({ ...y, st: stats(id, y.key) }));
  const lo = Math.min(P.lim - 4, ...rows.map(r => r.st.p99)) - 0.5, hi = Math.max(P.lim + 1, ...rows.map(r => r.st.mx)) + 0.5;
  const gw = 46, lw = 150, rh = 20, gap = 8, rw = 150, X = v => lw + (W0 - lw - rw) * (v - lo) / (hi - lo), yOf = i => 14 + i * rh + Math.floor(i / 3) * gap;
  let o = `<svg class="chart" width="${W0}" viewBox="0 0 ${W0} ${yOf(8) + rh + 4}" style="max-width:${W0}px" role="img">`;
  for (let v = Math.ceil(lo); v <= hi; v += 2) o += `<line class="gridl" x1="${X(v)}" x2="${X(v)}" y1="10" y2="${yOf(8) + rh}"/><text x="${X(v)}" y="8" text-anchor="middle">${v} °C</text>`;
  o += `<line class="lim" x1="${X(P.lim)}" x2="${X(P.lim)}" y1="10" y2="${yOf(8) + rh}"/>`;
  rows.forEach((r, i) => {
    const y = yOf(i), a = X(r.st.p99), b = X(r.st.mx), gapC = r.st.mx - P.lim;
    if (i % 3 === 0) o += `<text class="grp" x="0" y="${y + 14}">${r.grp}</text>`;
    o += `<text class="lab" x="${gw}" y="${y + 14}">${r.sub}</text>`;
    o += `<line x1="${a}" x2="${b}" y1="${y + 10}" y2="${y + 10}" stroke="${r.color}" stroke-width="3" stroke-linecap="round"/><circle cx="${a}" cy="${y + 10}" r="3.5" fill="#fff" stroke="${r.color}" stroke-width="2"/><circle cx="${b}" cy="${y + 10}" r="4" fill="${r.color}"/>`;
    o += `<text class="val" x="${W0 - rw + 10}" y="${y + 14}">${gapC > 0 ? `${fmt(gapC, 1)} °C · ${fmt(r.st.dh)} °C·h` : `<tspan style="fill:var(--ink-3)">clear by ${fmt(-gapC, 1)} °C</tspan>`}</text>`;
  });
  o += `</svg>`;
  const f = rows.find(r => r.key === `ext_${sc}_${per}`).st;
  const keys = `<div class="keys"><span><i style="background:#fff;outline:2px solid #4A4D57;border-radius:50%"></i>1 % design temperature (exceeded in 1 % of operating hours)</span><span><i style="background:#4A4D57;border-radius:50%"></i>hottest operating hour</span><span>dashed: the limit · right: cooling at peak · degree-hours above the limit</span></div>`;
  return `<div class="sc"><div class="t">To hold ${limText()} through an extreme ${per} year the hall needs <b>${fmt(Math.max(0, f.mx - P.lim), 1)} °C</b> of cooling at peak and <b>${fmt(f.dh)} °C·h</b> a year above the limit; sized to the 1 % design condition instead, <i>${fmt(Math.max(0, f.p99 - P.lim), 1)} °C</i>.</div>
    <div class="sub">Operating-hour air temperature against the limit, per year · ${hallText()} · ${runText()}</div>${o}${keys}</div>`;
}

/* ---------- wire ---------- */
const _renderAll = renderAll;
renderAll = function () { CACHE.clear(); _renderAll(); if (P.on) { $("#hallgrp").style.opacity = 1; for (const b of $$("#ctl-hall button")) b.disabled = false; } };
syncControls(); renderAll();
})();
