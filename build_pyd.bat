@echo off
setlocal
chcp 65001 >nul
title SeedBoxes - Cython 编译 backend.pyd

echo.
echo ==== 把 backend.py 编译为 backend.pyd（防反编译）====
echo.

cd /d "%~dp0"

rem ---- 检查 uv ----
where uv >nul 2>&1
if errorlevel 1 (
    if exist "..\boxes-1.2\uv-bin\uv.exe" (
        set "PATH=%~dp0..\boxes-1.2\uv-bin;%PATH%"
    ) else (
        echo [X] 未找到 uv
        goto end
    )
)

echo [1/3] 安装 Cython ...
set "UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"
uv pip install cython
if errorlevel 1 goto fail

echo.
echo [2/3] 编译 backend.py → backend.pyd ...
echo     需要 Microsoft Visual C++ Build Tools 14.0+
echo     若编译失败，请安装：winget install Microsoft.VisualStudio.2022.BuildTools
uv run python setup_ext.py build_ext --inplace
if errorlevel 1 goto fail

echo.
echo [3/3] 清理 backend.py（备份为 backend.py.src）...
if exist backend.py.src del backend.py.src
ren backend.py backend.py.src

echo.
echo ==========================================
echo  [OK] 已生成 backend.cp310-win_amd64.pyd
echo  原 backend.py 重命名为 backend.py.src（不再被 import）
echo  下次跑 build_uv.bat 打包，会自动用 .pyd
echo ==========================================
goto end

:fail
echo.
echo [X] 编译失败 — 通常是缺 MSVC 编译器
echo     安装命令: winget install Microsoft.VisualStudio.2022.BuildTools --override "--wait --quiet --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
:end
echo.
pause
endlocal
exit /b
