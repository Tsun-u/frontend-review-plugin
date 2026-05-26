#!/usr/bin/env python3
"""
Source-scan client-side extractor — 本機抽取中文 UI 文字。

設計原則（隱私）：
  源碼不離開本機。這支腳本在使用者本機 walk 源碼樹、抽出中文 UI 文字，
  只輸出字串清單（list[{text, source_file, line}]）給 server endpoint。
  server 端只收字串、不碰檔案系統。

抽取策略：
  逐行掃描，用「結構字元」(< > = { } ' " ;) 把行切成 token，
  取含中文的 token、strip 頭尾雜訊。這樣 alert('查無資料') 的字串、
  <td>確認</td> 的標籤內文、title="請輸入" 的屬性值都能乾淨抽出，
  而結尾的 ') "; 等程式碼語法不會被帶進來。

註解處理（跳過、避免抓到註解內的中文）：
  - JS / CSS  /* ... */（可跨行）、// 行內到行尾
  - HTML/XML  <!-- ... -->（可跨行）
  - JSP       <%-- ... --%>（可跨行）
  - .properties  # 開頭整行

用法：
  python extract_ui_strings.py <root_path> [--ext .jsp,.html,.js] [--out strings.json]
  預設輸出到 stdout（JSON）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_EXTENSIONS = [".jsp", ".html", ".htm", ".js", ".properties", ".xml"]

CJK_RE = re.compile(r"[一-鿿]")

# 把一行切成 token 的「結構字元」：字串邊界 / 標籤邊界 / 程式碼分隔
SPLIT_RE = re.compile(r"[<>={}'\";\n\r]+")

# strip 頭尾的雜訊（ASCII 標點、括號、引號、空白）；中文標點保留
LEADING_JUNK = re.compile(r"^[\s`)(\[\],.:;!?%/\\|*+&@#~^$\-—–]+")
TRAILING_JUNK = re.compile(r"[\s`)(\[\],.:;%/\\|*+&@#~^$\-—–]+$")

# 區塊註解配對（start, end）
BLOCK_COMMENTS = [
    ("<%--", "--%>"),   # JSP
    ("<!--", "-->"),    # HTML / XML
    ("/*", "*/"),       # JS / CSS
]


def count_cjk(s: str) -> int:
    return len(CJK_RE.findall(s))


def strip_junk(s: str) -> str:
    s = LEADING_JUNK.sub("", s)
    s = TRAILING_JUNK.sub("", s)
    return s.strip()


def remove_line_comments(line: str, ext: str) -> str:
    """移除行內到行尾的註解（// 或 .properties 的 #）。"""
    if ext == ".properties":
        # # 開頭整行視為註解
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("!"):
            return ""
    # JS // 註解：找第一個不在引號內的 //（簡化版：直接找 //，UI 文字極少含 //）
    # URL 的 http:// 在引號內、且不影響中文抽取（會被 strip），這裡保守處理
    idx = line.find("//")
    if idx != -1:
        # 粗略避開 http:// https://（前一字元是 :）
        if idx > 0 and line[idx - 1] == ":":
            pass  # 可能是 URL，不截
        else:
            line = line[:idx]
    return line


def extract_from_file(path: Path, root: Path) -> list[dict]:
    """從單一檔案抽出中文 UI 文字 candidate。"""
    ext = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="big5")
        except Exception:
            return []
    except Exception:
        return []

    rel = path.relative_to(root).as_posix()
    results = []
    seen = set()  # (text) 同檔去重

    in_block = None  # 目前所在的 block comment 結束符，None 表示不在註解內
    lines = text.split("\n")

    for line_no, raw in enumerate(lines, start=1):
        line = raw

        # === 處理跨行 block comment 狀態 ===
        work = []
        i = 0
        while i < len(line):
            if in_block:
                end_idx = line.find(in_block, i)
                if end_idx == -1:
                    # 整行剩餘都在註解內
                    i = len(line)
                    break
                else:
                    i = end_idx + len(in_block)
                    in_block = None
                    continue
            else:
                # 找最近的 block comment start
                next_start = None
                next_pos = len(line)
                for start, end in BLOCK_COMMENTS:
                    p = line.find(start, i)
                    if p != -1 and p < next_pos:
                        next_pos = p
                        next_start = (start, end)
                if next_start is None:
                    work.append(line[i:])
                    i = len(line)
                else:
                    work.append(line[i:next_pos])
                    in_block = next_start[1]
                    i = next_pos + len(next_start[0])
        code_part = "".join(work)

        # === 移除行內註解 ===
        code_part = remove_line_comments(code_part, ext)
        if not CJK_RE.search(code_part):
            continue

        # === 切 token、抽中文 ===
        for token in SPLIT_RE.split(code_part):
            if not CJK_RE.search(token):
                continue
            cleaned = strip_junk(token)
            cleaned = re.sub(r"\s+", " ", cleaned)
            if count_cjk(cleaned) < 1:
                continue
            # 過短的單字也保留（UI 常有「是」「否」單字按鈕），但純標點不要
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            results.append({
                "text": cleaned,
                "source_file": rel,
                "line": line_no,
            })

    return results


def scan_tree(root: Path, extensions: list[str]) -> list[dict]:
    exts = {e.lower() for e in extensions}
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts:
            out.extend(extract_from_file(p, root))
    return out


def main():
    ap = argparse.ArgumentParser(description="抽取本機源碼的中文 UI 文字")
    ap.add_argument("root", help="源碼根目錄")
    ap.add_argument("--ext", default=",".join(DEFAULT_EXTENSIONS),
                    help="副檔名清單，逗號分隔（預設 .jsp,.html,.htm,.js,.properties,.xml）")
    ap.add_argument("--out", default=None, help="輸出 JSON 路徑（預設 stdout）")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} 不是有效目錄", file=sys.stderr)
        sys.exit(1)

    extensions = [e.strip() if e.strip().startswith(".") else "." + e.strip()
                  for e in args.ext.split(",") if e.strip()]
    strings = scan_tree(root, extensions)

    payload = json.dumps(strings, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"抽出 {len(strings)} 筆字串 → {args.out}", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
