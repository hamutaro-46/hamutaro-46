"""きょうの てき を README.md に 書きこむ スクリプト。
 
README.md の中の
    <!-- MONSTER:START -->
    <!-- MONSTER:END -->
の あいだを 毎日 書きかえる。
 
同じ日なら 何回 実行しても 同じ モンスターになる（日付を たねにしている）。
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
 
WEEKDAYS = "月火水木金土日"
 
# rarity: 1=よくでる 2=ときどき 3=レア
MONSTERS = [
    {
        "name": "バグスライム", "icon": "🟢", "rarity": 1, "lv": (1, 10),
        "type": "みず",
    },
    {
        "name": "タイポ・バット", "icon": "🦇", "rarity": 1, "lv": (1, 8),
        "type": "かぜ",
    },
    {
        "name": "セミコロン・スパイダー", "icon": "🕷️", "rarity": 1, "lv": (3, 12),
        "type": "やみ",
    },
    {
        "name": "コーヒーぎれ・ゴブリン", "icon": "☕", "rarity": 1, "lv": (2, 9),
        "type": "ねむけ",
    },
    {
        "name": "ヌルポ・ゴースト", "icon": "👻", "rarity": 2, "lv": (8, 20),
        "type": "むう",
    },
    {
        "name": "むげんループ・スネーク", "icon": "🐍", "rarity": 2, "lv": (10, 22),
        "type": "じかん",
    },
    {
        "name": "メモリリーク・ゾンビ", "icon": "🧟", "rarity": 2, "lv": (12, 25),
        "type": "どく",
    },
    {
        "name": "404・ミミック", "icon": "📦", "rarity": 2, "lv": (6, 18),
        "type": "まいご",
    },
    {
        "name": "かんきょうへんすう・ニンジャ", "icon": "🥷", "rarity": 2, "lv": (10, 24),
        "type": "かくれ",
    },
    {
        "name": "CORS・ウィザード", "icon": "🧙", "rarity": 2, "lv": (14, 28),
        "type": "けっかい",
    },
    {
        "name": "いぞんじごく・ゴーレム", "icon": "🗿", "rarity": 3, "lv": (25, 40),
        "type": "いわ",
    },
    {
        "name": "レガシーコード・リッチ", "icon": "💀", "rarity": 3, "lv": (30, 45),
        "type": "のろい",
    },
    {
        "name": "マージコンフリクト・ドラゴン", "icon": "🐉", "rarity": 3, "lv": (35, 50),
        "type": "ほのお",
    },
]
 
GOLDEN = {
    "name": "きんいろ バグスライム", "icon": "✨", "rarity": 5, "lv": (99, 99),
    "type": "ひかり", "weak": "なし",
    "title": "🌟 めったに あえない てき",
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
 
 
def render(today: date) -> str:
    monster, lv, hp = pick_monster(today)
    rng = random.Random(today.isoformat() + "line")
    line = rng.choice(monster["lines"])
    heading = monster.get("title", "⚔️ きょうの てき")
    day = f"{today.year}/{today.month}/{today.day}（{WEEKDAYS[today.weekday()]}）"
 
    return f"""<div align="center">
 
### {heading}
 
<sub>{day}</sub>
 
# {monster["icon"]}
 
**やせいの {monster["name"]}（Lv.{lv}）が あらわれた！**
 
<sub>レアど {RARITY_LABEL[monster["rarity"]]}</sub>
 
| HP | ぞくせい |
|:---:|:---:|
| {hp} | {monster["type"]}
 
> {monster["name"]}「{line}」
 
</div>"""
 
 
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
