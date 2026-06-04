"""
重建鏈 第 3 步：從 Unihan_IRGSources.txt 取 kTotalStrokes 補進 lexicon.db。

須先跑 build_lexicon.py（第 1 步）。提供短文字 v2 模型的 avg_stroke 特徵，
以及給不在 NAER/MOE 字表的字一個筆畫 fallback（strokes_lookup）。

資料來源：Unicode Unihan Database（開放，見 data/DATA.md）。
"""
import os
import re
import sqlite3
from pathlib import Path

_DATA_ROOT = Path(os.environ.get("READABILITY_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
UNIHAN = _DATA_ROOT / "unihan" / "Unihan_IRGSources.txt"
DB = _DATA_ROOT / "lexicon.db"

STROKE_RE = re.compile(r"^U\+([0-9A-F]+)\s+kTotalStrokes\s+(\d+)")

strokes: dict[str, int] = {}
for line in UNIHAN.read_text(encoding="utf-8").splitlines():
    if not line or line.startswith("#"):
        continue
    m = STROKE_RE.match(line)
    if m:
        codepoint = int(m.group(1), 16)
        n = int(m.group(2))
        strokes[chr(codepoint)] = n

print(f"Loaded {len(strokes):,} chars with stroke counts")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Add column if not exists
cur.execute("PRAGMA table_info(chars)")
cols = {row[1] for row in cur.fetchall()}
if "strokes" not in cols:
    cur.execute("ALTER TABLE chars ADD COLUMN strokes INTEGER")
    print("Added strokes column to chars table")

# Update NAER chars
naer_chars = cur.execute("SELECT char FROM chars").fetchall()
updates = []
for (ch,) in naer_chars:
    if ch in strokes:
        updates.append((strokes[ch], ch))
cur.executemany("UPDATE chars SET strokes=? WHERE char=?", updates)
print(f"Updated {len(updates)} chars in NAER chars table")

# Add column to moe_chars too
cur.execute("PRAGMA table_info(moe_chars)")
cols = {row[1] for row in cur.fetchall()}
if "strokes" not in cols:
    cur.execute("ALTER TABLE moe_chars ADD COLUMN strokes INTEGER")
    print("Added strokes column to moe_chars table")

moe_chars = cur.execute("SELECT char FROM moe_chars").fetchall()
updates = []
for (ch,) in moe_chars:
    if ch in strokes:
        updates.append((strokes[ch], ch))
cur.executemany("UPDATE moe_chars SET strokes=? WHERE char=?", updates)
print(f"Updated {len(updates)} chars in MOE chars table")

# 新表：所有 CJK 字的筆畫（給字面上不在 NAER/MOE 表的字 fallback）
cur.execute("CREATE TABLE IF NOT EXISTS strokes_lookup (char TEXT PRIMARY KEY, strokes INTEGER NOT NULL)")
cur.executemany(
    "INSERT OR REPLACE INTO strokes_lookup VALUES (?, ?)",
    [(ch, n) for ch, n in strokes.items()]
)
print(f"strokes_lookup: {len(strokes)} entries")

conn.commit()
conn.close()
print(f"Done. DB: {DB}")
