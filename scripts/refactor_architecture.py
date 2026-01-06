#!/usr/bin/env python3
"""
Architecture Refactoring Script
Moves files to new clean structure without deleting anything.
"""

import os
import shutil
from pathlib import Path

# Project root
ROOT = Path(r"c:\Users\ayana\OneDrive\Desktop\local çalışabilen ML")

def create_folders():
    """Create new directory structure"""
    folders = [
        ROOT / "_legacy_backup",
        ROOT / "app" / "views",
        ROOT / "app" / "widgets",
        ROOT / "app" / "styles",
        ROOT / "src" / "services",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created: {folder}")

def move_to_legacy():
    """Move legacy files to backup"""
    legacy_files = [
        "app/formulation_editor.py",
        "app/components/advanced_ml_panel.py",
        "app/components/ml_panel.py",
        "app/offline_utils.py",
    ]
    
    legacy_dir = ROOT / "_legacy_backup"
    for rel_path in legacy_files:
        src = ROOT / rel_path
        if src.exists():
            dst = legacy_dir / src.name
            shutil.move(str(src), str(dst))
            print(f"[ARCHIVE] {rel_path} -> _legacy_backup/")
        else:
            print(f"[WARN] Not found: {rel_path}")

def move_to_new_structure():
    """Move active files to new folders"""
    
    moves = {
        # Views (major panels)
        "app/components/dashboard.py": "app/views/dashboard_view.py",
        "app/test_results_panel.py": "app/views/test_results_view.py",
        "app/components/passive_ml_panel.py": "app/views/ml_insights_view.py",
        "app/components/material_panel.py": "app/views/material_view.py",
        "app/optimization_panels.py": "app/views/optimization_view.py",
        
        # Widgets (reusable)
        "app/components/sidebar_navigator.py": "app/widgets/sidebar_navigator.py",
        "app/components/status_bar.py": "app/widgets/status_bar.py",
        "app/components/toast_notification.py": "app/widgets/toast_notification.py",
        "app/components/progress_dialog.py": "app/widgets/progress_dialog.py",
        "app/components/quick_actions.py": "app/widgets/quick_actions.py",
        
        # Editor components stay as widgets
        "app/components/editor/excel_style_grid.py": "app/widgets/excel_style_grid.py",
        "app/components/editor/modern_formulation_editor.py": "app/views/formulation_view.py",
        
        # Styles
        "app/theme.py": "app/styles/theme.py",
    }
    
    for src_rel, dst_rel in moves.items():
        src = ROOT / src_rel
        dst = ROOT / dst_rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            print(f"[COPY] {src_rel} -> {dst_rel}")
        else:
            print(f"[WARN] Not found: {src_rel}")

def create_init_files():
    """Create __init__.py files in new folders"""
    init_folders = [
        ROOT / "app" / "views",
        ROOT / "app" / "widgets",
        ROOT / "app" / "styles",
        ROOT / "src" / "services",
    ]
    
    for folder in init_folders:
        init_file = folder / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""\nAuto-generated module init\n"""\n')
            print(f"[INIT] Created: {init_file}")

def main():
    print("=" * 50)
    print("Architecture Refactoring Script")
    print("=" * 50)
    
    print("\n[Step 1] Creating new folders...")
    create_folders()
    
    print("\n[Step 2] Archiving legacy files...")
    move_to_legacy()
    
    print("\n[Step 3] Moving files to new structure...")
    move_to_new_structure()
    
    print("\n[Step 4] Creating __init__.py files...")
    create_init_files()
    
    print("\n" + "=" * 50)
    print("[DONE] Refactoring complete!")
    print("Next: Update imports in main.py and ui_components.py")
    print("=" * 50)

if __name__ == "__main__":
    main()
