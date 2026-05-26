# Chinese Readability — LLM Stop-gap Rubric

This is a temporary rubric for estimating Chinese text readability until the SVM model (v0.2) is ready. You are the LLM doing the estimation — use the anchor table below to calibrate.

## Output Format

```json
{
  "grade": 5,
  "hard_words": ["最佳化", "核心價值"],
  "hard_sentences": [
    {"text": "在進行最佳化的同時兼顧使用者體驗的核心價值", "issues": ["35字", "套疊4層結構"]}
  ],
  "warnings": []
}
```

- `grade`: estimated school grade level (1–12, where 1 = 小一, 6 = 小六, 7 = 國一, 12 = 高三)
- `hard_words`: words that push the grade up (technical terms, rare characters, multi-syllable compounds)
- `hard_sentences`: sentences that are hard to parse (long, deeply nested, passive voice, multiple clauses)
- `warnings`: edge cases like "text too short for reliable estimate" or "mixed language"

## Grade Anchor Table

| Grade | Typical characteristics | Example |
|---|---|---|
| 1–2 | 常用字、短句（≤10字）、主動語態 | 小狗跑到公園玩 |
| 3–4 | 複合句開始出現、簡單因果 | 因為下雨了，所以我們留在家裡玩遊戲 |
| 5–6 | 段落結構、抽象概念初現、20–25字句 | 科學家發現這種植物可以在沙漠中生長，因為它的根特別長 |
| 7–8 | 被動語態、專業術語初現、25–30字句 | 這項研究被認為對於了解氣候變遷的影響具有重要的參考價值 |
| 9–10 | 多重子句、學術用語、30–40字句 | 根據調查結果顯示，超過七成的受訪者認為政府應該加強對於食品安全的監管力度 |
| 11–12 | 文言詞彙混用、抽象論述、40+字句 | 在全球化的脈絡下，如何在追求經濟成長的同時維護本土文化的多元性，已成為各國政策制定者必須面對的核心議題 |

## Estimation Rules

1. **Start from word difficulty**: scan for words a student at each grade wouldn't know. The grade is the lowest level where most readers could understand most words.
2. **Adjust for sentence complexity**: deeply nested sentences (+1 grade), passive voice (+0.5), mixed Chinese-English (+0.5)
3. **Adjust for domain**: marketing copy targeting general public should aim for grade 5–7; government/legal documents are typically grade 9–12
4. **Web copy target**: for commercial websites, grade ≤ 7 is good, 8–9 is acceptable, ≥ 10 needs simplification

## Warning Conditions

- Text shorter than 50 characters: `"文字過短，估計可能不準確"`
- More than 30% English mixed in: `"中英混雜比例高，年級估計僅供參考"`
- Technical domain (medical/legal/financial): `"專業領域文字，一般讀者可能需要更高年級"`
