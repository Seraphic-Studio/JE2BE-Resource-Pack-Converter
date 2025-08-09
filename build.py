#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("Building JE2BE Resource Pack Converter...")
    
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name=je2be',
        '--icon=logo.png',
        '--add-data=mappings;mappings',
        '--add-data=essentials;essentials', 
        '--add-data=rtxfix;rtxfix',
        '--add-data=required;required',
        '--add-data=logo.png;.',
        '--console',
        '--clean',
        'je2be_converter.py'
    ]
    
    print("Running PyInstaller...")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = Path('dist/je2be.exe')
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1024 / 1024
            print(f"Build successful! Created je2be.exe ({size_mb:.1f} MB)")
            
            test_result = subprocess.run([str(exe_path), '--help'], 
                                       capture_output=True, text=True)
            if test_result.returncode == 0:
                print("Executable test passed!")
            else:
                print("Warning: Executable test failed")
        else:
            print("Error: Executable not found")
    else:
        print("Build failed!")
        return 1
    
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
