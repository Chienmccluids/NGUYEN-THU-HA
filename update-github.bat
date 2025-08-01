@echo off
rem Dat cua so dong lenh sang che do UTF-8 de hien thi Tieng Viet
chcp 65001 > nul

echo [Buoc 1] Dang xoa thong tin dang nhap GitHub da luu...
rem Lenh nay se xoa thong tin dang nhap cu. Neu khong co gi de xoa, no se bao loi nhung khong sao ca.
cmdkey /delete:git:https://github.com

echo.
echo [Buoc 2] Yeu cau ghi chu cho ban cap nhat...
set /p commitMessage=">> Nhap ghi chu roi an Enter: "

rem Kiem tra xem ghi chu co bi bo trong khong
if not defined commitMessage (
    echo [LOI] Ghi chu cap nhat khong duoc de trong.
    pause
    goto :eof
)

echo.
echo [Buoc 3] Dang chuan bi va luu code...
git add .
git commit -m "%commitMessage%"

echo.
echo [Buoc 4] Dang day code len GitHub (chuan bi dang nhap)...
git push origin main

echo.
echo ==================================================
echo  HOAN TAT! Kiem tra cua so dong lenh de xem ket qua.
echo ==================================================
echo.
pause