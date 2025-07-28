@echo off
chcp 65001 > nul
rem Batch script to add, commit, and push to Heroku. This version prompts for input.

echo ===================================
echo  DEPLOY SCRIPT TO HEROKU
echo ===================================
echo.

rem Yeu cau nguoi dung nhap commit message
set /p commitMessage=">> Nhap ghi chu cho ban cap nhat roi an Enter: "

rem Kiem tra xem ghi chu co bi bo trong khong
if not defined commitMessage (
    echo.
    echo [LOI] Ghi chu cap nhat khong duoc de trong.
    echo Vui long chay lai file.
    echo.
    pause
    goto :eof
)

echo.
echo [1/3] Dang them tat ca cac file vao Git...
git add .

echo.
echo [2/3] Dang commit cac thay doi...
git commit -m "%commitMessage%"

echo.
echo [3/3] Dang day code len Heroku...
git push heroku main

echo.
echo ===================================
echo  DEPLOY HOAN TAT!
echo ===================================
pause
