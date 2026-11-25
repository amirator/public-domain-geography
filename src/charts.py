"""Charts built only from results/pd_matrix_long.csv."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.patches import Patch, Polygon as MplPolygon
from shapely.geometry import shape

from .rules import COUNTRIES, NAMES

ROOT = Path(__file__).resolve().parents[1]
CH = ROOT / "charts"
COL = {"PD": "#2a9d8f", "Protected": "#1d3557", "Uncertain": "#f4a261", "Not modelled": "#e0e0e0"}
ORDER = ["PD", "Uncertain", "Protected", "Not modelled"]
INK, MUTED = "#1b1b1b", "#6b6b6b"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
SOURCE = "Source: Amir Khan, public-domain-geography model (statutes cited per country; death dates from Wikidata, CC0). Status on 1 Jan 2026. Not legal advice."

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc", "axes.titleweight": "bold"})


def _foot(fig, y=0.01):
    fig.text(0.01, y, SOURCE, fontsize=7.5, color=MUTED, ha="left")


def load() -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "pd_matrix_long.csv", dtype={"pd_year": "Int64", "alt_year": "Int64"})


def _short(t: str, n: int = 34) -> str:
    return t if len(t) <= n else t[: n - 1] + "…"


# 1. world map --------------------------------------------------------------
def world_map(df: pd.DataFrame) -> None:
    raw = ROOT / "data" / "raw" / "ne_110m_admin_0_countries.geojson"
    if not raw.exists():
        raw.write_bytes(requests.get(NE_URL, timeout=60).content)
    gj = json.loads(raw.read_text())
    m = df[df.status != "Not modelled"]
    pct = (m.assign(pd_=m.status.eq("PD")).groupby("country")["pd_"].mean() * 100).to_dict()
    cmap = LinearSegmentedColormap.from_list("pd", ["#1d3557", "#a8dadc", "#2a9d8f"])
    fig, ax = plt.subplots(figsize=(14, 7.4))
    for f in gj["features"]:
        iso = f["properties"].get("ISO_A2_EH") or f["properties"].get("ISO_A2")
        if f["properties"].get("ADMIN") == "Antarctica":
            continue
        geom = shape(f["geometry"])
        polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        color = cmap(pct[iso] / 100) if iso in pct else "#efefef"
        for p in polys:
            ax.add_patch(MplPolygon(np.asarray(p.exterior.coords), closed=True, fc=color, ec="white", lw=0.4))
    lab = {"GB": (-14, 56), "FR": (-6, 44.5), "DE": (12, 53.5), "ES": (-12, 38), "RU": (95, 62), "US": (-100, 39),
           "CA": (-105, 60), "MX": (-104, 22), "BR": (-52, -10), "CO": (-82, 4), "JP": (146, 37), "CN": (102, 34),
           "KR": (132, 33), "AU": (134, -25), "NZ": (176, -46), "ZA": (24, -31), "NG": (8, 9), "EG": (30, 26)}
    for iso, (x, y) in lab.items():
        ax.text(x, y, f"{pct[iso]:.0f}%", fontsize=10, weight="bold", ha="center", va="center", color="white",
                bbox=dict(boxstyle="round,pad=0.2", fc="#00000088", ec="none"))
    ax.set_xlim(-170, 190); ax.set_ylim(-58, 84); ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle("Same 80 classics, very different freedom", x=0.02, ha="left", fontsize=20, weight="bold", color=INK)
    fig.text(0.02, 0.905, "Share of 80 famous books, films, scores and paintings that are in the public domain on 1 January 2026 (modelled cells only)",
             fontsize=11, color=MUTED)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 100)); sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.02, aspect=50)
    cb.set_label("% public domain", fontsize=9); cb.outline.set_visible(False)
    _foot(fig)
    fig.savefig(CH / "01_world_map_share_public_domain.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# 2. same work, different status grid ------------------------------------------
ICONIC = ["Nineteen Eighty-Four", "The Hobbit", "The Little Prince", "Winnie-the-Pooh (text)", "The Sun Also Rises",
          "The Revolt of the Masses", "The Two Fridas", "Les Demoiselles d'Avignon", "Metropolis (1927)",
          "Rashomon (1950)", "Boléro", "Peter and the Wolf", "Tintin in the Land of the Soviets", "Gone with the Wind"]


def grid(df: pd.DataFrame) -> None:
    sub = df[df.title.isin(ICONIC)]
    st = sub.pivot(index="title", columns="country", values="status").loc[ICONIC, COUNTRIES]
    yr = sub.pivot(index="title", columns="country", values="pd_year").loc[ICONIC, COUNTRIES]
    code = st.replace({k: i for i, k in enumerate(ORDER)}).astype(int)
    fig, ax = plt.subplots(figsize=(16, 8.6))
    ax.imshow(code.values, cmap=ListedColormap([COL[k] for k in ORDER]), vmin=-0.5, vmax=3.5, aspect="auto")
    for i in range(len(ICONIC)):
        for j in range(len(COUNTRIES)):
            s, y = st.iat[i, j], yr.iat[i, j]
            if s == "Not modelled":
                txt = "n/m"
            elif s == "PD":
                txt = "free" if pd.isna(y) else f"free\n{y}"
            elif s == "Protected":
                txt = f"until\n{int(y) - 1}"
            else:
                txt = "?" if pd.isna(y) else f"?\n{y}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7.4, color="white" if s in ("PD", "Protected") else INK,
                    linespacing=0.95)
    ax.set_xticks(range(len(COUNTRIES)), [NAMES[c].replace("United ", "U. ").replace("South ", "S. ").replace("New Zealand", "N. Zealand") for c in COUNTRIES],
                  rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(ICONIC)), [_short(t) for t in ICONIC], fontsize=10)
    ax.tick_params(length=0)
    ax.set_xticks(np.arange(-.5, len(COUNTRIES)), minor=True); ax.set_yticks(np.arange(-.5, len(ICONIC)), minor=True)
    ax.grid(which="minor", color="white", lw=1.5); ax.tick_params(which="minor", length=0)
    fig.suptitle("Same work, different status", x=0.01, ha="left", fontsize=20, weight="bold", color=INK, y=1.0)
    fig.text(0.01, 0.955, "'free YYYY' = public domain since 1 Jan of that year; 'until YYYY' = protected through 31 Dec; '?' = contested reading (first year shown); n/m = film rule not modelled",
             fontsize=9.5, color=MUTED)
    ax.legend(handles=[Patch(color=COL[k], label=k) for k in ORDER], ncol=4, loc="lower right", bbox_to_anchor=(1, 1.0), frameon=False, fontsize=9)
    _foot(fig, -0.04)
    fig.savefig(CH / "02_same_work_different_status.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# 3. timeline ------------------------------------------------------------------
TL = ["Nineteen Eighty-Four", "The Hobbit", "The Little Prince", "The Revolt of the Masses", "The Two Fridas",
      "Les Demoiselles d'Avignon", "Winnie-the-Pooh (text)", "Metropolis (1927)", "Rashomon (1950)", "Tintin in the Land of the Soviets"]


def timeline(df: pd.DataFrame) -> None:
    sub = df[df.title.isin(TL) & df.pd_year.notna()]
    fig, ax = plt.subplots(figsize=(14, 7.2))
    for i, t in enumerate(TL):
        r = sub[sub.title == t]
        lo, hi = r.pd_year.min(), r.pd_year.max()
        ax.plot([lo, hi], [i, i], color="#d0d0d0", lw=3, zorder=1)
        for _, x in r.sort_values("status", key=lambda c: c.map({"Protected": 0, "PD": 1, "Uncertain": 2})).iterrows():
            unc = x.status == "Uncertain"
            ax.scatter(x.pd_year, i - (0.18 if unc else 0), s=70 if not unc else 55, zorder=4 if unc else 3,
                       color=COL[x.status], edgecolor="white", lw=0.8, marker="D" if unc else "o")
        ext = {lo: r[r.pd_year == lo].country.tolist(), hi: r[r.pd_year == hi].country.tolist()}
        ax.text(lo - 1, i + 0.28, f"{lo}: {', '.join(ext[lo][:4])}{'…' if len(ext[lo]) > 4 else ''}", fontsize=7.6, color=MUTED, ha="left")
        ax.text(hi + 1, i, f"{hi}: {', '.join(ext[hi][:3])}", fontsize=8, color=INK, va="center")
    ax.axvline(2026, color="#e63946", lw=1.5, ls="--"); ax.text(2026.5, -0.6, "today (2026)", color="#e63946", fontsize=9)
    ax.set_yticks(range(len(TL)), [_short(t) for t in TL], fontsize=10); ax.invert_yaxis()
    ax.set_xlim(1970, 2102); ax.grid(axis="x", color="#eeeeee"); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.suptitle("When does a classic become free? Depends where you stand", x=0.01, ha="left", fontsize=19, weight="bold", color=INK)
    fig.text(0.01, 0.915, "Each dot is one of 18 countries: the first year the work is in the public domain there. Grey bar = the gap between the first and last country.",
             fontsize=10, color=MUTED)
    ax.legend(handles=[Patch(color=COL["PD"], label="free by 2026"), Patch(color=COL["Protected"], label="still protected"),
                       Patch(color=COL["Uncertain"], label="contested reading (diamond)")], loc="lower left", bbox_to_anchor=(0, -0.16), ncol=3, frameon=False, fontsize=9)
    _foot(fig, -0.06)
    fig.savefig(CH / "03_timeline_unlock_years.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# 4. full heatmap (appendix) -----------------------------------------------------
def heatmap(df: pd.DataFrame) -> None:
    st = df.pivot(index="title", columns="country", values="status")[COUNTRIES]
    score = st.eq("PD").sum(axis=1) - st.eq("Protected").sum(axis=1)
    st = st.loc[score.sort_values(ascending=False).index]
    code = st.replace({k: i for i, k in enumerate(ORDER)}).astype(int)
    fig, ax = plt.subplots(figsize=(12, 24))
    ax.imshow(code.values, cmap=ListedColormap([COL[k] for k in ORDER]), vmin=-0.5, vmax=3.5, aspect="auto")
    ax.set_xticks(range(len(COUNTRIES)), COUNTRIES, fontsize=10); ax.xaxis.tick_top()
    ax.set_yticks(range(len(st)), [_short(t, 40) for t in st.index], fontsize=8.5)
    ax.set_xticks(np.arange(-.5, len(COUNTRIES)), minor=True); ax.set_yticks(np.arange(-.5, len(st)), minor=True)
    ax.grid(which="minor", color="white", lw=1); ax.tick_params(which="both", length=0)
    ax.set_title("80 works × 18 countries: public-domain status on 1 January 2026", fontsize=15, pad=36, loc="left")
    ax.legend(handles=[Patch(color=COL[k], label=k) for k in ORDER], ncol=4, loc="upper left", bbox_to_anchor=(0, -0.005), frameon=False)
    _foot(fig, 0.0)
    fig.savefig(CH / "04_full_heatmap_80x18.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


# 5. header image -----------------------------------------------------------------
def header(df: pd.DataFrame) -> None:
    r = df[(df.title == "Nineteen Eighty-Four") & df.pd_year.notna()].copy()
    fig = plt.figure(figsize=(16, 9), facecolor="#fbfaf7")
    ax = fig.add_axes([0.06, 0.10, 0.88, 0.50], facecolor="#fbfaf7")
    groups = r.groupby("pd_year")
    ax.axhline(0, color="#bbbbbb", lw=2, zorder=1)
    for yr, g in groups:
        sts = g.status.tolist()
        color = COL["Uncertain"] if all(x == "Uncertain" for x in sts) else (COL["PD"] if yr <= 2026 else COL["Protected"])
        ax.scatter(yr, 0, s=520, color=color, zorder=3, edgecolor="white", lw=2)
        names = [NAMES[c].replace("United Kingdom", "UK").replace("United States", "USA") + ("*" if st_ == "Uncertain" else "")
                 for c, st_ in zip(g.country, g.status)]
        label = "\n".join(names[:9]) + (f"\n+{len(names) - 9} more" if len(names) > 9 else "")
        ax.text(yr, 0.35, str(yr), ha="center", fontsize=22, weight="bold", color=color)
        ax.text(yr, -0.32, label, ha="center", va="top", fontsize=11.5, color=INK, linespacing=1.25)
    ax.axvline(2026, color="#e63946", ls="--", lw=1.5); ax.text(2026, 0.85, "today", color="#e63946", ha="center", fontsize=12)
    ax.set_xlim(1995, 2050); ax.set_ylim(-2.3, 1.1); ax.axis("off")
    fig.text(0.06, 0.86, "Nineteen Eighty-Four is free in London.", fontsize=40, weight="bold", color=INK)
    fig.text(0.06, 0.77, "In New York it stays locked until 2045.", fontsize=40, weight="bold", color=COL["Protected"])
    fig.text(0.06, 0.69, "The year Orwell's novel entered the public domain, by country (Mexico also free; its exact year is not modelled)", fontsize=15, color=MUTED)
    fig.text(0.06, 0.05, "Amir Khan · Independent Researcher · statutes cited per country · death dates: Wikidata (CC0) · * contested reading · not legal advice",
             fontsize=11, color=MUTED)
    fig.savefig(CH / "00_header_1984.png", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    CH.mkdir(exist_ok=True)
    df = load()
    world_map(df); grid(df); timeline(df); heatmap(df); header(df)
    print("charts:", sorted(p.name for p in CH.glob("*.png")))


if __name__ == "__main__":
    main()
