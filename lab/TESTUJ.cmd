@echo off
cd /d "%~dp0"
for %%p in (programy\*.exe) do (
  echo.
  echo ===== %%~np =====
  czas.exe "%%p" moje-instancje "wyniki\%%~np"
  weryfikator.exe moje-instancje "wyniki\%%~np"
)
echo.
echo Kolumny do arkusza: wyniki\^<program^>\CZASY.txt i KRYTERIUM.txt
pause
