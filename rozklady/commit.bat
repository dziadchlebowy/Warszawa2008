@echo off
chcp 65001 >nul
setlocal

cd converter
python3 convert.py
cd ..
echo Odswiezono baze.
pause

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$title = 'ZKM Zembaczyn'; ^
Add-Type -AssemblyName Microsoft.VisualBasic; ^
$description = [Microsoft.VisualBasic.Interaction]::InputBox('Zmiany w rozkładach:', $title, ''); ^
if ($description -eq '') { exit 1 }; ^
git add -A; ^
git commit -m $description; ^
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; ^
git push"

if %errorlevel% neq 0 (
    echo.
    echo Wystapil blad podczas commitowania lub pushowania.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ZMIANY ZACOMMITOWANE I WYPUSHOWANE
echo ========================================
echo.
pause