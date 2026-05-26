# Frontend Review Skill 安裝腳本 (Windows / PowerShell)
# 用法：cd 到 skill 目錄後跑 .\install.ps1

$ErrorActionPreference = "Stop"

$ApiBaseUrl = "https://your-server.example.com"
$ApiToken   = "YOUR_REVIEW_API_TOKEN"

$SkillSrc = $PSScriptRoot
$SkillDst = Join-Path $env:USERPROFILE ".claude\skills\frontend-review"

Write-Host "=== Frontend Review Skill 安裝 ===" -ForegroundColor Cyan

# Step 1: 建目標目錄
Write-Host "`n[1/3] 複製 skill 檔到 $SkillDst"
New-Item -ItemType Directory -Force -Path $SkillDst | Out-Null

# 只複製 skill 內容、排除 installer 自己
Copy-Item -Path (Join-Path $SkillSrc "SKILL.md") -Destination $SkillDst -Force
foreach ($dir in @("rubrics", "examples", "reference")) {
    $src = Join-Path $SkillSrc $dir
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $SkillDst -Recurse -Force
    }
}
Write-Host "      完成。" -ForegroundColor Green

# Step 2: 設環境變數 (User scope)
Write-Host "`n[2/3] 設環境變數 (User scope)"
[System.Environment]::SetEnvironmentVariable("REVIEW_API_BASE_URL", $ApiBaseUrl, "User")
[System.Environment]::SetEnvironmentVariable("REVIEW_API_TOKEN", $ApiToken, "User")
Write-Host "      REVIEW_API_BASE_URL = $ApiBaseUrl" -ForegroundColor Green
Write-Host "      REVIEW_API_TOKEN    = (已設定)" -ForegroundColor Green

# Step 3: 提示
Write-Host "`n[3/3] 安裝完成" -ForegroundColor Green
Write-Host "`n接下來請：" -ForegroundColor Yellow
Write-Host "  1. 重啟 Claude Code（讓 skill 被偵測到）"
Write-Host "  2. 環境變數提醒：Windows 環境變數快取較頑固，如果重啟 Claude Code 後仍說找不到 token，"
Write-Host "     請登出再登入、或重開機讓環境變數完全生效。"
Write-Host "`n驗證：在 Claude Code 裡跑 ``/review-frontend https://example.com``"
