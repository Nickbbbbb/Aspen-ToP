@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ================================================
echo Aspen-ToP 可执行文件打包开始
echo ================================================

python -m pip install --upgrade setuptools > nul
if errorlevel 1 (
    echo setuptools 安装失败
    exit /b 1
)

python -m pip install --upgrade pyinstaller > nul
if errorlevel 1 (
    echo PyInstaller 安装失败
    exit /b 1
)

python -m pip install --upgrade pycryptodome > nul
if errorlevel 1 (
    echo pycryptodome 安装失败
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --clean AspenToTop.spec
if errorlevel 1 (
    echo 打包失败
    exit /b 1
)

echo.
echo 打包完成
echo 生成文件: %cd%\dist\AspenToTop.exe
