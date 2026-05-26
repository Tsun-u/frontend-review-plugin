param(
    # 部署目標連線參數（請自填）
    [string]$RemoteHost = "your-server.example.com",
    [string]$RemoteUser = "deploy",
    # 遠端 root 直接對應本地 server/（compose / .env / app 都在這層）
    [string]$RemotePath = "/home/deploy/frontend-review-server",
    # PuTTY .ppk 私鑰 → 走 plink / pscp（不是 OpenSSH）
    [string]$KeyPath    = "$HOME\.ssh\deploy.ppk",
    [string]$Plink      = "plink.exe",
    [string]$Pscp       = "pscp.exe",
    [string]$LocalServer = "$PSScriptRoot\..\server",
    [switch]$SkipBuild
)
# 注意：plink/pscp 必須用 PowerShell tool 跑，Bash tool 會擋 outbound（connection timeout）。
$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$remote = "$RemoteUser@$RemoteHost"
$tarLocal = "$env:TEMP\frserver-deploy-$ts.tar.gz"
$tarName = "frserver-deploy-$ts.tar.gz"

function Invoke-Remote([string]$cmd) {
    & $Plink -ssh -batch -i $KeyPath $remote $cmd
    if ($LASTEXITCODE -ne 0) { throw "remote command failed: $cmd" }
}

Write-Host "[1/5] 備份遠端 .env（含 production master key）"
Invoke-Remote "cp $RemotePath/.env /tmp/.env.bak.$ts && wc -c /tmp/.env.bak.$ts"

Write-Host "[2/5] 本地打包 server/（排除 .env / __pycache__ / *.log）"
try {
    tar.exe -czf $tarLocal -C $LocalServer --exclude=.env --exclude=__pycache__ --exclude=.pytest_cache --exclude=*.log .
    if ($LASTEXITCODE -ne 0) { throw "tar failed" }

    Write-Host "[3/5] 上傳 + 暫存驗證後置換（清 app 殘檔、.env 全程不碰）"
    & $Pscp -batch -i $KeyPath $tarLocal "${remote}:/tmp/$tarName"
    if ($LASTEXITCODE -ne 0) { throw "pscp upload failed" }

    # 先驗 tar 可讀再 rm app，確保不會在壞包時清空 app/
    $extract = @"
cd $RemotePath
tar tzf /tmp/$tarName > /dev/null && echo TAR_OK || { echo TAR_BAD; exit 1; }
rm -rf app
tar xzf /tmp/$tarName
test -f .env && echo ENV_PRESENT || { echo ENV_MISSING; exit 1; }
test -f app/main.py && echo APP_OK || { echo APP_BAD; exit 1; }
rm -f /tmp/$tarName
"@
    Invoke-Remote $extract
} finally {
    Remove-Item -Force $tarLocal -ErrorAction SilentlyContinue
}

if (-not $SkipBuild) {
    Write-Host "[4/5] rebuild + recreate api（不 down，postgres/minio 不受影響；新容器重讀 .env）"
    Invoke-Remote "cd $RemotePath && docker compose up -d --build api 2>&1 | tail -5 && docker compose ps"
}

Write-Host "[5/5] Health check（retry 等容器啟動，避免撞 startup race 報假性失敗）"
# 單引號 here-string：bash 變數全字面、不被 PowerShell 插值
$healthCheck = @'
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5566/health)
  if [ "$code" = "200" ]; then echo "health HTTP 200 (after ${i}s)"; exit 0; fi
  sleep 1
done
echo "health HTTP $code (timeout 20s)"; exit 1
'@
Invoke-Remote $healthCheck

Write-Host "完成。遠端 .env 備份在 /tmp/.env.bak.$ts"
Write-Host "提醒：實際部署前先跟團隊同步、避開演示時段。"
