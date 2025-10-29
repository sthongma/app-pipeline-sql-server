# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for SQL Server Pipeline GUI Application
This spec file creates a professional Windows executable with all dependencies
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Application metadata
APP_NAME = 'SQLServerPipeline'
APP_VERSION = '2.2.0'
APP_AUTHOR = 'Your Organization'
APP_DESCRIPTION = 'SQL Server Data Pipeline - Excel/CSV to SQL Server'

# Collect all necessary data files
datas = [
    ('.env.example', '.'),
    ('README.md', '.'),
    ('SECURITY.md', '.'),
    ('PERFORMANCE.md', '.'),
]

# Collect customtkinter theme files
datas += collect_data_files('customtkinter')

# Collect all hidden imports
hiddenimports = [
    'customtkinter',
    'PIL._tkinter_finder',
    'sqlalchemy.sql.default_comparator',
    'pandas',
    'openpyxl',
    'xlrd',
    'pyodbc',
    'numpy',
    'dotenv',
]

# Collect all submodules from our application
hiddenimports += collect_submodules('config')
hiddenimports += collect_submodules('services')
hiddenimports += collect_submodules('ui')
hiddenimports += collect_submodules('utils')

a = Analysis(
    ['../pipeline_gui_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        'tkinter.test',
        'test',
        'tests',
    ],
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
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icon.ico' if os.path.exists('../assets/icon.ico') else None,
    version_info={
        'version': APP_VERSION,
        'description': APP_DESCRIPTION,
        'company': APP_AUTHOR,
        'product': APP_NAME,
    }
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
