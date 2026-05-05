@echo off
setlocal
chcp 65001 >nul
title 安装 MSVC Build Tools 到 D:\Apps\MSVC Build Tools

echo.
echo ==== 安装 MSVC C++ Build Tools 14.0+ （直连微软官方）====
echo  目标目录：D:\Apps\MSVC Build Tools
echo  下载约 2~3 GB，安装约 10~30 分钟（看网速）
echo.
echo  注：必须以"管理员身份"运行此脚本，否则会失败！
echo.
pause

set "TMPEXE=%TEMP%\vs_BuildTools.exe"
set "URL=https://aka.ms/vs/17/release/vs_BuildTools.exe"

echo.
echo [1/2] 下载 VS Bootstrapper （约 4 MB）...
powershell -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%TMPEXE%'"
if not exist "%TMPEXE%" (
    echo [X] 下载失败 — 检查网络或先访问 https://visualstudio.microsoft.com/zh-hans/visual-cpp-build-tools/ 手动下载
    goto end
)
echo     已下载到 %TMPEXE%

echo.
echo [2/2] 启动安装（静默 / 自动接受协议 / 无需重启）...
echo     任务栏会出现 "Visual Studio Installer" 图标显示进度
echo     此命令会等待安装完成才返回，请耐心等待...
"%TMPEXE%" --wait --quiet --norestart ^
  --installPath "D:\Apps\MSVC Build Tools" ^
  --add Microsoft.VisualStudio.Workload.VCTools ^
  --includeRecommended

if errorlevel 1 (
    echo.
    echo [X] 安装返回非零退出码 ^(%errorlevel%^)
    echo     - 3010 表示安装成功但建议重启
    echo     - 1602 表示用户取消
    echo     - 其它请到 %TEMP%\dd_*.log 查看安装日志
    goto end
)

echo.
echo ==========================================
echo  [OK] MSVC Build Tools 安装完成！
echo  路径：D:\Apps\MSVC Build Tools
echo  现在可以回到对话继续 Cython 编译
echo ==========================================

:end
echo.
pause
endlocal
exit /b
