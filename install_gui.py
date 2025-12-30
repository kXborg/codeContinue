#!/usr/bin/env python3
"""
CodeContinue Sublime Text 4 Package Installer - GUI Version
Cross-platform graphical installer using Tkinter.
"""

import os
import sys
import shutil
import json
import platform
import subprocess
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
except ImportError:
    print("ERROR: tkinter not available. Please install python3-tk package.")
    sys.exit(1)


# Import detection functions from CLI installer
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
        return None
    
    try:
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
    except Exception:
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


def install_package(packages_dir, script_dir, user_config, log_callback):
    """Install the CodeContinue package."""
    
    package_name = "CodeContinue"
    package_dest = os.path.join(packages_dir, package_name)
    
    try:
        os.makedirs(package_dest, exist_ok=True)
        log_callback(f"✓ Package directory created: {package_dest}\n")
    except Exception as e:
        log_callback(f"ERROR: Could not create package directory: {e}\n")
        return False
    
    files_to_copy = [
        "codeContinue.py",
        "Default.sublime-keymap",
        "messages.json",
        "LICENSE",
        "README.md",
        "PACKAGE_STRUCTURE.md",
    ]
    
    dirs_to_copy = ["messages"]
    
    for file_name in files_to_copy:
        src = os.path.join(script_dir, file_name)
        dst = os.path.join(package_dest, file_name)
        
        if not os.path.exists(src):
            log_callback(f"⚠ Warning: {file_name} not found\n")
            continue
        
        try:
            shutil.copy2(src, dst)
            log_callback(f"✓ Copied: {file_name}\n")
        except Exception as e:
            log_callback(f"ERROR: Failed to copy {file_name}: {e}\n")
            return False
    
    if user_config:
        settings_dst = os.path.join(package_dest, "CodeContinue.sublime-settings")
        try:
            with open(settings_dst, 'w') as f:
                json.dump(user_config, f, indent=4)
            log_callback(f"✓ Created settings with your configuration\n")
        except Exception as e:
            log_callback(f"ERROR: Failed to write settings: {e}\n")
            return False
    else:
        src = os.path.join(script_dir, "CodeContinue.sublime-settings")
        dst = os.path.join(package_dest, "CodeContinue.sublime-settings")
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
                log_callback(f"✓ Copied: CodeContinue.sublime-settings\n")
            except Exception as e:
                log_callback(f"ERROR: Failed to copy settings: {e}\n")
                return False
    
    for dir_name in dirs_to_copy:
        src = os.path.join(script_dir, dir_name)
        dst = os.path.join(package_dest, dir_name)
        
        if not os.path.exists(src):
            log_callback(f"⚠ Warning: {dir_name} directory not found\n")
            continue
        
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            log_callback(f"✓ Copied directory: {dir_name}\n")
        except Exception as e:
            log_callback(f"ERROR: Failed to copy {dir_name}: {e}\n")
            return False
    
    return True


class InstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeContinue Installer")
        self.root.geometry("750x680")
        self.root.resizable(False, False)
        
        # DPI awareness for better font rendering on Windows
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        self.os_type = get_os_type()
        self.sublime_path = None
        self.packages_dir = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set better default fonts based on platform
        self.setup_fonts()
        
        self.create_widgets()
        self.detect_sublime()
    
    def setup_fonts(self):
        """Configure better fonts for the platform."""
        if self.os_type == "windows":
            self.title_font = ("Segoe UI", 16, "bold")
            self.header_font = ("Segoe UI", 10)
            self.label_font = ("Segoe UI", 9)
            self.small_font = ("Segoe UI", 8)
            self.mono_font = ("Consolas", 9)
        elif self.os_type == "macos":
            self.title_font = ("SF Pro Display", 16, "bold")
            self.header_font = ("SF Pro Text", 10)
            self.label_font = ("SF Pro Text", 9)
            self.small_font = ("SF Pro Text", 8)
            self.mono_font = ("Menlo", 9)
        else:  # linux
            self.title_font = ("Ubuntu", 16, "bold")
            self.header_font = ("Ubuntu", 10)
            self.label_font = ("Ubuntu", 9)
            self.small_font = ("Ubuntu", 8)
            self.mono_font = ("Ubuntu Mono", 9)
    
    def create_widgets(self):
        # Title
        title_frame = ttk.Frame(self.root, padding="15")
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            title_frame,
            text="CodeContinue Sublime Text 4 Installer",
            font=self.title_font
        )
        title_label.pack(pady=(0, 5))
        
        os_label = ttk.Label(
            title_frame,
            text=f"Detected OS: {self.os_type.upper()}",
            font=self.header_font
        )
        os_label.pack()
        
        # Detection status
        detect_frame = ttk.LabelFrame(self.root, text="Detection", padding="12")
        detect_frame.pack(fill=tk.X, padx=12, pady=8)
        
        self.sublime_label = ttk.Label(detect_frame, text="Searching for Sublime Text 4...", font=self.label_font)
        self.sublime_label.pack(anchor=tk.W, pady=2)
        
        self.packages_label = ttk.Label(detect_frame, text="", font=self.label_font)
        self.packages_label.pack(anchor=tk.W, pady=2)
        
        # Configuration
        config_frame = ttk.LabelFrame(self.root, text="API Configuration", padding="12")
        config_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        # Endpoint
        ttk.Label(config_frame, text="API Endpoint URL:", font=self.label_font).grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.endpoint_var = tk.StringVar(value="https://your-api.com/v1/chat/completions")
        ttk.Entry(config_frame, textvariable=self.endpoint_var, width=58, font=self.label_font).grid(row=0, column=1, pady=4)
        
        # Model
        ttk.Label(config_frame, text="Model Name:", font=self.label_font).grid(row=1, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.model_var = tk.StringVar(value="Qwen/Qwen2.5-Coder-1.5B-Instruct")
        ttk.Entry(config_frame, textvariable=self.model_var, width=58, font=self.label_font).grid(row=1, column=1, pady=4)
        
        # API Key
        ttk.Label(config_frame, text="API Key (optional):", font=self.label_font).grid(row=2, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.api_key_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.api_key_var, width=58, font=self.label_font, show="*").grid(row=2, column=1, pady=4)
        
        # Max context
        ttk.Label(config_frame, text="Max Context Lines:", font=self.label_font).grid(row=3, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.max_context_var = tk.StringVar(value="30")
        ttk.Entry(config_frame, textvariable=self.max_context_var, width=20, font=self.label_font).grid(row=3, column=1, sticky=tk.W, pady=4)
        
        # Timeout
        ttk.Label(config_frame, text="Timeout (ms):", font=self.label_font).grid(row=4, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.timeout_var = tk.StringVar(value="20000")
        ttk.Entry(config_frame, textvariable=self.timeout_var, width=20, font=self.label_font).grid(row=4, column=1, sticky=tk.W, pady=4)
        
        # Languages
        ttk.Label(config_frame, text="Trigger Languages:", font=self.label_font).grid(row=5, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.languages_var = tk.StringVar(value="python,cpp,javascript")
        ttk.Entry(config_frame, textvariable=self.languages_var, width=58, font=self.label_font).grid(row=5, column=1, pady=4)
        ttk.Label(config_frame, text="(comma-separated)", font=self.small_font).grid(row=6, column=1, sticky=tk.W)
        
        # Log output
        log_frame = ttk.LabelFrame(self.root, text="Installation Log", padding="12")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=8, 
            state=tk.DISABLED,
            font=self.mono_font,
            wrap=tk.WORD,
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)
        
        self.install_button = ttk.Button(
            button_frame,
            text="Install CodeContinue",
            command=self.install,
            state=tk.DISABLED
        )
        self.install_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
    
    def log(self, message):
        """Add message to log window."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
    
    def detect_sublime(self):
        """Detect Sublime Text installation."""
        self.log("Detecting Sublime Text 4...\n")
        
        self.sublime_path = find_sublime_text_4()
        
        if self.sublime_path:
            self.sublime_label.config(text=f"✓ Sublime Text 4 found at: {self.sublime_path}")
            self.log(f"✓ Found Sublime Text 4 at: {self.sublime_path}\n")
            
            self.packages_dir = get_packages_directory()
            if self.packages_dir:
                self.packages_label.config(text=f"✓ Packages directory: {self.packages_dir}")
                self.log(f"✓ Packages directory: {self.packages_dir}\n\n")
                self.install_button.config(state=tk.NORMAL)
            else:
                self.packages_label.config(text="✗ Could not determine Packages directory")
                self.log("ERROR: Could not determine Packages directory\n")
        else:
            self.sublime_label.config(text="✗ Sublime Text 4 not found!")
            self.log("ERROR: Sublime Text 4 not found!\n")
            self.log("Please ensure Sublime Text 4 is installed.\n")
            messagebox.showerror(
                "Sublime Text Not Found",
                "Sublime Text 4 was not found on your system.\nPlease install it first."
            )
    
    def install(self):
        """Perform installation in a separate thread."""
        self.install_button.config(state=tk.DISABLED)
        self.log("\n" + "="*60 + "\n")
        self.log("Starting installation...\n")
        self.log("="*60 + "\n\n")
        
        # Run installation in thread to keep GUI responsive
        thread = threading.Thread(target=self.do_install)
        thread.start()
    
    def do_install(self):
        """Actual installation logic."""
        try:
            # Build configuration
            languages = [lang.strip() for lang in self.languages_var.get().split(",")]
            
            config = {
                "endpoint": self.endpoint_var.get(),
                "model": self.model_var.get(),
                "max_context_lines": int(self.max_context_var.get()),
                "timeout_ms": int(self.timeout_var.get()),
                "trigger_language": languages
            }
            
            if self.api_key_var.get():
                config["api_key"] = self.api_key_var.get()
            
            # Install
            success = install_package(self.packages_dir, self.script_dir, config, self.log)
            
            if success:
                self.log("\n" + "="*60 + "\n")
                self.log("✓ Installation completed successfully!\n")
                self.log("="*60 + "\n\n")
                self.log("Next steps:\n")
                
                if self.os_type == "windows":
                    self.log("1. Restart Sublime Text or reload (Ctrl+Shift+P → Reload)\n")
                elif self.os_type == "macos":
                    self.log("1. Restart Sublime Text or reload (Cmd+Shift+P → Reload)\n")
                else:
                    self.log("1. Restart Sublime Text or reload (Ctrl+Shift+P → Reload)\n")
                
                self.log("2. CodeContinue plugin is ready to use\n")
                self.log("3. Check the status bar for plugin activation\n")
                
                messagebox.showinfo(
                    "Installation Complete",
                    "CodeContinue has been installed successfully!\n\n"
                    "Please restart Sublime Text 4 to activate the plugin."
                )
            else:
                self.log("\n" + "="*60 + "\n")
                self.log("✗ Installation failed!\n")
                self.log("="*60 + "\n")
                
                messagebox.showerror(
                    "Installation Failed",
                    "Installation failed. Please check the log for details."
                )
        
        except Exception as e:
            self.log(f"\nERROR: {e}\n")
            messagebox.showerror("Error", f"An error occurred: {e}")
        
        finally:
            self.root.after(0, lambda: self.install_button.config(state=tk.NORMAL))


def main():
    root = tk.Tk()
    app = InstallerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
