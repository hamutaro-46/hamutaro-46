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

def render(state: dict) -> str:
    d = date.fromisoformat(state["date"])
    heading = state.get("title") or "⚔️ Today's Enemy"
    day = f"{d.year}/{d.month}/{d.day} ({WEEKDAYS[d.weekday()]})"
    alive = state["hp"] > 0
 
    if alive:
        headline = f'A wild {state["name"]} (Lv.{state["lv"]}) appeared!'
        action = (
            f'<p><a href="{FIGHT_URL}"><b>▶ FIGHT</b></a><br>\n'
            "<sub>Press FIGHT, then the green button. "
            "Reload this page in about 1 minute to see the damage!</sub></p>\n"
        )
    else:
        headline = f'{state["name"]} was defeated! 🎉'
        action = "<p><sub>A new enemy appears tomorrow at 6:00 (JST).</sub></p>\n"
 
    speech = ""
    if alive and state.get("speech"):
        speech = f'<p>💬 <i>{state["name"]}: "{state["speech"]}"</i></p>\n'
 
    log = ""
    if state.get("logs"):
        log = "<p><sub>" + "<br>\n".join(state["logs"]) + "</sub></p>\n"

    return (
        '<div align="center">\n'
        f"<h3>{heading}</h3>\n"
        f"<sub>{day}</sub>\n"
        f'<h1>{state["icon"]}</h1>\n'
        f"<p><b>{headline}</b><br>\n"
        f'<sub>Rarity {RARITY_LABEL[state["rarity"]]}</sub></p>\n'
        f'<p><code>HP {hp_bar(state["hp"], state["max_hp"])} '
        f'{state["hp"]}/{state["max_hp"]}</code></p>\n'
        "<table>\n"
        "<tr><th>Max HP</th><th>Type</th></tr>\n"
        f'<tr><td align="center">{state["max_hp"]}</td>'
        f'<td align="center">{state["type"]}</td></tr>\n'
        "</table>\n"
        f"{speech}"
        f"{action}"
        f"{log}"
        "</div>"
    )


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