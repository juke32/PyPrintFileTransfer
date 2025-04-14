# -*- mode: python ; coding: utf-8 -*-
import sys
from os import path

block_cipher = None

# Define additional data files - ensure icon is included
added_files = [
    ('icon0.1.ico', '.'),
]

a = Analysis(
    ['file_transfer.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['win32print', 'win32api', 'win32gui', 'win32con', 'win32gui_struct'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='file_transfer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon0.1.ico',  # Changed from list to string
    uac_admin=True,
    compatibility_mode={
        'win_ver': '5.1.2600',  # Windows XP
        'dep': False,
        'aslr': False
    }
)
