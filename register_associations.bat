@echo off
set "APP_DIR=%~dp0dist\ComicReader\ComicReader.exe"
set "ICON_DIR=%~dp0icons"

reg add "HKCU\Software\Classes\Applications\ComicReader.exe" /v "FriendlyAppName" /d "Comic Reader" /f
reg add "HKCU\Software\Classes\Applications\ComicReader.exe\DefaultIcon" /ve /d "%ICON_DIR%\app.ico" /f
reg add "HKCU\Software\Classes\Applications\ComicReader.exe\shell\open\command" /ve /d "\"%APP_DIR%\" \"%%1\"" /f

:: CBZ
reg add "HKCU\Software\Classes\ComicReader.cbz" /ve /d "Comic Book CBZ Archive" /f
reg add "HKCU\Software\Classes\ComicReader.cbz\DefaultIcon" /ve /d "%ICON_DIR%\cbz.ico" /f
reg add "HKCU\Software\Classes\ComicReader.cbz\shell\open\command" /ve /d "\"%APP_DIR%\" \"%%1\"" /f
reg add "HKCU\Software\Classes\.cbz\OpenWithProgids" /v "ComicReader.cbz" /f

:: Repeat for CBR, PDF, EPUB as needed...
echo Associations registered successfully!
pause