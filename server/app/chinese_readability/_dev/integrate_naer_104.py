"""
重建鏈 第 2 步：整合 NAER 民國 100-104 年常用語詞調查資料進 lexicon.db。

須先跑 build_lexicon.py（第 1 步）建好 lexicon.db，再跑本腳本。

新增三個 table（供短文字 v2 supervised 模型的 avg_topic_coverage / avg_log_freq 特徵使用）：
  - naer_104_char_freq        (字頻)
  - naer_104_word_freq        (多音節詞頻)
  - naer_104_topic_coverage   (跨主題高頻詞，含 5 領域分佈)

資料來源見 data/DATA.md（國家教育研究院，著作權保留，需自行取得）。
"""
import os
import pandas as pd
import sqlite3
from pathlib import Path

# 資料目錄：預設本套件 data/，可用環境變數 READABILITY_DATA_DIR 覆寫
_DATA_ROOT = Path(os.environ.get("READABILITY_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
DATA = _DATA_ROOT / "naer_100_104"
DB = _DATA_ROOT / "lexicon.db"

if not DB.exists():
    raise SystemExit(f"找不到 {DB}，請先執行 build_lexicon.py 建立 lexicon.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. 字頻表
print("Loading 104 char_freq...")
df_c = pd.read_excel(DATA / "104_char_freq.xls")
df_c.columns = [c.replace("\n", "") for c in df_c.columns]
cur.executescript("""
DROP TABLE IF EXISTS naer_104_char_freq;
CREATE TABLE naer_104_char_freq (
    char TEXT PRIMARY KEY,
    rank INTEGER NOT NULL,
    freq INTEGER NOT NULL
);
""")
rows = [(r["字"], int(r["字頻序位"]), int(r["字頻"])) for _, r in df_c.iterrows()]
cur.executemany("INSERT INTO naer_104_char_freq VALUES (?, ?, ?)", rows)
print(f"  -> {len(rows)} chars")

# 2. 多音節詞頻
print("Loading 104 word_freq (multi-syllable)...")
df_w = pd.read_excel(DATA / "104_word_freq.xls", sheet_name="附錄19_多音節詞頻統計")
df_w.columns = [c.replace("\n", "").replace("多音詞序號", "序號") for c in df_w.columns]
cur.executescript("""
DROP TABLE IF EXISTS naer_104_word_freq;
CREATE TABLE naer_104_word_freq (
    word TEXT PRIMARY KEY,
    rank INTEGER NOT NULL,
    freq INTEGER NOT NULL
);
""")
seen = set()
rows = []
for _, r in df_w.iterrows():
    w = str(r["詞彙"]).strip()
    if not w or w in seen:
        continue
    seen.add(w)
    rows.append((w, int(r["序號"]), int(r["詞頻"])))
cur.executemany("INSERT INTO naer_104_word_freq VALUES (?, ?, ?)", rows)
print(f"  -> {len(rows)} multi-syllable words")

# 3. 跨主題高頻詞表
print("Loading 104 topic_coverage...")
df_t = pd.read_excel(DATA / "104_high_freq_multi_topic.xls")
df_t.columns = [c.replace("\n", "") for c in df_t.columns]
cur.executescript("""
DROP TABLE IF EXISTS naer_104_topic_coverage;
CREATE TABLE naer_104_topic_coverage (
    word TEXT PRIMARY KEY,
    total_freq INTEGER NOT NULL,
    topics_count INTEGER NOT NULL,
    freq_lifestyle INTEGER,
    freq_politics INTEGER,
    freq_science INTEGER,
    freq_arts INTEGER,
    freq_finance INTEGER
);
""")
rows = []
seen = set()
for _, r in df_t.iterrows():
    w = str(r["詞"]).strip()
    if not w or w in seen:
        continue
    seen.add(w)
    rows.append((
        w,
        int(r["詞頻"]),
        int(r["出現領域數"]),
        int(r.get("生活與時尚詞頻", 0) or 0),
        int(r.get("法政軍事詞頻", 0) or 0),
        int(r.get("科學詞頻", 0) or 0),
        int(r.get("文教藝術詞頻", 0) or 0),
        int(r.get("財經與時事詞頻", 0) or 0),
    ))
cur.executemany(
    "INSERT INTO naer_104_topic_coverage VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
)
print(f"  -> {len(rows)} cross-topic high-freq words")

cur.executescript("""
CREATE INDEX IF NOT EXISTS idx_char104_rank ON naer_104_char_freq(rank);
CREATE INDEX IF NOT EXISTS idx_word104_rank ON naer_104_word_freq(rank);
CREATE INDEX IF NOT EXISTS idx_topic_count ON naer_104_topic_coverage(topics_count);
""")
conn.commit()
conn.close()
print(f"\nDone. DB: {DB} ({DB.stat().st_size / 1024 / 1024:.1f} MB)")
