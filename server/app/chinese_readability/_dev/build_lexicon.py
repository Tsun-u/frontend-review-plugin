"""
Build unified lexicon SQLite database from NAER + MOE sources.

L1-L4 mapping (verified from NAER 使用手冊精華版 p.25):
  L1 = TBCL 1-2 級 (基礎初級)         母語者: 國小~國中可讀
  L2 = TBCL 3-4 級 (基礎高級 + 進階)  母語者: 國中~高中可讀
  L3 = TBCL 5-6 級 (進階高級 + 精熟)  母語者: 高中~大學可讀
  L4 = TBCL 7 級   (精熟高級)         母語者: 大學以上

星號級 (1*, 2*, 3*, 4*) = 同等級內較難版，不跨 L 級。
"""
import os
import pandas as pd
import sqlite3
import re
from pathlib import Path

# 資料目錄：預設本套件 data/，可用環境變數 READABILITY_DATA_DIR 覆寫
_DATA_ROOT = Path(os.environ.get("READABILITY_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
DATA = _DATA_ROOT / "naer"
DB_PATH = _DATA_ROOT / "lexicon.db"

TBCL_RE = re.compile(r"第(\d+)(\*?)級")

def parse_ji(ji_text):
    m = TBCL_RE.match(str(ji_text))
    if not m:
        return None, None
    return int(m.group(1)), bool(m.group(2))

def map_level(ji):
    if ji in (1, 2): return "L1"
    if ji in (3, 4): return "L2"
    if ji in (5, 6): return "L3"
    if ji == 7: return "L4"
    return None

if DB_PATH.exists():
    DB_PATH.unlink()
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("Building schema...")
cur.executescript("""
CREATE TABLE chars (
    char TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    tbcl_deng TEXT,
    tbcl_ji INTEGER,
    tbcl_substar INTEGER,
    written_freq REAL,
    spoken_freq REAL,
    in_moe_4808 INTEGER
);

CREATE TABLE words (
    word TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    tbcl_deng TEXT,
    tbcl_ji INTEGER,
    tbcl_substar INTEGER,
    situation TEXT,
    written_freq REAL,
    spoken_freq REAL,
    bopomofo TEXT,
    pinyin TEXT
);

CREATE TABLE word_freq (
    word TEXT PRIMARY KEY,
    written_freq REAL,
    spoken_freq REAL,
    news_freq REAL,
    avg_freq REAL
);

CREATE TABLE moe_chars (
    char TEXT PRIMARY KEY,
    moe_id TEXT
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX idx_chars_level ON chars(level);
CREATE INDEX idx_words_level ON words(level);
""")

print("Loading MOE 4808 chars...")
moe = pd.read_excel(DATA / "moe_4808_chars.ods", engine="odf")
moe_set = set(moe["常用字"])
moe_rows = [(c, mid) for c, mid in zip(moe["常用字"], moe["教育部字號"])]
cur.executemany("INSERT INTO moe_chars VALUES (?, ?)", moe_rows)
print(f"  -> {len(moe_rows)} MOE chars inserted")

print("Loading NAER hanzi table...")
hanzi = pd.read_excel(DATA / "naer_hanzi_table.xlsx")
char_rows = []
for _, r in hanzi.iterrows():
    ji, star = parse_ji(r["級別"])
    if ji is None:
        continue
    level = map_level(ji)
    char_rows.append((
        r["漢字"],
        level,
        r["等別"],
        ji,
        1 if star else 0,
        float(r["書面字頻（每百萬字）"]) if pd.notna(r["書面字頻（每百萬字）"]) else None,
        float(r["口語字頻（每百萬字）"]) if pd.notna(r["口語字頻（每百萬字）"]) else None,
        1 if r["漢字"] in moe_set else 0,
    ))
cur.executemany(
    "INSERT INTO chars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    char_rows
)
print(f"  -> {len(char_rows)} NAER chars inserted")

print("Loading NAER 14452 words...")
words = pd.read_excel(DATA / "naer_14452_words.xlsx")
word_rows = []
seen = set()
for _, r in words.iterrows():
    ji, star = parse_ji(r["ji"])
    if ji is None:
        continue
    level = map_level(ji)
    # 處理 "爸爸/爸" 這種多形式 — 拆開分別插入，但避免重複
    forms = str(r["word"]).split("/")
    for w in forms:
        w = w.strip()
        if not w or w in seen:
            continue
        seen.add(w)
        word_rows.append((
            w,
            level,
            r["deng"],
            ji,
            1 if star else 0,
            r.get("situation"),
            float(r["wfreq"]) if pd.notna(r["wfreq"]) else None,
            float(r["sfreq"]) if pd.notna(r["sfreq"]) else None,
            r.get("bopomofo"),
            r.get("pinyin"),
        ))
cur.executemany(
    "INSERT INTO words VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    word_rows
)
print(f"  -> {len(word_rows)} NAER words inserted (after splitting variants)")

print("Loading NAER common word freq (163701 rows)...")
freq = pd.read_excel(DATA / "naer_common_word_freq.xlsx")
freq.columns = [c.replace("\n", "_") for c in freq.columns]
freq_rows = []
seen_freq = set()
for _, r in freq.iterrows():
    w = str(r["詞"]).strip()
    if not w or w in seen_freq:
        continue
    seen_freq.add(w)
    freq_rows.append((
        w,
        float(r["書面語_每百萬詞頻"]) if pd.notna(r["書面語_每百萬詞頻"]) else None,
        float(r["口語_每百萬詞頻"]) if pd.notna(r["口語_每百萬詞頻"]) else None,
        float(r["新聞_每百萬詞頻"]) if pd.notna(r["新聞_每百萬詞頻"]) else None,
        float(r["每百萬詞頻_(平均)"]) if pd.notna(r["每百萬詞頻_(平均)"]) else None,
    ))
cur.executemany(
    "INSERT INTO word_freq VALUES (?, ?, ?, ?, ?)",
    freq_rows
)
print(f"  -> {len(freq_rows)} freq rows inserted")

# Metadata
cur.executemany(
    "INSERT INTO meta VALUES (?, ?)",
    [
        ("schema_version", "1"),
        ("source_naer_words", "14452詞語表202504.xlsx"),
        ("source_naer_hanzi", "臺灣華語文能力基準漢字表_111-09-20.xlsx"),
        ("source_naer_freq", "通用詞頻表 - 定稿1141208.xlsx"),
        ("source_moe", "教育部4808個常用字.ods"),
        ("level_mapping", "L1=TBCL 1-2; L2=TBCL 3-4; L3=TBCL 5-6; L4=TBCL 7"),
        ("star_meaning", "同等級內較難版，不跨 L 級"),
    ]
)

conn.commit()

# Summary
print()
print("=" * 60)
print("Summary")
print("=" * 60)
for tbl in ["chars", "words", "word_freq", "moe_chars"]:
    n = cur.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
    print(f"  {tbl}: {n:,}")

print()
print("Level distribution (chars):")
for lvl, n in cur.execute("SELECT level, count(*) FROM chars GROUP BY level ORDER BY level"):
    print(f"  {lvl}: {n}")

print()
print("Level distribution (words):")
for lvl, n in cur.execute("SELECT level, count(*) FROM words GROUP BY level ORDER BY level"):
    print(f"  {lvl}: {n}")

print()
print(f"DB written to: {DB_PATH}")
print(f"DB size: {DB_PATH.stat().st_size / 1024:.1f} KB")

conn.close()
