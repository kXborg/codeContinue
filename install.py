#!/usr/bin/env python3
"""
CodeContinue Sublime Text 4 Package Installer
Automatically detects Sublime Text 4 installation and installs the package.
Cross-platform support for Windows, macOS, and Linux.
"""

import os
import sys
import shutil
import json
import platform
import subprocess
from pathlib import Path


def get_os_type():
    """Detect operating system."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    else:
        return "unknown"


def find_sublime_text_4_windows():
    """Find Sublime Text 4 on Windows using registry."""
    try:
        import winreg
    except ImportError:
        print("ERROR: winreg module not available")
        return None
    
    try:
        # Try HKEY_LOCAL_MACHINE first
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                try:
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        if "Sublime Text" in display_name and "4" in display_name:
                            install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            if install_location and os.path.isdir(install_location):
                                return install_location
                except (FileNotFoundError, OSError):
                    continue
        
        # Try HKEY_CURRENT_USER as fallback
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                try:
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        if "Sublime Text" in display_name and "4" in display_name:
                            install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            if install_location and os.path.isdir(install_location):
                                return install_location
                except (FileNotFoundError, OSError):
                    continue
        
        # Try common installation paths as fallback
        common_paths = [
            os.path.expandvars(r"%ProgramFiles%\Sublime Text"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Sublime Text"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Sublime Text"),
        ]
        
        for path in common_paths:
            if os.path.isdir(path):
                exe_path = os.path.join(path, "sublime_text.exe")
                if os.path.isfile(exe_path):
                    return path
        
        return None
    
    except Exception as e:
        print(f"ERROR: Failed to search registry: {e}")
        return None


def find_sublime_text_4_macos():
    """Find Sublime Text 4 on macOS."""
    common_paths = [
        "/Applications/Sublime Text.app/Contents/SharedSupport/bin",
        "/Applications/Sublime Text.app",
    ]
    
    for path in common_paths:
        if os.path.isdir(path):
            return path
    
    # Try using 'which' command
    try:
        result = subprocess.run(["which", "subl"], capture_output=True, text=True)
        if result.returncode == 0:
            return os.path.dirname(result.stdout.strip())
    except:
        pass
    
    return None


def find_sublime_text_4_linux():
    """Find Sublime Text 4 on Linux."""
    common_paths = [
        "/opt/sublime_text",
        "/usr/bin",
        "/usr/local/bin",
        os.path.expanduser("~/.local/bin"),
    ]
    
    for path in common_paths:
        if os.path.isdir(path):
            sublime_exe = os.path.join(path, "sublime_text")
            if os.path.isfile(sublime_exe):
                return path
    
    # Try using 'which' command
    try:
        result = subprocess.run(["which", "subl"], capture_output=True, text=True)
        if result.returncode == 0:
            return os.path.dirname(result.stdout.strip())
        
        result = subprocess.run(["which", "sublime_text"], capture_output=True, text=True)
        if result.returncode == 0:
            return os.path.dirname(result.stdout.strip())
    except:
        pass
    
    return None


def find_sublime_text_4():
    """Find Sublime Text 4 installation directory (cross-platform)."""
    os_type = get_os_type()
    
    if os_type == "windows":
        return find_sublime_text_4_windows()
    elif os_type == "macos":
        return find_sublime_text_4_macos()
    elif os_type == "linux":
        return find_sublime_text_4_linux()
    else:
        return None


def get_packages_directory():
    """Get the Packages directory for Sublime Text (cross-platform)."""
    os_type = get_os_type()
    
    if os_type == "windows":
        return os.path.expandvars(r"%APPDATA%\Sublime Text\Packages")
    elif os_type == "macos":
        return os.path.expanduser("~/Library/Application Support/Sublime Text/Packages")
    elif os_type == "linux":
        return os.path.expanduser("~/.config/sublime-text/Packages")
    else:
        return None


def install_package(sublime_path, packages_dir, script_dir):
    """Install the CodeContinue package."""
    
    package_name = "CodeContinue"
    package_dest = os.path.join(packages_dir, package_name)
    
    # Create package directory if it doesn't exist
    try:
        os.makedirs(package_dest, exist_ok=True)
        print(f"✓ Package directory created: {package_dest}")
    except Exception as e:
        print(f"ERROR: Could not create package directory: {e}")
        return False
    
    # Files to copy
    files_to_copy = [
        "codeContinue.py",
        "CodeContinue.sublime-settings",
        "Default.sublime-keymap",
        "messages.json",
        "LICENSE",
        "README.md",
        "PACKAGE_STRUCTURE.md",
    ]
    
    # Directories to copy
    dirs_to_copy = ["messages"]
    
    # Copy files
    for file_name in files_to_copy:
        src = os.path.join(script_dir, file_name)
        dst = os.path.join(package_dest, file_name)
        
        if not os.path.exists(src):
            print(f"⚠ Warning: {file_name} not found in script directory")
            continue
        
        try:
            shutil.copy2(src, dst)
            print(f"✓ Copied: {file_name}")
        except Exception as e:
            print(f"ERROR: Failed to copy {file_name}: {e}")
            return False
    
    # Copy directories
    for dir_name in dirs_to_copy:
        src = os.path.join(script_dir, dir_name)
        dst = os.path.join(package_dest, dir_name)
        
        if not os.path.exists(src):
            print(f"⚠ Warning: {dir_name} directory not found in script directory")
            continue
        
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"✓ Copied directory: {dir_name}")
        except Exception as e:
            print(f"ERROR: Failed to copy {dir_name}: {e}")
            return False
    
    return True


def main():
    """Main installation function."""
    os_type = get_os_type()
    
    print("=" * 60)
    print("CodeContinue Sublime Text 4 Package Installer")
    print(f"Detected OS: {os_type.upper()}")
    print("=" * 60)
    print()
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Step 1: Find Sublime Text 4
    print("Step 1: Locating Sublime Text 4...")
    sublime_path = find_sublime_text_4()
    
    if not sublime_path:
        print("ERROR: Sublime Text 4 not found!")
        print("Please ensure Sublime Text 4 is installed.")
        
        if os_type == "windows":
            print("\nInstallation paths checked:")
            print("  - HKEY_LOCAL_MACHINE registry")
            print("  - HKEY_CURRENT_USER registry")
            print("  - C:\\Program Files\\Sublime Text")
            print("  - C:\\Program Files (x86)\\Sublime Text")
            print("  - C:\\Users\\[User]\\AppData\\Local\\Programs\\Sublime Text")
        elif os_type == "macos":
            print("\nInstallation paths checked:")
            print("  - /Applications/Sublime Text.app")
            print("  - /Applications/Sublime Text.app/Contents/SharedSupport/bin")
            print("  - which subl")
        elif os_type == "linux":
            print("\nInstallation paths checked:")
            print("  - /opt/sublime_text")
            print("  - /usr/bin")
            print("  - /usr/local/bin")
            print("  - ~/.local/bin")
            print("  - which subl")
            print("  - which sublime_text")
        
        sys.exit(1)
    
    print(f"✓ Found Sublime Text 4 at: {sublime_path}")
    print()
    
    # Step 2: Get Packages directory
    print("Step 2: Locating Packages directory...")
    packages_dir = get_packages_directory()
    
    if not packages_dir:
        print("ERROR: Could not determine Packages directory!")
        sys.exit(1)
    
    print(f"✓ Packages directory: {packages_dir}")
    print()
    
    # Step 3: Install package
    print("Step 3: Installing CodeContinue package...")
    if install_package(sublime_path, packages_dir, script_dir):
        print()
        print("=" * 60)
        print("✓ Installation completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        
        if os_type == "windows":
            print("1. Restart Sublime Text 4 or reload plugins (Ctrl+Shift+P -> Reload)")
        elif os_type == "macos":
            print("1. Restart Sublime Text 4 or reload plugins (Cmd+Shift+P -> Reload)")
        elif os_type == "linux":
            print("1. Restart Sublime Text 4 or reload plugins (Ctrl+Shift+P -> Reload)")
        
        print("2. The CodeContinue plugin should now be available")
        print("3. Check the bottom status bar for plugin activation")
        print()
        print(f"Package installed to: {os.path.join(packages_dir, 'CodeContinue')}")
        return 0
    else:
        print()
        print("=" * 60)
        print("✗ Installation failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
