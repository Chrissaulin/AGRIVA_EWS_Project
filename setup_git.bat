@echo off
echo ===================================================
echo   AGRIVA EWS: Git Branch Setup & Remote Pull
echo ===================================================
echo [1/5] Memeriksa direktori kerja saat ini...
cd /d "c:\Users\faizr\Documents\! Data-Data Faiz\File Kuliah dkk\Semester 4\agriva\AGRIVA_EWS_Project"
echo Direktori aktif: %cd%
echo.

echo [2/5] Memeriksa status repositori dan remote...
git status
git remote -v
echo.

echo [3/5] Berpindah ke branch main...
git checkout main
echo.

echo [4/5] Menarik pembaruan dari origin main...
git pull origin main
echo.

echo [5/5] Membuat dan berpindah ke branch feature/web-dashboard-ews...
git checkout -b feature/web-dashboard-ews
echo.

echo ===================================================
echo   Git Branch Setup Selesai dengan Sukses!
echo ===================================================
pause
