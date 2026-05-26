# 中文可讀性資料檔

本目錄的資料檔與模型權重**未隨 repo 散布**，因為來源資料受著作權保護：

- 國家教育研究院《臺灣華語文能力基準》（TBCL）字表 / 詞語表 / 通用詞頻表：國教院版權所有，All rights reserved。
- 教育部 4808 常用字。

要啟用中文可讀性功能，請自行向來源取得原始資料、放入本目錄，再執行重建腳本產生 `lexicon.db`。

## 需要的原始檔

放入 `server/app/chinese_readability/data/naer/`：

| 檔名 | 內容 |
|---|---|
| `naer_hanzi_table.xlsx` | 國教院 TBCL 漢字表 |
| `naer_14452_words.xlsx` | 國教院 TBCL 詞語表 |
| `naer_common_word_freq.xlsx` | 國教院 通用詞頻表 |
| `moe_4808_chars.ods` | 教育部 4808 常用字 |

來源入口：國家教育研究院「華語文語料庫與能力基準整合應用系統」<https://coct.naer.edu.tw/>

## 重建 lexicon.db

```bash
python server/app/chinese_readability/_dev/build_lexicon.py
```

腳本預設讀本目錄（`data/`）下的 `naer/`、輸出 `data/lexicon.db`。
資料若放在別處，用環境變數覆寫根目錄：

```bash
READABILITY_DATA_DIR=/path/to/data python server/app/chinese_readability/_dev/build_lexicon.py
```

## 模型權重（`*.joblib`）

`short_form_v2.joblib`（短文字模式）與 `svm_sung2014_v1` 對應的長文字模型，是以上述資料訓練出的權重，同樣不隨 repo 散布。重訓需自備標註語料，本 repo 未附訓練腳本。

> 沒有 `lexicon.db` 與模型權重時，server 的中文可讀性 endpoint 無法運作；其餘功能（Lighthouse / WCAG / DeepGaze / Nielsen 等）不受影響。
