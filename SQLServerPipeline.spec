# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pipeline_gui_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('ui/icons', 'ui/icons'),
        ('.env.example', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        # Third-party libraries
        'customtkinter',
        'pyodbc',
        'sqlalchemy.dialects.mssql',
        'openpyxl',
        'xlrd',
        'send2trash',
        'python-dateutil',
        # Local packages
        'ui',
        'ui.login_window',
        'ui.main_window',
        'ui.loading_dialog',
        'ui.icon_manager',
        'ui.ui_callbacks',
        'services',
        'services.settings_manager',
        'utils',
        'utils.logger',
        'utils.error_helpers',
        'utils.file_helpers',
        'utils.helpers',
        'utils.sql_utils',
        'utils.ui_helpers',
        'utils.validators',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ML libraries - not needed for GUI-only version
        'torch',
        'transformers',
        'sentence_transformers',
        'sklearn',
        'scikit-learn',
        'numpy.f2py',
        # Matplotlib - if not used
        'matplotlib',
        # Testing frameworks
        'unittest',
        'pytest',
        'test',
        'tests',
        # Addon directory
        'addons',
        # Other large packages not needed
        'PIL.ImageQt',
        'IPython',
        'notebook',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SQLServerPipeline',
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
    icon=['build_resources\\app_icon.ico'],
)
