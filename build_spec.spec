# -*- mode: python ; coding: utf-8 -*-
"""
Paint Formulation AI - PyInstaller Build Specification
=======================================================
Bu dosya, uygulamayı tek bir EXE dosyasına paketlemek için kullanılır.

Kullanım:
    pyinstaller build_spec.spec

Veya direkt olarak:
    pyinstaller --noconfirm --onefile --windowed --icon=assets/icons/app_icon.ico app/main.py
"""

import os
import sys

# Proje kök dizini
ROOT_DIR = os.path.dirname(os.path.abspath(SPEC))

block_cipher = None

# Tüm Python dosyalarını topla
added_files = [
    # Konfigürasyon
    ('config.ini', '.'),
    
    # Veri ve log klasörleri (boş olarak)
    ('data_storage/.gitkeep', 'data_storage'),
    ('logs/.gitkeep', 'logs'),
    
    # Assets
    ('assets/models/.gitkeep', 'assets/models'),
    ('assets/templates/.gitkeep', 'assets/templates'),
    
    # Dokümantasyon
    ('README_TR.txt', '.'),
    ('LISANS.txt', '.'),
]

# Hidden imports (otomatik tespit edilemeyenler)
hidden_imports = [
    'sqlite3',
    'configparser',
    'logging',
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'json',
    'csv',
    'datetime',
    'threading',
    'statistics',
    # Opsiyonel ML kütüphaneleri
    'sklearn',
    'sklearn.ensemble',
    'sklearn.preprocessing',
    'numpy',
    'openpyxl',
]

a = Analysis(
    ['app/main.py'],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Gereksiz büyük modülleri çıkar
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
        'keras',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PaintFormulationAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX sıkıştırma (boyutu küçültür)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Konsol penceresi gösterme (windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app_icon.ico' if os.path.exists('assets/icons/app_icon.ico') else None,
    version='file_version_info.txt' if os.path.exists('file_version_info.txt') else None,
)
