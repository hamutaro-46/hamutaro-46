"""きょうの てき を README.md に 書きこむ スクリプト。

ためしに 別の日を 見たいときは:
    python scripts/monster.py --date 2026-12-24 --print
"""
 
import argparse
import random
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
 
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- MONSTER:START -->"
END = "<!-- MONSTER:END -->"
 
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
 
# rarity: 1=よくでる 2=ときどき 3=レア
# セリフを 出したいときは "lines": ["セリフ1", "セリフ2"] を 足す
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
 
def hp_bar(now: int, max_hp: int, width: int = 10) -> str:
    """HP を █ と ░ の バーに する（例: ██████░░░░）"""
    filled = round(width * now / max_hp)
    return "█" * filled + "░" * (width - filled)

def render(today: date) -> str:
    monster, lv, hp = pick_monster(today)
    # セリフ（"lines"）が ある モンスターだけ セリフを 表示する
    speech = ""
    if monster.get("lines"):
        rng = random.Random(today.isoformat() + "line")
        line = rng.choice(monster["lines"])
        speech = f'<p>💬 <i>{monster["name"]}「{line}」</i></p>\n'
    heading = monster.get("title", "⚔️ きょうの てき")
    day = f"{today.year}/{today.month}/{today.day}（{WEEKDAYS[today.weekday()]}）"
 
    return (
        '<div align="center">\n'
        f'<h3>{heading}</h3>\n'
        f'<sub>{day}</sub>\n'
        f'<h1>{monster["icon"]}</h1>\n'
        f'<p><b>やせいの {monster["name"]}（Lv.{lv}）が あらわれた！</b><br>\n'
        f'<sub>レア度 {RARITY_LABEL[monster["rarity"]]}</sub></p>\n'
        f'<p><code>HP {hp_bar(hp, hp)} {hp}/{hp}</code></p>\n'
        '<table>\n'
        '<tr><th>HP</th><th>ぞくせい</th></tr>\n'
        f'<tr><td align="center">{hp}</td><td align="center">{monster["type"]}</td></tr>\n'
        '</table>\n'
        f'{speech}'
        '</div>'
    )
 


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD（ためしに 別の日を 見るとき）")
    parser.add_argument("--print", action="store_true", help="README を かえずに 表示だけする")
    args = parser.parse_args()
 
    today = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(ZoneInfo("Asia/Tokyo")).date()
    )
    block = render(today)
 
    if args.print:
        print(block)
        return
 
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        sys.exit(f"README.md に {START} と {END} が みつかりません")
 
    new_text = pattern.sub(lambda _: f"{START}\n{block}\n{END}", text)
    README.write_text(new_text, encoding="utf-8")
    print(f"{today}: README を こうしんしました")
 
 
if __name__ == "__main__":
    main()