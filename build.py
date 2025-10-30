#!/usr/bin/env python3
"""
اسکریپت ساخت فایل اجرایی برای Galactic Cinematic Game
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_executable():
    """ساخت فایل اجرایی با PyInstaller"""
    
    print("🔨 Building Galactic Cinematic Game executable...")
    
    # پاک کردن buildهای قبلی
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # دستور PyInstaller
    pyinstaller_cmd = [
        'pyinstaller',
        '--name=GalacticCinematicGame',
        '--onefile',
        '--windowed',
        '--add-data=README.md;.',
        '--icon=assets/icon.ico' if os.path.exists('assets/icon.ico') else '',
        '--hidden-import=pygame',
        '--hidden-import=OpenGL',
        '--hidden-import=numpy',
        'main.py'
    ]
    
    # حذف آیتم‌های خالی
    pyinstaller_cmd = [x for x in pyinstaller_cmd if x]
    
    try:
        # اجرای PyInstaller
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")
        
        # کپی فایل‌های اضافی
        copy_additional_files()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def copy_additional_files():
    """کپی فایل‌های اضافی به پوشه dist"""
    dist_dir = Path('dist')
    files_to_copy = ['README.md', 'LICENSE', 'requirements.txt']
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, dist_dir / file)
            print(f"📄 Copied {file} to dist folder")

def create_installer_script():
    """ایجاد اسکریپت نصب برای لینوکس"""
    install_script = """#!/bin/bash
# Installer Script for Galactic Cinematic Game

echo "🚀 Installing Galactic Cinematic Game..."

# Check if game executable exists
if [ ! -f "GalacticCinematicGame" ]; then
    echo "❌ Game executable not found!"
    exit 1
fi

# Create install directory
INSTALL_DIR="/usr/local/games/galactic-cinematic"
sudo mkdir -p $INSTALL_DIR

# Copy files
sudo cp GalacticCinematicGame $INSTALL_DIR/
sudo cp README.md $INSTALL_DIR/

# Create desktop entry
DESKTOP_ENTRY="/usr/share/applications/galactic-cinematic.desktop"
sudo bash -c "cat > $DESKTOP_ENTRY << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Galactic Cinematic Game
Comment=یک بازی فضایی سینمایی با گرافیک سه‌بعدی
Exec=$INSTALL_DIR/GalacticCinematicGame
Icon=$INSTALL_DIR/icon.png
Terminal=false
Categories=Game;
Keywords=game;space;3d;opengl;
EOF"

echo "✅ Installation completed!"
echo "🎮 You can now find 'Galactic Cinematic Game' in your applications menu"
"""
    
    with open('install_linux.sh', 'w') as f:
        f.write(install_script)
    
    # دادن مجوز اجرا
    os.chmod('install_linux.sh', 0o755)
    print("📜 Created Linux installer script")

if __name__ == "__main__":
    print("🏗️  Galactic Cinematic Game - Build System")
    print("=" * 50)
    
    success = build_executable()
    
    if success and sys.platform.startswith('linux'):
        create_installer_script()
    
    if success:
        print("\n🎉 Build process completed successfully!")
        print("📁 Executable is in the 'dist' folder")
    else:
        print("\n💥 Build process failed!")
        sys.exit(1)
