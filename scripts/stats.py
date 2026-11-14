"""Write a game-style STATUS window (commits, languages...) into README.md.

Run on GitHub Actions (needs GITHUB_TOKEN). Preview without changing README:
    GITHUB_TOKEN=xxx python3 scripts/stats.py --print
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

USER = "hamutaro-46"
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- STATS:START -->"
END = "<!-- STATS:END -->"

TOP_LANGS = 5   # number of languages to show
WIDTH = 34      # inner width of the window
BAR = 10        # length of the language bar


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


def width(text: str) -> int:
    """Display width (full-width characters count as 2)."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def row(text: str = "") -> str:
    return "│ " + text + " " * (WIDTH - 2 - width(text)) + " │"


def title(label: str, left: str = "├", right: str = "┤") -> str:
    head = f"─ {label} "
    return left + head + "─" * (WIDTH - len(head)) + right


def render(s: dict) -> str:
    lines = [
        title("STATUS", "┌", "┐"),
        row(f"NAME     {USER}"),
        row(f"SINCE    {s['since']}"),
        row(f"COMMITS  {s['commits']:<8}PRs    {s['prs']}"),
        row(f"REPOS    {s['repos']:<8}STARS  {s['stars']}"),
        title("LANGUAGES"),
    ]

    total = sum(s["langs"].values())
    top = sorted(s["langs"].items(), key=lambda x: -x[1])[:TOP_LANGS]
    if not top:
        lines.append(row("(no data yet)"))
    for name, size in top:
        pct = 100 * size / total
        filled = max(1, round(BAR * size / total))
        bar = "█" * filled + "░" * (BAR - filled)
        lines.append(row(f"{name[:11]:<11} {bar} {pct:5.1f}%"))

    lines.append("└" + "─" * WIDTH + "┘")
    return '<div align="center">\n<pre>\n' + "\n".join(lines) + "\n</pre>\n</div>"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", action="store_true", help="only print, don't change README")
    args = parser.parse_args()

    block = render(collect())
    if args.print:
        print(block)
        return

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        sys.exit(f"{START} and {END} were not found in README.md")
    README.write_text(pattern.sub(lambda _: f"{START}\n{block}\n{END}", text), encoding="utf-8")
    print("STATUS window updated")


if __name__ == "__main__":
    main()