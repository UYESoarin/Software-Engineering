# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：打包 levels.json 与 assets/，onefile，无控制台窗口。

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("game")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("levels.json", "."),
        ("assets", "assets"),
    ],
    hiddenimports=hiddenimports,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="YiJianYouYiJian",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
