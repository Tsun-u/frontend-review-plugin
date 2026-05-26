# Frontend Review Skill 安裝說明

這是一個前端 UI/UX 評測工具的 Claude Code skill。裝好後在 Claude Code 裡一句 `/review-frontend <網址>` 就能對任意網頁跑客觀指標（Lighthouse / WCAG / 視線預測）加主觀評估（Nielsen heuristic / 中文可讀性），產出整合報告。

## 前置需求

- **Claude Code CLI**（這份說明是 CLI 版的裝法；如果你用 Claude cowork 網頁版，安裝機制不同、請另外詢問）
- 連得到你部署的評測 server（skill 會呼叫環境變數 `REVIEW_API_BASE_URL` 指向的網址，例如 `https://your-server.example.com`）

---

## 方式 A：自動安裝（推薦）

### Windows

開 PowerShell，cd 到這個 skill 目錄，跑：

```powershell
.\install.ps1
```

### Mac / Linux

開 terminal，cd 到這個 skill 目錄，跑：

```bash
bash install.sh
```

腳本會自動：
1. 複製 skill 檔到 `~/.claude/skills/frontend-review/`
2. 設好兩個環境變數（API 網址 + token）
3. 提示你重啟 Claude Code

跑完照提示重啟即可。

---

## 方式 B：手動安裝

### Step 1：複製 skill 檔

把這個目錄下的 `SKILL.md` + `rubrics/` + `examples/` + `reference/` 複製到：

- Windows：`%USERPROFILE%\.claude\skills\frontend-review\`
- Mac / Linux：`~/.claude/skills/frontend-review/`

複製後結構應該長這樣（`SKILL.md` 直接在 `frontend-review/` 下、不要多包一層）：

```
~/.claude/skills/frontend-review/
├── SKILL.md
├── rubrics/
├── examples/
└── reference/
```

（`INSTALL.md` / `install.ps1` / `install.sh` 不用複製過去）

### Step 2：設環境變數

**Windows**（PowerShell，設到 User scope 永久生效）：

```powershell
[System.Environment]::SetEnvironmentVariable("REVIEW_API_BASE_URL", "https://your-server.example.com", "User")
[System.Environment]::SetEnvironmentVariable("REVIEW_API_TOKEN", "YOUR_REVIEW_API_TOKEN", "User")
```

**Mac / Linux**（加到 `~/.zshrc` 或 `~/.bashrc`）：

```bash
export REVIEW_API_BASE_URL="https://your-server.example.com"
export REVIEW_API_TOKEN="YOUR_REVIEW_API_TOKEN"
```

### Step 3：重啟 Claude Code

讓 skill 被偵測到、環境變數被讀進去。

---

## 驗證

重啟後在 Claude Code 裡跑：

```
/review-frontend https://example.com
```

或直接講「幫我 review 這個前端：https://example.com」。

應該會看到 Claude 開始偵測能力、呼叫 API、產出報告。

---

## 常見問題

### Q：設了環境變數但 Claude 說找不到 token？

**Windows 特有雷**：環境變數設到 User scope 後，已經開著的程式（包括 Claude Code、explorer）不會立刻看到——Windows 的環境變數快取要重新登入或重開機才會完全刷新。重開 terminal 通常不夠。**最保險：重開機，或登出再登入。**

### Q：Claude 找不到 `/review-frontend` skill？

確認：
1. 檔案真的在 `~/.claude/skills/frontend-review/SKILL.md`
2. Claude Code 重啟過
3. Claude Code 版本支援 skill 功能（太舊的版本可能不支援、請更新）

### Q：API 回 401？

token 設錯或沒設到。檢查環境變數：
- Windows：`echo $env:REVIEW_API_TOKEN`（新開的 PowerShell）
- Mac/Linux：`echo $REVIEW_API_TOKEN`

### Q：API 回逾時 / 連不上？

確認你連得到自己部署的 server，例如 `https://your-server.example.com/health`（瀏覽器開應該看到 `{"status":"ok"}`）。

---

## 注意

- **token 是存取你 server 的憑證**，請妥善保管，不要 commit 進版控或貼到公開場合（GitHub、Slack 公開頻道等）。
- 一次 review 跑完約 1-2 分鐘（伺服器在跑 Lighthouse + 視線預測 + 中文分析），請耐心等。
- 伺服器一次只處理一個 review，多人同時打會排隊，慢慢來。
