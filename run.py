"""Run the full analysis: Wikidata fetch (cached) -> matrix -> charts.

Usage:  python run.py            (uses cached Wikidata results)
        python run.py --refresh  (re-queries Wikidata)
"""
import sys

import pandas as pd

from src import build_matrix, charts
from src.wikidata import fetch_all

if __name__ == "__main__":
    works = pd.read_csv("data/works.csv", keep_default_na=False)
    pairs = {}
    for r in works.itertuples():
        for n, d in zip(r.creators.split("|"), r.expected_deaths.split("|")):
            pairs[n] = int(d)
    cache = fetch_all(list(pairs.items()), refresh="--refresh" in sys.argv)
    issues = [v for v in cache.values() if v["match"] != "ok"]
    print(f"Wikidata: {len(cache)} creators resolved, {len(issues)} differ from editor expectation")
    for i in issues:
        print("  check:", i)
    build_matrix.main()
    charts.main()
