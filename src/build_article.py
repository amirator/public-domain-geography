"""Fill the article table from data, then render Markdown + styled HTML."""
from __future__ import annotations

import re
from pathlib import Path

import markdown
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "article"
WORKS = ["Nineteen Eighty-Four", "The Hobbit", "The Little Prince", "The Revolt of the Masses", "The Two Fridas",
         "Les Demoiselles d'Avignon", "Winnie-the-Pooh (text)", "Metropolis (1927)", "Rashomon (1950)",
         "Tintin in the Land of the Soviets"]
COLS = [("GB", "UK"), ("FR", "France"), ("ES", "Spain"), ("US", "USA"), ("CA", "Canada"), ("MX", "Mexico"),
        ("CN", "China"), ("NZ", "N. Zealand")]


def fmt(status: str, year) -> str:
    if status == "Not modelled":
        return "n/m"
    if status == "PD":
        return "free" if pd.isna(year) else f"free {int(year)}"
    if status == "Protected":
        return f"to {int(year) - 1}"
    return "?" if pd.isna(year) else f"? ({int(year)})"


def table() -> str:
    d = pd.read_csv(ROOT / "results" / "pd_matrix_long.csv", dtype={"pd_year": "Int64"})
    lines = ["| Work | " + " | ".join(n for _, n in COLS) + " |", "|---|" + "---|" * len(COLS)]
    for t in WORKS:
        r = d[d.title == t].set_index("country")
        cells = [fmt(r.loc[c, "status"], r.loc[c, "pd_year"]) for c, _ in COLS]
        lines.append(f"| *{t.replace(' (text)', '')}* | " + " | ".join(cells) + " |")
    return "\n".join(lines)


CSS = """
:root{--ink:#1b1b1b;--muted:#666;--accent:#1d3557;--teal:#2a9d8f;--paper:#fbfaf7}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
font:18px/1.7 Georgia,'Times New Roman',serif}
main{max-width:760px;margin:0 auto;padding:48px 22px 80px}
h1{font:800 2.5rem/1.15 'Helvetica Neue',Arial,sans-serif;letter-spacing:-.02em;margin:.2em 0 .3em}
h1+p em{font-size:1.25rem;color:var(--muted)}
h2{font:700 1.45rem/1.3 'Helvetica Neue',Arial,sans-serif;margin:2.2em 0 .6em;color:var(--accent)}
h3{font:700 1.1rem 'Helvetica Neue',Arial,sans-serif;margin-top:2em}
img{width:100%;height:auto;border-radius:6px;margin:1.2em 0;box-shadow:0 1px 8px rgba(0,0,0,.08)}
table{width:100%;border-collapse:collapse;font:14px/1.4 'Helvetica Neue',Arial,sans-serif;margin:1.4em 0;display:block;overflow-x:auto}
th,td{padding:7px 8px;border-bottom:1px solid #e3e1da;text-align:left;white-space:nowrap}
th{background:#efede6}td:first-child{white-space:normal;min-width:170px}
blockquote{border-left:4px solid var(--teal);margin:1.5em 0;padding:.2em 1em;color:#333}
a{color:var(--accent);word-break:break-word}
ol li{font-size:14px;line-height:1.5;margin-bottom:.4em;font-family:'Helvetica Neue',Arial,sans-serif}
hr{border:0;border-top:1px solid #ddd;margin:3em 0}
strong{color:#111}
td.free{color:#1f7a6f;font-weight:600}td.lock{color:var(--accent);font-weight:600}td.q{color:#c06a1f;font-weight:600}
"""


def main() -> None:
    md = (ART / "article_template.md").read_text().replace("{{TABLE}}", table())
    (ART / "article.md").write_text(md)
    body = markdown.markdown(md, extensions=["tables"])
    body = re.sub(r"<td>(free[^<]*)</td>", r'<td class="free">\1</td>', body)
    body = re.sub(r"<td>(to \d+)</td>", r'<td class="lock">\1</td>', body)
    body = re.sub(r"<td>(\?[^<]*)</td>", r'<td class="q">\1</td>', body)
    body = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', body)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Big Brother Is Free in London. In New York, He Is Locked Until 2045 — Amir Khan</title>
<meta name="author" content="Amir Khan"><style>{CSS}</style></head><body><main>{body}</main></body></html>"""
    (ART / "article.html").write_text(html)
    main_text = md.split("### Method in brief")[0]
    words = len(re.findall(r"[A-Za-z0-9'’\-]+", re.sub(r"!\[.*?\]\(.*?\)|\|.*\|", " ", main_text)))
    print("article words (excl. table, method, references):", words)


if __name__ == "__main__":
    main()
