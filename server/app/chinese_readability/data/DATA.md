# 中文可讀性資料與重建說明

中文可讀性功能的**字表詞頻資料**與**模型權重**未隨 repo 散布，原因有二：

1. NAER／教育部的字表詞頻資料著作權保留（見下方各來源），不可轉散布。
2. Unihan、`lexicon.db` 等檔案較大，不適合進 git。

斷詞用的 CKIP Transformers 模型不在此列——它是開源套件，首次執行自動從 HuggingFace 下載。

> 沒有 `lexicon.db` 與模型權重時，中文可讀性 endpoint 無法運作；其餘功能（Lighthouse / WCAG / DeepGaze / Nielsen / 英文可讀性）不受影響。

## 中文可讀性技術概覽（v2.0）

- **斷詞**：CKIP Transformers（`bert-base`，CPU）。
- **短文字（< 50 中文字，UI 場景主路徑）**：`tbcl_supervised_v2` — CKIP 斷詞 + 8 個特徵 + RandomForest 三分類（L1–L3）。**模型是用人工標註的 UI 字串語料訓練的**；NAER／教育部／Unihan 資料是用來「抽特徵」，不是訓練標籤來源。
- **長文字（≥ 200 中文字）**：`svm_sung2014_v1` — Sung et al. (2014) 復刻的 31 特徵 SVM。
- **fallback**：`tbcl_rules_v1` — 舊版 TBCL 三等七級 level lookup，僅在 supervised 模型缺檔時退用。

## 需要的原始資料

下載後依各表「放置檔名」改名、放進對應子目錄（相對 `server/app/chinese_readability/data/`）。

### `data/naer/` — NAER TBCL 與教育部常用字

| 放置檔名 | 內容 | 來源 | 授權 |
|---|---|---|---|
| `naer_hanzi_table.xlsx` | TBCL 漢字表 | [國教院 coct 文件下載](https://coct.naer.edu.tw/page.jsp?ID=41) | 國教院版權所有 |
| `naer_14452_words.xlsx` | TBCL 三等七級詞語表 | 同上 | 同上 |
| `naer_common_word_freq.xlsx` | TBCL 通用詞頻表 | 同上 | 同上 |
| `moe_4808_chars.ods` | 教育部常用國字 4808 | 教育部（搜尋「常用國字標準字體表」）| 教育部版權 |

> NAER 資料：官網標示「國家教育研究院版權所有 ©2023 All rights reserved」，開放下載供使用，但著作權保留。本專案不隨附，請自行下載並於使用時標註來源（國家教育研究院）。

### `data/naer_100_104/` — NAER 常用語詞調查（民國 100–104 年）

| 放置檔名 | 內容 |
|---|---|
| `104_char_freq.xls` | 104 年字頻 |
| `104_word_freq.xls` | 104 年多音節詞頻（sheet「附錄19_多音節詞頻統計」）|
| `104_high_freq_multi_topic.xls` | 104 年跨主題高頻詞 |

來源：國家教育研究院《一○○至一○四年常用語詞調查報告書》
- [報告書（上）](https://teric.naer.edu.tw/wSite/ct?mp=teric_b&xItem=2037390&ctNode=645)
- [報告書（下）](https://teric.naer.edu.tw/wSite/ct?mp=teric_b&xItem=2037392&ctNode=645)

授權：國教院版權所有。（原研究下載用的 `coct2.naer.edu.tw` 技術報告站已停用，請以 teric／國教院最新系統為準。）

### `data/unihan/` — Unicode 筆畫

| 放置檔名 | 內容 | 來源 | 授權 |
|---|---|---|---|
| `Unihan_IRGSources.txt` | CJK 字筆畫（kTotalStrokes）| [Unicode Unihan.zip](https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip) 解壓取出 | Unicode License（開放）|

## 重建 lexicon.db（三步，依序執行）

> 重建腳本路徑已對齊套件慣例、語法驗證通過；端到端完整重建尚未實跑驗證——若重建過程遇到問題，歡迎回報 issue。

```bash
cd server/app/chinese_readability
python _dev/build_lexicon.py        # 第 1 步：TBCL 字/詞表 + 通用詞頻 + 教育部 4808
python _dev/integrate_naer_104.py   # 第 2 步：NAER 104 字頻/詞頻/跨主題
python _dev/add_strokes.py          # 第 3 步：Unihan 筆畫
```

資料放別處時，用環境變數覆寫資料根目錄：

```bash
READABILITY_DATA_DIR=/path/to/data python _dev/build_lexicon.py
```

各資料對應的特徵用途：

| 資料 → 表 | 短文字 v2 主路徑 | v1 fallback |
|---|---|---|
| 通用詞頻 → `word_freq` | ✓ `avg_log_freq` / `hard_word_ratio` | ✓ |
| NAER 104 → `naer_104_topic_coverage` / `naer_104_word_freq` | ✓ `avg_topic_coverage` / `avg_log_freq` | |
| Unihan → `strokes_lookup` | ✓ `avg_stroke` | |
| 教育部 4808 → `moe_chars` | ✓ `char_outside_4808_ratio` | ✓ |
| TBCL 漢字/詞語表 → `chars` / `words` | （經 moe／strokes 間接）| ✓ level lookup |

> 短文字 v2 主路徑**不做**三等七級 level lookup——當初刻意拿掉，改用詞頻／跨主題／筆畫等特徵的 supervised 模型。三等七級的 level 目前只剩 `tbcl_rules_v1` fallback 在用（所以 `words` 表仍需建起來備援）。

## 模型權重（`*.joblib`）

| 檔名 | 對應 backend | 訓練資料 |
|---|---|---|
| `short_form_v2.joblib` | `tbcl_supervised_v2`（短文字）| 人工標註的 UI 字串語料（非 NAER）|
| `svm_v0.joblib` | `svm_sung2014_v1`（長文字）| 自建分級語料 |

兩者同樣不隨 repo 散布；重訓需自備標註語料，本 repo 未附訓練腳本。
