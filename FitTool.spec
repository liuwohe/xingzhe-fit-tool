# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ui/styles.py', 'ui')],
    hiddenimports=['core', 'core.models', 'core.xingzhe_client', 'core.onelap_client', 'core.gpx_to_fit', 'ui', 'ui.main_window', 'ui.xingzhe_tab', 'ui.onelap_tab', 'ui.settings_tab', 'ui.auto_sync_tab', 'ui.styles', 'gpxpy', 'garmin_fit_sdk', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FitTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FitTool',
)
