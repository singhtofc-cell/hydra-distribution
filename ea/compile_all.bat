@echo off
REM ============================================================================
REM  🐙 Hydra Trading System — Compile All MQL5 EAs
REM  วางไฟล์นี้ไว้ใน %MT5_DATA_DIR%\MQL5\Experts\Hydra\ แล้ว双击รัน
REM ============================================================================
echo.
echo  🐙 Hydra Trading System — Compiling all EAs...
echo  ==============================================
echo.

setlocal enabledelayedexpansion

REM — 1. ค้นหา MetaEditor.exe — เฉพาะของ MT5 เท่านั้น!
set "METAEDITOR="
set "PATHS[0]=C:\Program Files\MetaTrader 5\MetaEditor.exe"
set "PATHS[1]=C:\Program Files (x86)\MetaTrader 5\MetaEditor.exe"
set "PATHS[2]=%LOCALAPPDATA%\Programs\MetaTrader 5\MetaEditor.exe"
set "PATHS[3]=%USERPROFILE%\AppData\Local\MetaTrader 5\MetaEditor.exe"

REM ข้าม MT4 อย่างเด็ดขาด — MT4 MetaEditor ไม่สามารถ compile .mq5 ได้
set "PATHS[4]=C:\Program Files\MetaTrader 4\MetaEditor.exe"
set "PATHS[5]=C:\Program Files (x86)\MetaTrader 4\MetaEditor.exe"

for /L %%i in (0,1,3) do (
    if exist "!PATHS[%%i]!" (
        set "METAEDITOR=!PATHS[%%i]!"
        goto :FOUND
    )
)

:FOUND
if "%METAEDITOR%"=="" (
    echo  [ERROR] MetaEditor.exe not found!
    echo.
    echo  Make sure MetaTrader 5 is installed on this machine.
    echo  Common paths checked:
    for /L %%i in (0,1,3) do echo    - !PATHS[%%i]!
    goto :END
)

echo  [OK] Found MetaEditor: %METAEDITOR%
echo.

REM — 2. ตั้งค่า Path
set "SOURCE_DIR=%~dp0"
set "MQL5_DIR=%SOURCE_DIR%..\"
if not exist "!MQL5_DIR!Include" (
    REM ถ้าไม่ได้อยู่ใน MT5 folder ให้หา Include ใน MT5
    for /f "delims=" %%d in ("%METAEDITOR%") do set "MT5_DIR=%%~dpd"
    set "MT5_INCLUDE=!MT5_DIR!MQL5\Include"
) else (
    set "MT5_INCLUDE=!MQL5_DIR!Include"
)

echo  Source files to compile:
echo  -----------------------
set COMPILE_COUNT=0
for %%f in ("%SOURCE_DIR%*.mq5" "%SOURCE_DIR%*.mqh") do (
    if exist "%%f" (
        echo    %%~nxf
        set /a COMPILE_COUNT+=1
    )
)
echo.
if %COMPILE_COUNT%==0 (
    echo  [ERROR] No .mq5 or .mqh files found in %SOURCE_DIR%
    goto :END
)

REM — 3. Compile แต่ละไฟล์
echo  Starting compilation...
echo  =======================
echo.

:COMPILE_LOOP
for %%f in ("%SOURCE_DIR%*.mq5") do (
    echo  [%%~nf] Compiling...
    start /wait "" "%METAEDITOR%" /compile:"%%f" /log:"%SOURCE_DIR%compile_%%~nf.log"
    
    REM ตรวจสอบผลลัพธ์
    if exist "%%~dpnf.ex5" (
        echo  [%%~nf] ✅ SUCCESS — %%~nf.ex5 created
    ) else (
        echo  [%%~nf] ❌ FAILED — Check compile_%%~nf.log for details
        type "%SOURCE_DIR%compile_%%~nf.log" 2>nul
    )
    echo.
)

REM — 4. Summary
echo  =======================
echo.
echo  Compiled files (.ex5):
dir /b "%SOURCE_DIR%*.ex5" 2>nul
echo.
echo  Log files (.log):
dir /b "%SOURCE_DIR%compile_*.log" 2>nul
REM — 5. Auto-deploy to MT5 Data Folder
echo  =======================
echo.
echo  Checking MT5 data folders for auto-deploy...
for %%d in (
    "%USERPROFILE%\AppData\Roaming\MetaQuotes\Terminal"
    "%APPDATA%\MetaQuotes\Terminal"
    "%LOCALAPPDATA%\MetaQuotes\Terminal"
) do (
    if exist "%%d" (
        for /r "%%d" %%e in (HydraClientEA.ex5) do (
            if exist "%%~dpe" (
                copy /Y "%SOURCE_DIR%*.ex5" "%%~dpe" >nul
                echo  ✅ Deployed to %%~dpe
            )
        )
    )
)

echo.
echo  🐙 Compilation complete!
echo.

:END
echo.
pause
