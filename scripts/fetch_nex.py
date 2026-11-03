"""Download NEX-GDDP-CMIP6 daily data at the pilot sites (baseline + future windows).

Usage: python scripts/fetch_nex.py [--workers 6] [--models ACCESS-CM2,...] [--variables tasmax,tasmin]
                                   [--scenarios historical --years 2000-2014]
Default: the configured scenarios, the delta baseline and future windows, and (D61) the historical
run for the baseline-adjustment window before 2015.
Resumable: cached variable-years are skipped.
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from climate_risk import nex
from climate_risk.config import load_sites, settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--models", default="")
    ap.add_argument("--variables", default="", help="comma list; default all configured variables")
    ap.add_argument("--scenarios", default="", help="comma list, e.g. historical; default configured scenarios")
    ap.add_argument("--years", default="", help="first-last, e.g. 2000-2014; default the configured windows")
    args = ap.parse_args()

    cfg = settings()["future"]
    sites = load_sites()
    models = cfg["models"]
    if args.models:
        models = {m: models[m] for m in args.models.split(",")}
    b0, b1 = cfg["baseline_years"]
    variables = args.variables.split(",") if args.variables else cfg["variables"]
    if args.scenarios or args.years:
        scenarios = args.scenarios.split(",") if args.scenarios else cfg["scenarios"]
        y0, y1 = (int(x) for x in args.years.split("-")) if args.years else (b0, b1)
        plan = [(sc, list(range(y0, y1 + 1)), variables) for sc in scenarios]
    else:
        years = sorted(set(range(b0, b1 + 1)).union(*[range(p[0], p[1] + 1) for p in cfg["periods"].values()]))
        plan = [(sc, years, variables) for sc in cfg["scenarios"]]
        adj = cfg.get("baseline_adjustment")
        if adj:  # D61: early window from the historical run (NEX historical ends in 2014)
            a0, a1 = adj["early_window"]
            hist_years = [y for y in range(a0, a1 + 1) if y <= 2014]
            ssp_years = [y for y in range(a0, a1 + 1) if y > 2014]
            plan.append(("historical", hist_years, adj["variables"]))
            plan += [(sc, ssp_years, adj["variables"]) for sc in cfg["scenarios"]]
            plan += [(sc, list(range(b0, b1 + 1)), adj["variables"]) for sc in cfg["scenarios"]]
    jobs = sorted({(m, mem, sc, v, y) for m, mem in models.items() for sc, ys, vs in plan for v in vs for y in ys})
    todo = [j for j in jobs if not nex.cache_path(j[0], j[2], j[3], j[4]).exists()]
    print(f"{len(jobs)} variable-years, {len(todo)} to download", flush=True)

    t0, done, failed = time.time(), 0, []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(nex.fetch_year, sites, *j): j for j in todo}
        for fut in as_completed(futs):
            j = futs[fut]
            try:
                fut.result()
            except Exception as exc:
                failed.append((j, str(exc)[:200]))
            done += 1
            if done % 50 == 0 or done == len(todo):
                rate = done / (time.time() - t0)
                print(f"{done}/{len(todo)} done, {len(failed)} failed, "
                      f"~{(len(todo) - done) / max(rate, 1e-9) / 60:.0f} min left", flush=True)
    for j, e in failed:
        print("FAILED", j, e, flush=True)


if __name__ == "__main__":
    main()
