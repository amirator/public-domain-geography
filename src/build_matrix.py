"""Build the work x country public-domain matrix (as of 1 Jan 2026)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .rules import AS_OF, COUNTRIES, NAMES, Work, cell

ROOT = Path(__file__).resolve().parents[1]


def load_works() -> list[Work]:
    df = pd.read_csv(ROOT / "data" / "works.csv", keep_default_na=False)
    wd = json.loads((ROOT / "data" / "wikidata_creators.json").read_text())
    works = []
    for r in df.itertuples():
        deaths = [wd[n]["death_year"] for n in r.creators.split("|")]
        works.append(Work(r.id, r.title, r.type, max(deaths), int(r.pub_year), r.origin, r.author_nat,
                          frozenset(f for f in r.flags.split(";") if f)))
    return works


def build() -> pd.DataFrame:
    works = load_works()
    meta = pd.read_csv(ROOT / "data" / "works.csv", keep_default_na=False).set_index("id")
    rows = []
    for w in works:
        for c in COUNTRIES:
            x = cell(w, c)
            rows.append({"work_id": w.id, "title": w.title, "type": w.type, "creators": meta.loc[w.id, "creators"],
                         "last_author_death": w.death, "pub_year": w.pub_year, "origin": w.origin,
                         "country": c, "country_name": NAMES[c], "status": x.status,
                         "pd_year": x.pd_year, "alt_year": x.alt_year, "rule": x.note})
    long = pd.DataFrame(rows)
    long["pd_year"] = long["pd_year"].astype("Int64")
    long["alt_year"] = long["alt_year"].astype("Int64")
    return long


def summaries(long: pd.DataFrame) -> dict:
    by_country = (long.groupby("country")["status"].value_counts().unstack(fill_value=0)
                  .reindex(COUNTRIES).fillna(0).astype(int))
    by_country["pct_pd"] = (100 * by_country.get("PD", 0) / by_country.sum(axis=1)).round(1)
    wide = long.pivot(index="work_id", columns="country", values="status")
    divided = wide.apply(lambda r: r.nunique(), axis=1)
    unlock_spread = (long.dropna(subset=["pd_year"]).groupby("work_id")["pd_year"]
                     .agg(lambda s: int(s.max() - s.min())))
    return {
        "as_of": f"{AS_OF}-01-01",
        "n_works": int(long.work_id.nunique()),
        "n_countries": len(COUNTRIES),
        "n_cells": int(len(long)),
        "status_counts": long.status.value_counts().to_dict(),
        "works_with_mixed_status": int((divided > 1).sum()),
        "works_pd_everywhere_modelled": int((wide == "PD").all(axis=1).sum()),
        "pct_pd_by_country": by_country["pct_pd"].to_dict(),
        "max_unlock_spread_years": int(unlock_spread.max()),
        "work_with_max_spread": long.loc[long.work_id == unlock_spread.idxmax(), "title"].iloc[0],
    }


def main() -> None:
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    long = build()
    long.to_csv(out / "pd_matrix_long.csv", index=False)
    wide = long.assign(v=long.status.str.replace("Not modelled", "n/m") + " " + long.pd_year.astype("string").fillna(""))
    wide.pivot(index="title", columns="country", values="v")[COUNTRIES].to_csv(out / "pd_matrix_wide.csv")
    s = summaries(long)
    (out / "summary.json").write_text(json.dumps(s, indent=2, ensure_ascii=False))
    print(json.dumps(s, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
