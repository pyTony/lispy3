"""Put a "Lispy Machine" shortcut with the λ icon on the Windows desktop.

    python icons/make_shortcut.py

The shortcut starts lispy_machine.pyw with pythonw.exe (no console window).
It works from any folder and needs nothing beyond Python: Windows PowerShell
writes the shortcut, so pywin32 is not required.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Paths go to PowerShell as environment variables, so spaces and quotes in
# them need no escaping.
POWERSHELL = r"""
$desktop = [Environment]::GetFolderPath('Desktop')
$link = Join-Path $desktop 'Lispy Machine.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
$s.TargetPath = $env:LISPY_PYTHONW
$s.Arguments = '"' + $env:LISPY_SCRIPT + '"'
$s.WorkingDirectory = $env:LISPY_DIR
$s.IconLocation = $env:LISPY_ICON + ',0'
$s.Description = 'Lispy3 Machine Lisp environment'
$s.Save()
Write-Output $link
"""


def pythonw():
    """pythonw.exe next to the running Python, or that Python itself."""
    folder, exe = os.path.split(sys.executable)
    candidate = os.path.join(folder, exe.lower().replace("python.exe", "pythonw.exe"))
    return candidate if os.path.exists(candidate) else sys.executable


def main():
    if sys.platform != "win32":
        sys.exit("Desktop shortcuts are made this way only on Windows.")
    env = dict(os.environ,
               LISPY_PYTHONW=pythonw(),
               LISPY_SCRIPT=os.path.join(REPO, "lispy_machine.pyw"),
               LISPY_DIR=REPO,
               LISPY_ICON=os.path.join(HERE, "lispy_machine.ico"))
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", POWERSHELL],
        env=env, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit("Could not create the shortcut:\n" + result.stderr)
    print("Shortcut created:", result.stdout.strip())


if __name__ == "__main__":
    main()
