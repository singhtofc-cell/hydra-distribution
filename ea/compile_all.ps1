# 🐙 Hydra Trading System — Compile All EAs (PowerShell)
# วางไฟล์นี้ไว้ใน folder ea/ แล้วรันด้วย PowerShell บนเครื่อง Windows ที่มี MT5
# Run: powershell -ExecutionPolicy Bypass -File compile_all.ps1

Write-Host "`n 🐙 Hydra Trading System — Compiling all EAs..." -ForegroundColor Cyan
Write-Host " ==============================================`n" -ForegroundColor Cyan

# — 1. Find MetaEditor.exe — เฉพาะของ MT5 เท่านั้น!
$mt5Paths = @(
    "$env:ProgramFiles\MetaTrader 5\MetaEditor.exe",
    "${env:ProgramFiles(x86)}\MetaTrader 5\MetaEditor.exe",
    "$env:LOCALAPPDATA\Programs\MetaTrader 5\MetaEditor.exe",
    "$env:USERPROFILE\AppData\Local\MetaTrader 5\MetaEditor.exe"
)

$mt4Paths = @(
    "$env:ProgramFiles\MetaTrader 4\MetaEditor.exe",
    "${env:ProgramFiles(x86)}\MetaTrader 4\MetaEditor.exe",
    "$env:LOCALAPPDATA\Programs\MetaTrader 4\MetaEditor.exe"
)

$metaEditor = $null
$isMT4 = $false

# หา MT5 ก่อน
foreach ($p in $mt5Paths) {
    if (Test-Path $p) {
        $metaEditor = $p
        $isMT4 = $false
        break
    }
}

# ถ้าไม่เจอ MT5 ให้ Warning แต่ยังหา MT4 (เผื่อมีแค่ MT4)
if (-not $metaEditor) {
    foreach ($p in $mt4Paths) {
        if (Test-Path $p) {
            Write-Host " ⚠️ พบเฉพาะ MetaEditor ของ MT4, MT5 MetaEditor ไม่พบ!" -ForegroundColor Yellow
            Write-Host " ⚠️ MT4 ไม่สามารถ compile .mq5 ได้ ต้องใช้ MT5 เท่านั้น" -ForegroundColor Yellow
            $metaEditor = $p
            $isMT4 = $true
            break
        }
    }
}

if (-not $metaEditor) {
    Write-Host " [ERROR] MetaEditor.exe not found!" -ForegroundColor Red
    Write-Host " Install MetaTrader 5 first, then re-run this script.`n"
    Read-Host "Press Enter to exit"
    exit 1
}

if ($isMT4) {
    Write-Host " [ERROR] พบเฉพาะ MT4 MetaEditor ซึ่งไม่สามารถ compile .mq5 ได้!" -ForegroundColor Red
    Write-Host " กรุณาติดตั้ง MetaTrader 5 แล้วรันสคริปต์อีกครั้ง" -ForegroundColor Red
    Write-Host ""
    Write-Host " หรืออีกวิธี: เปิดไฟล์ .mq5 ด้วย MetaEditor ของ MT5 โดยตรง:" -ForegroundColor Yellow
    Write-Host "   1. เปิด MetaTrader 5" -ForegroundColor Yellow
    Write-Host "   2. Tools → MetaQuotes Language Editor" -ForegroundColor Yellow
    Write-Host "   3. File → Open → เลือก HydraClientEA.mq5" -ForegroundColor Yellow
    Write-Host "   4. F7 (Compile)`n" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host " [OK] Found MetaEditor: $metaEditor`n" -ForegroundColor Green

# — 2. Set source directory (same as script location)
$sourceDir = Split-Path -Parent $PSCommandPath

# — 3. Find all .mq5 files
$mq5Files = Get-ChildItem -Path $sourceDir -Filter "*.mq5" | Sort-Object Name
$mqhFiles = Get-ChildItem -Path $sourceDir -Filter "*.mqh" | Sort-Object Name

Write-Host " Files to compile:" -ForegroundColor Yellow
foreach ($f in $mq5Files) { Write-Host "   📄 $($f.Name)" }
foreach ($f in $mqhFiles) { Write-Host "   📄 $($f.Name)" }
Write-Host ""

if ($mq5Files.Count -eq 0) {
    Write-Host " [ERROR] No .mq5 files found in $sourceDir" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# — 4. Compile each file
$success = 0
$failed = 0

foreach ($f in $mq5Files) {
    $logFile = Join-Path $sourceDir "compile_$($f.BaseName).log"
    $ex5File = Join-Path $sourceDir "$($f.BaseName).ex5"
    
    Write-Host " [$($f.BaseName)] Compiling..." -ForegroundColor Cyan
    
    $process = Start-Process -FilePath $metaEditor -ArgumentList "/compile:`"$($f.FullName)`" /log:`"$logFile`"" -Wait -NoNewWindow -PassThru
    
    if (Test-Path $ex5File) {
        Write-Host " [$($f.BaseName)] ✅ SUCCESS - $($f.BaseName).ex5 created" -ForegroundColor Green
        $success++
    } else {
        Write-Host " [$($f.BaseName)] ❌ FAILED - Check $logFile" -ForegroundColor Red
        if (Test-Path $logFile) {
            Get-Content $logFile | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
        }
        $failed++
    }
}

# — 5. Summary
Write-Host "`n =======================" -ForegroundColor Cyan
Write-Host " Compilation Complete!" -ForegroundColor Cyan
Write-Host " ✅ Success: $success" -ForegroundColor Green
if ($failed -gt 0) { Write-Host " ❌ Failed: $failed" -ForegroundColor Red }
Write-Host "`n Compiled files:" -ForegroundColor Yellow
Get-ChildItem -Path $sourceDir -Filter "*.ex5" | ForEach-Object { Write-Host "   📦 $($_.Name) ($(($_.Length/1KB).ToString('F1')) KB)" }

Write-Host "`n 🐙 Hydra Trading System" -ForegroundColor Cyan
# — 6. Auto-deploy to MT5 Data Folder (ถ้าหาเจอ)
$mt5DataPaths = @(
    "$env:USERPROFILE\AppData\Roaming\MetaQuotes\Terminal\*\MQL5\Experts\Hydra",
    "$env:APPDATA\MetaQuotes\Terminal\*\MQL5\Experts\Hydra",
    "$env:LOCALAPPDATA\MetaQuotes\Terminal\*\MQL5\Experts\Hydra"
)

foreach ($pattern in $mt5DataPaths) {
    $folders = Resolve-Path $pattern -ErrorAction SilentlyContinue
    foreach ($folder in $folders) {
        if ($folder -and (Test-Path $folder)) {
            Write-Host "`n 📁 Deploying to MT5 Data Folder: $folder" -ForegroundColor Magenta
            Copy-Item "$sourceDir\*.ex5" $folder -Force
            Write-Host " ✅ Deployed to $folder" -ForegroundColor Green
        }
    }
}

Read-Host "`nPress Enter to exit"
