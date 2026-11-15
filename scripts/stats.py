"""Draw an RPG-menu style STATUS window (commits, languages...) as an SVG
and show it in README.md.

Run on GitHub Actions (needs GITHUB_TOKEN). Preview without changing files:
    GITHUB_TOKEN=xxx python3 scripts/stats.py --print
"""

import argparse
import json
import os
import random
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

def text(x: int, y: int, s: str, anchor: str = "start", size: int = 20) -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">'
        f"{escape(s)}</text>"
    )


def label_value(x: int, w: int, y: int, label: str, value: str) -> str:
    """Label on the left, value on the right (like 'Level ... 2')."""
    return text(x + 24, y, label) + text(x + w - 24, y, value, "end")


# ---------- draw the RPG field behind the windows ----------

W, H = 760, 396   # whole image size
P = 4             # size of one "pixel" in the pixel art
PATH_X, PATH_W = 362, 36   # dirt road between the two windows

GRASS = "#6cc644"
GRASS_DARK = "#4fa832"
GRASS_LIGHT = "#8ad65c"
ROAD = "#d8b878"
ROAD_DARK = "#b8955a"
LEAF = "#2e8b3a"
LEAF_LIGHT = "#4cb050"
LEAF_DARK = "#1f6328"
TRUNK = "#7a5230"
FLOWERS = ["#ffffff", "#ff7aa8", "#ffd84a", "#7ec8ff"]


def px(x: int, y: int, color: str, w: int = 1, h: int = 1) -> str:
    """One block of pixel art (w x h pixels)."""
    return f'<rect x="{x}" y="{y}" width="{w * P}" height="{h * P}" fill="{color}"/>'


def on_road(x: int, w: int = 0) -> bool:
    return x + w > PATH_X - 4 and x < PATH_X + PATH_W + 4


def tree(cx: int, base: int) -> list[str]:
    """A round pixel-art tree whose trunk stands on y=base."""
    out = [f'<ellipse cx="{cx}" cy="{base}" rx="24" ry="6" fill="{GRASS_DARK}"/>']
    out.append(px(cx - 6, base - 18, TRUNK, 3, 5))
    r = 6  # canopy radius in pixels
    top = base - 18 - (2 * r - 1) * P
    for j in range(2 * r):
        for i in range(2 * r):
            dx, dy = i - r + 0.5, j - r + 0.5
            if dx * dx + dy * dy > r * r:
                continue
            color = LEAF
            if dx + dy < -r * 0.7:
                color = LEAF_LIGHT       # light from the upper left
            elif dx + dy > r * 0.8:
                color = LEAF_DARK        # shadow on the lower right
            out.append(px(cx - r * P + i * P, top + j * P, color))
    return out


def scene() -> list[str]:
    rng = random.Random("hamutaro-field")  # same field every day
    out = [f'<rect width="{W}" height="{H}" fill="{GRASS}"/>']

    # grass texture
    for _ in range(260):
        x = rng.randrange(0, W, P)
        y = rng.randrange(0, H, P)
        if on_road(x):
            continue
        if rng.random() < 0.7:
            out.append(px(x, y, GRASS_DARK))
            out.append(px(x + 2 * P, y, GRASS_DARK))
            out.append(px(x + P, y + P, GRASS_DARK))
        else:
            out.append(px(x, y, GRASS_LIGHT))

    # dirt road from top to bottom
    out.append(f'<rect x="{PATH_X}" y="0" width="{PATH_W}" height="{H}" fill="{ROAD}"/>')
    for _ in range(40):
        x = rng.randrange(PATH_X + P, PATH_X + PATH_W - P, P)
        y = rng.randrange(0, H, P)
        out.append(px(x, y, ROAD_DARK))

    # flowers
    for _ in range(36):
        x = rng.randrange(8, W - 16, P)
        y = rng.randrange(4, H - 16, P)
        if on_road(x, 3 * P):
            continue
        petal = rng.choice(FLOWERS)
        out += [
            px(x + P, y, petal), px(x, y + P, petal),
            px(x + 2 * P, y + P, petal), px(x + P, y + 2 * P, petal),
            px(x + P, y + P, "#ffcc33"),
        ]

    # a row of trees along the bottom (leave the road open)
    for cx in range(28, W, 56):
        if not on_road(cx - 26, 52):
            out += tree(cx, H - 14)
    return out


def window(x: int, y: int, w: int, h: int) -> str:
    shadow = (
        f'<rect x="{x + 5}" y="{y + 6}" width="{w}" height="{h}" rx="10" '
        f'fill="#000000" fill-opacity="0.35"/>'
    )
    return shadow + (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
        f'fill="{BG}" stroke="{LINE}" stroke-width="4"/>'
    )


def render_svg(s: dict) -> str:
    parts = []
    WY, WH = 24, 284  # top and height of the windows

    # left: character status
    x, y, w, h = 24, WY, 326, WH
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
    x, y, w, h = 410, WY, 326, WH
    parts.append(window(x, y, w, h))
    parts.append(text(x + 24, y + 42, "Languages", size=22))

    total = sum(s["langs"].values())
    top = sorted(s["langs"].items(), key=lambda kv: -kv[1])[:TOP_LANGS]
    if not top:
        parts.append(text(x + 24, y + 90, "(no data yet)"))
    bar_x, bar_w = x + 148, 100
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
        f'<defs><clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath></defs>\n'
        f'<g clip-path="url(#frame)" shape-rendering="crispEdges">\n'
        + "\n".join(scene())
        + "\n</g>\n"
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
        '<img src="assets/status.svg" alt="STATUS window" width="760">\n'
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