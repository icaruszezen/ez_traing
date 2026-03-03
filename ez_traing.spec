# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ez_traing (onedir mode)."""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── paths ──────────────────────────────────────────────────────────────
SRC_DIR = os.path.join(SPECPATH, "src")
THIRD_PARTY = os.path.join(SRC_DIR, "third_party")

# ── data files ─────────────────────────────────────────────────────────
datas = []

# qfluentwidgets resources
datas += collect_data_files("qfluentwidgets", includes=["**/*.qss", "**/*.svg",
                                                         "**/*.png", "**/*.ttf",
                                                         "**/*.json"])

# labelImg (full tree, excluding __pycache__ and .pyc)
labelimg_tree = Tree(
    os.path.join(THIRD_PARTY, "labelImg"),
    prefix=os.path.join("third_party", "labelImg"),
    excludes=["__pycache__", "*.pyc"],
)
datas += labelimg_tree

# annotation script templates (shipped as data so users can edit them)
datas += [
    (os.path.join(SRC_DIR, "ez_traing", "annotation_scripts"), os.path.join("ez_traing", "annotation_scripts")),
]

# ── hidden imports ─────────────────────────────────────────────────────
hiddenimports = (
    collect_submodules("qfluentwidgets")
    + collect_submodules("lxml")
    + [
        "cv2",
        "PIL",
        "PIL.Image",
        "yaml",
        "requests",
        "matplotlib",
        "matplotlib.backends.backend_agg",
        "albumentations",
        "numpy",
    ]
)

# ── excludes (torch / ultralytics are too large) ──────────────────────
excludes = ["torch", "torchvision", "torchaudio", "ultralytics", "tkinter"]

# ── analysis ───────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(SRC_DIR, "ez_traing", "main.py")],
    pathex=[SRC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ez_traing",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ez_traing",
)
