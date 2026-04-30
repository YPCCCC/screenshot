@echo off
chcp 65001 >nul
setlocal

:: 设置一个标记，默认使用 python 命令
set "PYTHON_CMD=python"

:: 检查 python 命令是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 'python' 命令不可用，尝试使用 'py' 启动器...
    :: 如果 python 不可用，尝试使用 Windows 的 py 启动器
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo ==========================================
        echo [错误] 系统未检测到 Python 环境。
        echo.
        echo 请确认：
        echo 1. 已安装 Python
        echo 2. 安装时勾选了 "Add Python to PATH"
        echo ==========================================
        pause
        exit /b
    ) else (
        set "PYTHON_CMD=py"
    )
)

echo 检测到 Python 命令: %PYTHON_CMD%
echo.

echo 正在检查依赖...
:: 使用 -m pip 代替 pip，兼容性更好
%PYTHON_CMD% -m pip install -r "%~dp0requirements.txt" -q

echo 启动截图工具...
%PYTHON_CMD% "%~dp0screenshot_tool.py"

:: 无论成功失败，最后都暂停，防止窗口消失
echo.
echo ------------------------------------------------
if %errorlevel% neq 0 (
    echo [注意] 程序运行结束，但似乎有错误发生。
) else (
    echo 程序已退出。
)
pause
