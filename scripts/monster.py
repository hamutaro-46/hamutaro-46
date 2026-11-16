"""きょうの てき を README.md に 書きこむ スクリプト。

ためしに 別の日を 見たいときは:
    python scripts/monster.py --date 2026-12-24 --print
"""
 
import argparse
import random
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo
 
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
STATE = ROOT / "state.json"
START = "<!-- MONSTER:START -->"
END = "<!-- MONSTER:END -->"
 
REPO = "hamutaro-46/hamutaro-46"
ISSUE_BODY = (
    "⚠️ **Notice**\n"
    "Your GitHub username will be shown in the damage log on the profile "
    "and will remain on this issue.\n"


    "If that's OK, press the green button to attack!"
)
FIGHT_URL = (
    f"https://github.com/{REPO}/issues/new"
    f"?title=fight&body={quote(ISSUE_BODY)}"
)

MAX_LOGS = 4  # number of damage log lines to show

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
 
# rarity: 1=よくでる 2=ときどき 3=レア
MONSTERS = [
    {
        "name": "Bug Slime", "icon": "🟢", "rarity": 1, "lv": (1, 10),
        "type": "Water",
    },
    {
        "name": "Typo Bat", "icon": "🦇", "rarity": 1, "lv": (1, 8),
        "type": "Wind",
    },
    {
        "name": "Semicolon Spider", "icon": "🕷️", "rarity": 1, "lv": (3, 12),
        "type": "Dark",
    },
    {
        "name": "Out-of-Coffee Goblin", "icon": "☕", "rarity": 1, "lv": (2, 9),
        "type": "Sleepy",
    },
    {
        "name": "Null Pointer Ghost", "icon": "👻", "rarity": 2, "lv": (8, 20),
        "type": "Void",
    },
    {
        "name": "Infinite Loop Snake", "icon": "🐍", "rarity": 2, "lv": (10, 22),
        "type": "Time",
    },
    {
        "name": "Memory Leak Zombie", "icon": "🧟", "rarity": 2, "lv": (12, 25),
        "type": "Poison",
    },
    {
        "name": "404 Mimic", "icon": "📦", "rarity": 2, "lv": (6, 18),
        "type": "Lost",
    },
    {
        "name": "Env Variable Ninja", "icon": "🥷", "rarity": 2, "lv": (10, 24),
        "type": "Stealth",
    },
    {
        "name": "CORS Wizard", "icon": "🧙", "rarity": 2, "lv": (14, 28),
        "type": "Barrier",
    },
    {
        "name": "Dependency Hell Golem", "icon": "🗿", "rarity": 3, "lv": (25, 40),
        "type": "Rock",
    },
    {
        "name": "Legacy Code Lich", "icon": "💀", "rarity": 3, "lv": (30, 45),
        "type": "Curse",
    },
    {
        "name": "Merge Conflict Dragon", "icon": "🐉", "rarity": 3, "lv": (35, 50),
        "type": "Fire",
    },
]

GOLDEN = {
    "name": "Golden Bug Slime", "icon": "✨", "rarity": 5, "lv": (99, 99),
    "type": "Light", "weak": "None",
    "title": "🌟 A Rare Encounter",
}
 
RARITY_LABEL = {1: "★", 2: "★★", 3: "★★★", 4: "👑 ボス", 5: "🌟 でんせつ"}
RARITY_WEIGHT = {1: 60, 2: 30, 3: 10}
 
 
def pick_monster(today: date) -> tuple[dict, int, int]:
    rng = random.Random(today.isoformat())
 
    if rng.random() < 0.03:
        monster = GOLDEN
    else:
        weights = [RARITY_WEIGHT[m["rarity"]] for m in MONSTERS]
        monster = rng.choices(MONSTERS, weights=weights, k=1)[0]
 
    lv = rng.randint(*monster["lv"])
    hp = lv * rng.randint(8, 12) + rng.randint(0, 9)
    return monster, lv, hp

def spawn(today: date) -> dict:
    """Create today's enemy at full HP."""
    monster, lv, hp = pick_monster(today)
    speech = ""
    if monster.get("lines"):
        rng = random.Random(today.isoformat() + "line")
        speech = rng.choice(monster["lines"])
    return {
        "date": today.isoformat(),
        "name": monster["name"],
        "icon": monster["icon"],
        "rarity": monster["rarity"],
        "type": monster["type"],
        "title": monster.get("title", ""),
        "speech": speech,
        "lv": lv,
        "hp": hp,
        "max_hp": hp,
        "logs": [],
    }
 
def fight(state: dict, player: str) -> None:
    """Deal damage to the enemy. About 5-10 hits to defeat it."""
    if state["hp"] <= 0:
        return  # already defeated: keep "defeated by ..." message
 
    low = max(1, state["max_hp"] // 10)
    high = max(low, state["max_hp"] // 5)
    dmg = random.randint(low, high)
    critical = random.random() < 0.1
    if critical:
        dmg *= 2
 
    state["hp"] = max(0, state["hp"] - dmg)
    msg = f"{player} dealt {dmg} damage!"
    if critical:
        msg = "💥 Critical hit! " + msg
    if state["hp"] == 0:
        msg += f" {state['name']} was defeated by {player}!"
    logs = state.get("logs", [])
    state["logs"] = ([msg] + logs)[:MAX_LOGS]  # newest first


def hp_bar(now: int, max_hp: int, width: int = 10) -> str:
    """Turn HP into a bar of █ and ░ (e.g. ██████░░░░)."""
    filled = round(width * now / max_hp)
    if now > 0:
        filled = max(1, filled)  # keep at least 1 block while alive
    return "█" * filled + "░" * (width - filled)

# ---------- battle screen (SVG) ----------

BATTLE_SVG = ROOT / "assets" / "battle.svg"
FONT = "'Courier New', 'DejaVu Sans Mono', monospace"
SW, SH = 800, 460  # size of the battle screen

# Pixel-art sprites (16 dots wide).
#   . = empty   a = body   b = dark/outline   e = eyes   y = accent   w = white
SPRITES = {
    "Bug Slime": """
................
......aaaa......
....aaaaaaaa....
...aaawaaaaaa...
..aawwaaaaaaaa..
..aaaaaaaaaaaa..
.aaaaeaaaaeaaaa.
.aaaaeaaaaeaaaa.
.aaaaaaaaaaaaaa.
.aaaaaayyaaaaaa.
.baaaaaaaaaaaab.
..bbbbbbbbbbbb..
""",
    "Typo Bat": """
................
.b............b.
.bb..a....a..bb.
.bbb.aaaaaa.bbb.
.bbbbaeaaeabbbb.
.bbbbaaaaaabbbb.
.bbbbaawwaabbbb.
..bbb.aaaa.bbb..
...bb..aa..bb...
....b......b....
""",
    "Semicolon Spider": """
..a..........a..
...a........a...
a...a..aa..a...a
.a...aaaaaa...a.
..a.aaeaaeaa.a..
...aaaaaaaaaa...
aaaaaaayyaaaaaaa
a...aaaaaaaa...a
...a.aaaaaa.a...
..a...aaya...a..
.a....ayaa....a.
a..............a
""",
    "Out-of-Coffee Goblin": """
....w..w..w.....
.....w..w..w....
................
..bbbbbbbbbbb...
..baaaaaaaaab...
..baeaaaaeabbbb.
..baaaaaaaaab.b.
..baaayyaaaab.b.
..baaaaaaaaabbb.
..baaaaaaaaab...
...baaaaaaab....
....bbbbbbb.....
""",
    "Null Pointer Ghost": """
.....aaaaaa.....
...aaaaaaaaaa...
..aaaaaaaaaaaa..
..aaeeaaaaeeaa..
.aaaeeaaaaeeaaa.
.aaaaaaaaaaaaaa.
.aaaaaayyaaaaaa.
.aaaaaayyaaaaaa.
.aaaaaaaaaaaaaa.
.aaaaaaaaaaaaaa.
.aa.aaa..aaa.aa.
.a...a....a...a.
""",
    "Infinite Loop Snake": """
................
..aaaa....aaaa..
.aa..aa..aa..aa.
.a....aaaa....a.
.a....aaaa....a.
.aa..aa..aa..aa.
..aaaa....aaaa..
.............a..
...........aaaa.
..........aeaaay
...........aaaa.
""",
    "Memory Leak Zombie": """
....bbbbbbbb....
...baaaaaaaab...
..baaaaaaaaaab..
..baeeaaaaeeab..
..baeeaaaaeeab..
..baaaaabaaaab..
..baaaaaaaaaab..
..bawawawawaab..
...baaaaaaaab...
....bbbbbbbb....
.....y....y.....
....yy.y..y.yy..
""",
    "404 Mimic": """
..bbbbbbbbbbbb..
.baaaaaaaaaaaab.
.baaeeaaaaeeaab.
.baaaaayyaaaaab.
.bbbbbbyybbbbbb.
.bw.w.w..w.w.wb.
.b............b.
.b.w.w.w.w.w..b.
.baaaaaaaaaaaab.
.baaaaaaaaaaaab.
..bbbbbbbbbbbb..
""",
    "Env Variable Ninja": """
....bbbbbbbb....
...bbbbbbbbbb...
..bbbbbbbbbbbb..
..byyyyyyyyyybyy
..bbweebbweebb.y
..bbbbbbbbbbbb..
...bbbbbbbbbb...
..aabbbbbbbbaa..
..a.bbbbbbbb.a..
....bb....bb....
....bb....bb....
""",
    "CORS Wizard": """
.......y........
......aaa.......
.....aaaaa......
....aayaaaa.....
...aaaaaaaaa....
.bbbbbbbbbbbbb..
...wwwwwwwww....
...weewwweew....
...wwwwwwwww....
....wwwwwww.....
.....wwwww......
......www.......
""",
    "Dependency Hell Golem": """
...bbbbbbbbbb...
...baaaaaaaab...
...baeaaaaeab...
...baaayyaaab...
.bbbbbbbbbbbbbb.
baaaaaaaaaaaaaab
baabaaaaaaaabaab
baab.aaaaaa.baab
bbbb.aaaaaa.bbbb
.....aab.baa....
.....aab.baa....
....bbbb.bbbb...
""",
    "Legacy Code Lich": """
...y..y..y..y...
...yyyyyyyyyy...
...aaaaaaaaaa...
..aaaaaaaaaaaa..
..abbbaaaabbba..
..abebaaaabeba..
..aaaaaabaaaaa..
...aaaabbaaaa...
....awawawaa....
....aaaaaaaa....
.....wawawa.....
""",
    "Merge Conflict Dragon": """
..a.........a...
..aa.......aa...
...aaaaaaaaa....
..aaeaaaaaeaa...
..aaaaaaaaaaa...
...aaawwwaaa....
y...aawwwaa...y.
yy.aaaaaaaaa.yy.
.yyaaaaaaaaayy..
..yaaabbbaaay...
....aa...aa.....
...bbb...bbb....
""",
}
SPRITES["Golden Bug Slime"] = SPRITES["Bug Slime"]

#            a (body)   b (dark)   e (eyes)   y (accent) w (white)
PALETTES = {
    "Bug Slime":             ("#5ee07a", "#2e9e4a", "#16213a", "#ff6b8a", "#ffffff"),
    "Typo Bat":              ("#7d6bd6", "#3d2f7a", "#ffd84a", "#ff5a6e", "#ffffff"),
    "Semicolon Spider":      ("#b48ef0", "#6b4fb0", "#ff4f6d", "#ffd84a", "#ffffff"),
    "Out-of-Coffee Goblin":  ("#f2e6d0", "#7a4e2d", "#2b1a10", "#c94f4f", "#b9b9c9"),
    "Null Pointer Ghost":    ("#e8ecff", "#9aa3c7", "#1b1f3a", "#1b1f3a", "#ffffff"),
    "Infinite Loop Snake":   ("#4fd1c5", "#22867c", "#ff4f6d", "#ff4f6d", "#ffffff"),
    "Memory Leak Zombie":    ("#8fbf6a", "#4c6e35", "#ffef5a", "#b06bff", "#e8e8e8"),
    "404 Mimic":             ("#c9884a", "#6b4422", "#ff4f6d", "#ffd84a", "#ffffff"),
    "Env Variable Ninja":    ("#3a3f5c", "#1d2033", "#ffffff", "#ff4f6d", "#f2d5b6"),
    "CORS Wizard":           ("#4a5ee8", "#2a347a", "#1b1f3a", "#ffd84a", "#e8e8f0"),
    "Dependency Hell Golem": ("#9a8f86", "#5a524c", "#ff8a3a", "#ff4f3a", "#ffffff"),
    "Legacy Code Lich":      ("#e9e4d4", "#3a2f55", "#7cf0ff", "#ffd84a", "#ffffff"),
    "Merge Conflict Dragon": ("#e8503a", "#8a2a1e", "#ffd84a", "#ff9a3a", "#ffe9c4"),
    "Golden Bug Slime":      ("#ffd84a", "#c99a1a", "#3a2a00", "#ff8ab0", "#fff8d0"),
}

TYPE_COLOR = "#b39dfa"
TITLE_COLOR = "#ffd54a"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_text(x, y, s, size=20, color="#ffffff", anchor="start", bold=False, extra=""):
    weight = ' font-weight="bold"' if bold else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
        f'text-anchor="{anchor}"{weight}{extra}>{esc(s)}</text>'
    )


def battle_window(x, y, w, h):
    """White double-line window like classic RPGs."""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#000000" '
        f'stroke="#ffffff" stroke-width="4"/>'
        f'<rect x="{x + 7}" y="{y + 7}" width="{w - 14}" height="{h - 14}" rx="5" '
        f'fill="none" stroke="#555566" stroke-width="1.5"/>'
    )


def wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def sprite(name: str, cx: int, bottom: int, dot: int, faded: bool) -> list[str]:
    rows = [r for r in SPRITES.get(name, SPRITES["Bug Slime"]).strip("\n").split("\n")]
    colors = dict(zip("abeyw", PALETTES.get(name, PALETTES["Bug Slime"])))
    left = cx - len(rows[0]) * dot // 2
    top = bottom - len(rows) * dot
    out = [f'<g opacity="{0.25 if faded else 1}">']
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c in colors:
                out.append(
                    f'<rect x="{left + i * dot}" y="{top + j * dot}" '
                    f'width="{dot}" height="{dot}" fill="{colors[c]}"/>'
                )
    out.append("</g>")
    return out


def render_svg(state: dict) -> str:
    d = date.fromisoformat(state["date"])
    alive = state["hp"] > 0
    rng = random.Random(state["date"] + "stars")
    p = []

    # background: night sky and ground
    p.append(f'<rect width="{SW}" height="{SH}" fill="#0f0f1e"/>')
    p.append(f'<rect y="{SH // 2}" width="{SW}" height="{SH // 2}" fill="#161630"/>')
    for _ in range(45):
        x, y = rng.randrange(0, SW), rng.randrange(0, SH)
        p.append(f'<rect x="{x}" y="{y}" width="3" height="3" fill="#ffffff" '
                 f'opacity="{rng.choice([0.15, 0.25, 0.4])}"/>')

    # HP window (top left)
    p.append(battle_window(22, 22, 304, 68))
    p.append(svg_text(44, 66, "HP", 20, bold=True))
    ratio = state["hp"] / state["max_hp"]
    color = "#43f07a" if ratio > 0.5 else "#ffd84a" if ratio > 0.2 else "#ff4f6d"
    filled = round(10 * ratio)
    if alive:
        filled = max(1, filled)
    for i in range(10):
        p.append(f'<rect x="{88 + i * 15}" y="{48}" width="11" height="20" '
                 f'fill="{color if i < filled else "#2a2a3e"}"/>')
    p.append(svg_text(304, 66, f'{state["hp"]}/{state["max_hp"]}', 17, anchor="end"))

    # date window (top right)
    p.append(battle_window(474, 22, 304, 68))
    day = f"{d.year}/{d.month}/{d.day} {WEEKDAYS[d.weekday()].upper()}"
    p.append(svg_text(626, 64, day, 21, anchor="middle", bold=True))

    # monster name and type
    p.append(svg_text(SW // 2, 128, f'{state["name"].upper()} Lv.{state["lv"]}',
                      24, TITLE_COLOR, "middle", True))
    sub = "★ RARE ENCOUNTER ★" if state.get("title") else f'— {state["type"].upper()} TYPE —'
    p.append(svg_text(SW // 2, 156, sub, 15, TYPE_COLOR, "middle"))

    # monster sprite and its shadow
    p.append(f'<ellipse cx="{SW // 2}" cy="{298}" rx="130" ry="16" fill="#0a0a16"/>')
    p += sprite(state["name"], SW // 2, 290, 10, faded=not alive)

    # message window (bottom left)
    p.append(battle_window(22, 318, 522, 120))
    logs = state.get("logs", [])
    if not alive:
        message = f'{state["name"]} was defeated!'
        key = f'{state["name"]} was defeated by '
        if logs and key in logs[0]:
            message = logs[0][logs[0].index(key):]  # "X was defeated by Y!"
    elif logs:
        message = logs[0]
    else:
        message = f'A wild {state["name"]} appeared!'
    message = message.replace("💥 ", "")
    for i, line in enumerate(wrap(message, 34)[:2]):
        p.append(svg_text(48, 360 + i * 30, line, 20))
    stars = "★" * min(state["rarity"], 5) + "☆" * max(0, 5 - state["rarity"])
    p.append(svg_text(48, 420, f'TYPE: {state["type"].upper()}  RARITY: {stars}', 14, TYPE_COLOR))
    p.append('<polygon points="508,410 524,410 516,422" fill="#ffffff"/>')

    # command window (bottom right)
    p.append(battle_window(558, 318, 220, 120))
    if alive:
        p.append('<polygon points="606,366 606,390 624,378" fill="#ffffff"/>')
        p.append(svg_text(638, 387, "FIGHT", 26, bold=True))
    else:
        p.append(svg_text(668, 372, "VICTORY!", 22, TITLE_COLOR, "middle", True))
        p.append(svg_text(668, 404, "next: 6:00 JST", 14, "#9999aa", "middle"))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}" height="{SH}" '
        f'viewBox="0 0 {SW} {SH}">\n'
        f'<defs><clipPath id="c"><rect width="{SW}" height="{SH}" rx="14"/></clipPath></defs>\n'
        f'<g clip-path="url(#c)" font-family="{FONT}" shape-rendering="crispEdges">\n'
        + "\n".join(p)
        + "\n</g>\n</svg>\n"
    )


def render(state: dict) -> str:
    """HTML for README: the battle screen image + FIGHT link + logs."""
    alive = state["hp"] > 0
    # ?v=... makes GitHub fetch the new image after each attack
    version = f'{state["date"]}-{state["hp"]}'
    img = f'<img src="assets/battle.svg?v={version}" alt="Today\'s enemy: {state["name"]}" width="800">'

    if alive:
        top = f'<a href="{FIGHT_URL}">{img}</a>\n'
        action = (
            f'<p><a href="{FIGHT_URL}"><b>▶ FIGHT</b></a><br>\n'
            "<sub>Press FIGHT (or the picture), then the green button. "
            "Reload this page in about 1 minute to see the damage!</sub></p>\n"
        )
    else:
        top = img + "\n"
        action = "<p><sub>A new enemy appears tomorrow at 6:00 (JST).</sub></p>\n"

    log = ""
    if state.get("logs"):
        log = "<p><sub>" + "<br>\n".join(state["logs"]) + "</sub></p>\n"

    return '<div align="center">\n' + top + action + log + "</div>"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD (to preview another day)")
    parser.add_argument("--print", action="store_true", help="only print, don't change files")
    parser.add_argument("--fight", metavar="PLAYER", help="attack the current enemy")
    args = parser.parse_args()
 
    today = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(ZoneInfo("Asia/Tokyo")).date()
    )
 
    if args.fight:
        if STATE.exists():
            state = json.loads(STATE.read_text(encoding="utf-8"))
            # old format had a single "log" string
            old = state.pop("log", "")
            state.setdefault("logs", [old] if old else [])
        else:
            state = spawn(today)
        fight(state, args.fight)
    else:
        state = spawn(today)
 
    block = render(state)
 
    if args.print:
        print(block)
        return
 
    BATTLE_SVG.parent.mkdir(exist_ok=True)
    BATTLE_SVG.write_text(render_svg(state), encoding="utf-8")

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        sys.exit(f"{START} and {END} were not found in README.md")
 
    new_text = pattern.sub(lambda _: f"{START}\n{block}\n{END}", text)
    README.write_text(new_text, encoding="utf-8")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
 
    if args.fight:
        print(f"{args.fight}: {state['logs'][0] if state['logs'] else ''}")
    else:
        print(f"{today}: README updated")
 
 
if __name__ == "__main__":
    main()