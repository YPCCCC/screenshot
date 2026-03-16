@echo off
chcp 65001 >nul
pip install -r "%~dp0requirements.txt" -q
py "%~dp0screenshot_tool.py"
