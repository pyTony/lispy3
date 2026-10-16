import os
import sys
import win32com.client  # Requires pywin32: pip install pywin32

def create_shortcut():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Lispy Machine.lnk")
    
    # Paths
    target_script = os.path.abspath("lispy_machine.pyw")
    python_w_path = sys.executable.replace("python.exe", "pythonw.exe")  # Runs without console flash
    working_dir = os.path.dirname(target_script)
    
    # Path to your custom icon (change to your .ico filename if different)
    icon_path = os.path.join(working_dir, "favicon.ico") 

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = python_w_path
    shortcut.Arguments = f'"{target_script}"'
    shortcut.WorkingDirectory = working_dir
    shortcut.IconLocation = f"{icon_path}, 0"
    shortcut.Description = "Lispy3 Machine Lisp Environment"
    shortcut.Save()
    print(f"Shortcut successfully created at: {shortcut_path}")

if __name__ == "__main__":
    create_shortcut()