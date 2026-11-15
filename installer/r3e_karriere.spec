# PyInstaller-Spec: R3E Karriere als Ordner-Build (dist/R3EKarriere).
# In CI: pyinstaller installer/r3e_karriere.spec --noconfirm
block_cipher = None

a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=[],
    datas=[("../assets/icon.ico", "assets")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="R3EKarriere",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="../assets/icon.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="R3EKarriere",
)
