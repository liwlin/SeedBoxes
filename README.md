<h1 align="center">SeedBoxes</h1>

<p align="center">
  基于开源项目 <a href="https://github.com/florianfesti/boxes">Boxes.py</a> 二次开发的桌面客户端<br/>
  中文界面 · 100% 离线 · Windows 单 exe
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3" /></a>
  <img src="https://img.shields.io/badge/python-3.10-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Platform" />
  <a href="https://github.com/liwlin/SeedBoxes/releases/tag/v0.1"><img src="https://img.shields.io/badge/release-v0.1-brightgreen.svg" alt="Release" /></a>
</p>

<p align="center">
  <img src="docs/screenshots/init.png" alt="SeedBoxes 主界面" width="900" />
</p>

<p align="center">
  <em>主界面：左侧分组导航 + 中央分组卡片画廊 + 底部 GPL 致谢</em>
</p>

---

## 简介

SeedBoxes 是基于 [Boxes.py](https://github.com/florianfesti/boxes)（激光切割盒子生成器）开发的桌面客户端，由 [makerseed 种子创客工坊](https://github.com/makerseed) 维护。它把上游 Web 服务器版包装为本地 Windows 桌面 app（PyWebView），并补齐了完整中文界面。

### 主要特性
- **动态发现生成器** — 当前锁定 release-1.2 提交，干净环境验证发现 172 个可视化生成器；旧文档的 179 个来自原本地依赖环境，不作为当前保证
- **完整中文化** — 加载 boxes 自带的 zh_CN.po 翻译，覆盖率 ~98%；客户端层补 4 级 fallback 翻译链处理上游漏译
- **作品参考图** — 169 个生成器配实物照片，10 个无图的自动渲染 SVG 示意图（带角标区分）
- **3 视图导航** — 主页画廊 → 分组浏览 → 编辑器（带面包屑返回）
- **本地渲染** — 所有 SVG 渲染在本地完成，无需联网，无服务器
- **多种输出** — SVG / SVG_Ponoko / PostScript / Lightburn (lbrn2) 直接生成；DXF / GCode / PDF 需系统装 `pstoedit` / `ps2pdf`
- **单文件 .exe** — PyInstaller 打包约 100 MB，复制即用，依赖 Windows 10/11 默认的 WebView2 Runtime

---

## 开发模式

依赖 [uv](https://docs.astral.sh/uv/)（Astral Python 包管理器）。

```cmd
git clone https://github.com/makerseed/SeedBoxes.git
cd SeedBoxes
run_uv.bat
```

首次运行会自动 `uv sync` 拉取依赖（包含从 GitHub 拉 boxes release-1.2），约 2~3 分钟。后续启动秒开。

---

## 打包发布

```cmd
build_uv.bat
```

产物：`dist\SeedBoxes.exe`（约 100 MB，单文件，含 boxes 源码 + Python 运行时 + 全部依赖）。

复制到任意 Windows 10/11 机器即可运行（依赖系统默认的 WebView2 Runtime）。

---

## 启用 PDF / DXF / GCode 输出

默认只能输出 SVG / PS / LBRN2。要输出 DXF/GCode/PLT/PDF：

```cmd
winget install --id=Cybernetic.pstoedit         :: DXF / GCode / PLT
winget install --id=ArtifexSoftware.GhostScript :: PDF (内含 ps2pdf)
```

安装后重启客户端，下拉框会自动出现新格式选项。

---

## 加密路径（可选）

`backend.py` 是核心业务代码。如需防反编译，可用 Cython 编译为 `.pyd`：

```cmd
install_msvc.bat        :: 一次性装 MSVC Build Tools (~4 GB)
build_pyd.bat           :: backend.py → backend.cp310-win_amd64.pyd
build_uv.bat            :: 重新打包，自动用 .pyd 替代 .py
```

加密后反编译需 IDA / Ghidra 等逆向工具，强度约 ★★★★。

---

## 项目结构

```
SeedBoxes/
├── app.py                  PyWebView 入口
├── backend.py              JS↔Python 桥接 API（含 i18n / 自渲染兜底 / 边缘字符映射）
├── web/                    前端
│   ├── index.html / app.js / styles.css
│   ├── seedboxes-logo.svg  主软件 logo
│   └── makerseed-logo.svg  种子创客工坊标识
├── pyproject.toml          uv 项目（boxes 通过 git 引用上游 release-1.2）
├── uv.lock                 依赖锁文件
├── SeedBoxes.spec          PyInstaller 打包配置
├── logo.ico                .exe 图标（多尺寸）
├── run_uv.bat / build_uv.bat                       开发 / 打包
├── build_pyd.bat / setup_ext.py / install_msvc.bat 加密路径预备
├── README.md / DEVELOPMENT.md / CLAUDE.md          文档
└── LICENSE                 GPL-3.0
```

---

## 许可

本项目采用 **GPL-3.0-or-later**，与上游 boxes 一致。

依赖：
- [boxes](https://github.com/florianfesti/boxes) (GPL-3.0) by Florian Festi — 核心渲染引擎
- [pywebview](https://github.com/r0x0r/pywebview) (BSD-3-Clause) — 桌面框架

如分发本程序，需附带源码或源码获取方式（GPL 要求）。

---

## 致谢

- [Florian Festi](https://github.com/florianfesti) — boxes.py 原作者
- 上游 zh_CN 翻译贡献者：裘炯涛 \<qiujiongtao@163.com\>

© makerseed 种子创客工坊

## 制造升级开发分支

项目名称保持 **SeedBoxes**。开发方案位于 `docs/superpowers/plans/2026-10-01-seedboxes-manufacturing-upgrade.md`，进度与验证边界位于 `docs/development/manufacturing-progress.md`。

```bash
uv sync --locked
uv run --locked pytest -q
uv run --locked python scripts/verify_baseline.py
```

Boxes.py 固定至 `9d93cd81b05d6ef5b0f3d4b4d6ed7eaf5bbed0dd`，不再引用旧开发机相邻目录。上方作品图片统计是旧版本记录；当前实际生成器数量与格式以基线脚本输出为准。

### 制造基础开发分支（T01–T04）

新增受限 `ClosedBox` 结构化几何后端：六块板的稳定身份、名义轮廓、补偿刀路、装配坐标和工程契约。桌面界面与传统二维流程保持现状。诊断命令：

```bash
uv sync --locked
uv run --locked pytest -q
uv run --locked python scripts/generate_model.py tests/fixtures/project.json --output model.json
```

`model.json` 是开发检查数据，不是可直接交给机器的制造文件。尚未实现制造体检、排版、工程保存和三维界面；Windows 打包与实物试切仍待验收。支持范围与决策见 [开发进度](docs/development/manufacturing-progress.md)。
