# PyInstaller spec for Road Damage Assessment Streamlit app
# Build: pyinstaller road_damage_app.spec
# Output: dist/RoadDamageApp/ (folder mode) or dist/RoadDamageApp.exe (onefile)
#
# NOTE: Streamlit apps need special handling — see https://discuss.streamlit.io/t/can-we-bundle-streamlit-app-with-pyinstaller/13673
# Recommended: use `streamlit run app.py` from PyInstaller-bundled Python instead of freezing Streamlit itself.

# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# Collect Streamlit + ultralytics + supervision data files
datas = []
binaries = []
hiddenimports = []

for pkg in ['streamlit', 'ultralytics', 'supervision', 'cv2', 'PIL', 'pandas', 'numpy', 'torch']:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Add our app + engine_bridge
datas += [('app.py', '.')]
datas += [('engine_bridge.py', '.')]
datas += [('render_video.py', '.')]

# Add dumps engine source (needed at runtime via sys.path)
datas += [
    ('../dumps/src', 'dumps_src/src'),
    ('../dumps/data/pci_astm_d6433.json', 'dumps_data'),
    ('../dumps/models', 'dumps_models'),
]
datas += collect_data_files('streamlit')

a = Analysis(
    ['app.py'],
    pathex=['.', '../dumps'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['engine_bridge', 'src.engine.detector', 'src.engine.pci', 'src.engine.segmenter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib.tests', 'numpy.tests', 'pandas.tests'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RoadDamageApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RoadDamageApp',
)
