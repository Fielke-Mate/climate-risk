"""Download ERA5 hourly time series (baseline years) for every pilot site.

Usage:  CDSAPI_KEY=... python scripts/fetch_era5.py [--workers 4] [--sites TLS,SVQ]
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from climate_risk import era5
from climate_risk.config import load_sites, settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--sites", default="")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    b = settings()["baseline"]
    sites = load_sites()
    if args.sites:
        wanted = set(args.sites.split(","))
        sites = [s for s in sites if s.site_id in wanted]

    def job(site):
        t0 = time.time()
        for attempt in range(3):
            try:
                path = era5.fetch(site, b["start_year"], b["end_year"], overwrite=args.overwrite)
                return site.site_id, f"ok {path.stat().st_size/1e6:.1f} MB in {time.time()-t0:.0f}s"
            except Exception as exc:  # retry transient CDS errors
                err = exc
                time.sleep(10 * (attempt + 1))
        return site.site_id, f"FAILED: {err}"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for fut in as_completed([pool.submit(job, s) for s in sites]):
            sid, msg = fut.result()
            print(f"{sid}: {msg}", flush=True)


if __name__ == "__main__":
    main()
