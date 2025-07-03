@echo off

cd "%~dp0\.."

call .venv\Scripts\activate.bat

set SITE_PACKAGES=.venv\Lib\site-packages

python -m nuitka --output-filename="phasescope.exe" ^
    --standalone --onefile ^
    --follow-imports --enable-plugin=pyside6 ^
    --windows-icon-from-ico="icon.ico" --windows-console-mode=disable ^
    --include-data-files="%SITE_PACKAGES%\soundcard\coreaudio.py.h"="soundcard/coreaudio.py.h" ^
    --include-data-files="%SITE_PACKAGES%\soundcard\mediafoundation.py.h"="soundcard/mediafoundation.py.h" ^
    --include-data-files="%SITE_PACKAGES%\soundcard\pulseaudio.py.h"="soundcard/pulseaudio.py.h" ^
    main.py

pause
