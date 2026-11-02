"""Download NEX-GDDP-CMIP6 daily data at the pilot sites (baseline + future windows).

Usage: python scripts/fetch_nex.py [--workers 6] [--models ACCESS-CM2,...]
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
    args = ap.parse_args()

    cfg = settings()["future"]
    sites = load_sites()
    models = cfg["models"]
    if args.models:
        models = {m: models[m] for m in args.models.split(",")}
    b0, b1 = cfg["baseline_years"]
    years = sorted(set(range(b0, b1 + 1)).union(*[range(p[0], p[1] + 1) for p in cfg["periods"].values()]))
    jobs = [(m, mem, sc, v, y) for m, mem in models.items() for sc in cfg["scenarios"]
            for v in cfg["variables"] for y in years]
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
