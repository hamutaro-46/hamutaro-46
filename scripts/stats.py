"""Draw an RPG-menu style STATUS window (commits, languages...) as an SVG
and show it in README.md.

Run on GitHub Actions (needs GITHUB_TOKEN). Preview without changing files:
    GITHUB_TOKEN=xxx python3 scripts/stats.py --print
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

USER = "hamutaro-46"
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SVG = ROOT / "assets" / "status.svg"
START = "<!-- STATS:START -->"
END = "<!-- STATS:END -->"

TOP_LANGS = 5  # number of languages to show
SHORT_NAMES = {"Jupyter Notebook": "Jupyter", "Dockerfile": "Docker"}

# window style (like an RPG menu)
BG = "#111111"
LINE = "#ffffff"
TEXT = "#ffffff"
FONT = "'DotGothic16', 'PixelMplus10', 'Courier New', monospace"


# ---------- collect data from GitHub ----------

def api(path: str) -> dict | list:
    req = Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urlopen(req, timeout=30) as res:
        return json.load(res)


def search_count(kind: str, query: str) -> int:
    return api(f"/search/{kind}?q={quote(query)}&per_page=1")["total_count"]


def collect() -> dict:
    user = api(f"/users/{USER}")

    repos = []
    page = 1
    while True:
        batch = api(f"/users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    repos = [r for r in repos if not r["fork"]]  # only your own repos

    langs: dict[str, int] = {}
    for r in repos:
        for name, size in api(f"/repos/{r['full_name']}/languages").items():
            langs[name] = langs.get(name, 0) + size

    return {
        "since": user["created_at"][:4],
        "commits": search_count("commits", f"author:{USER}"),
        "prs": search_count("issues", f"author:{USER} type:pr"),
        "repos": len(repos),
        "stars": sum(r["stargazers_count"] for r in repos),
        "langs": langs,
    }


# ---------- draw SVG ----------

def window(x: int, y: int, w: int, h: int) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
        f'fill="{BG}" stroke="{LINE}" stroke-width="4"/>'
    )


def text(x: int, y: int, s: str, anchor: str = "start", size: int = 20) -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">'
        f"{escape(s)}</text>"
    )


def label_value(x: int, w: int, y: int, label: str, value: str) -> str:
    """Label on the left, value on the right (like 'Level ... 2')."""
    return text(x + 24, y, label) + text(x + w - 24, y, value, "end")


def render_svg(s: dict) -> str:
    W, H = 720, 300
    parts = []

    # left: character status
    x, y, w, h = 6, 6, 330, H - 12
    parts.append(window(x, y, w, h))
    parts.append(text(x + 24, y + 42, USER, size=22))
    parts.append(text(x + w - 24, y + 42, f'Since {s["since"]}', "end", size=16))
    rows = [
        ("Commits", f'{s["commits"]:,}'),
        ("Repositories", f'{s["repos"]:,}'),
        ("Stars", f'{s["stars"]:,}'),
        ("Pull requests", f'{s["prs"]:,}'),
        ("Languages", f'{len(s["langs"]):,}'),
    ]
    for i, (label, value) in enumerate(rows):
        parts.append(label_value(x, w, y + 90 + i * 40, label, value))

    # right: languages (like the "Equipment" window)
    x, y, w, h = 354, 6, 360, H - 12
    parts.append(window(x, y, w, h))
    parts.append(text(x + 24, y + 42, "Languages", size=22))

    total = sum(s["langs"].values())
    top = sorted(s["langs"].items(), key=lambda kv: -kv[1])[:TOP_LANGS]
    if not top:
        parts.append(text(x + 24, y + 90, "(no data yet)"))
    bar_x, bar_w = x + 160, 110
    for i, (name, size) in enumerate(top):
        ry = y + 90 + i * 40
        ratio = size / total
        pct = f"{ratio * 100:.0f}%" if ratio >= 0.01 else "<1%"
        parts.append(text(x + 24, ry, SHORT_NAMES.get(name, name)[:11], size=18))
        parts.append(
            f'<rect x="{bar_x}" y="{ry - 13}" width="{bar_w}" height="12" '
            f'fill="none" stroke="{LINE}" stroke-width="2"/>'
        )
        parts.append(
            f'<rect x="{bar_x}" y="{ry - 13}" width="{max(2, round(bar_w * ratio))}" '
            f'height="12" fill="{LINE}"/>'
        )
        parts.append(text(x + w - 24, ry, pct, "end", size=18))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">\n'
        f'<g font-family="{FONT}" fill="{TEXT}">\n'
        + "\n".join(parts)
        + "\n</g>\n</svg>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", action="store_true", help="only print the SVG, don't change files")
    args = parser.parse_args()

    svg = render_svg(collect())
    if args.print:
        print(svg)
        return

    SVG.parent.mkdir(exist_ok=True)
    SVG.write_text(svg, encoding="utf-8")

    block = (
        '<div align="center">\n'
        '<img src="assets/status.svg" alt="STATUS window" width="720">\n'
        "</div>"
    )
    text_ = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text_):
        sys.exit(f"{START} and {END} were not found in README.md")
    README.write_text(pattern.sub(lambda _: f"{START}\n{block}\n{END}", text_), encoding="utf-8")
    print("STATUS window updated")


if __name__ == "__main__":
    main()