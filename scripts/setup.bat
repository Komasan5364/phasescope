@echo off

cd "%~dp0\.."

set PYTHON=python
where uv > nul 2> nul && set PYTHON=uv run python

echo Creating virtual environment...
%PYTHON% -m venv .venv

call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

pause
