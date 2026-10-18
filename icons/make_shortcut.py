"""Put a "Lispy Machine" launcher with the λ icon on the desktop.

    python icons/make_shortcut.py

Windows: a desktop shortcut that starts lispy_machine.pyw with pythonw.exe
(no console window). Windows PowerShell writes it, so pywin32 is not needed.

Linux: a lispy-machine.desktop launcher in ~/.local/share/applications, so
Lispy Machine shows up in the applications menu and the dock with its icon,
plus a copy on the desktop. It starts the editor with the Python that ran this
script, so run it with your venv's python if you use one.

Either way it works from any folder.
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


def windows():
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


DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=Lispy Machine
Comment=Lisp-Machine style editor for lispy3
Exec={exec_line}
Path={repo}
Icon={icon}
Terminal=false
Categories=Development;IDE;
StartupWMClass=LispyMachine
"""


def desktop_quote(arg):
    """Quote one Exec= argument as the Desktop Entry spec asks."""
    for ch in '\\"`$':
        arg = arg.replace(ch, "\\" + ch)
    return '"' + arg + '"'


def desktop_folder():
    """The user's desktop folder (it has a local name in some languages), or None."""
    try:
        folder = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True,
                                text=True).stdout.strip()
    except OSError:
        folder = ""
    folder = folder or os.path.expanduser("~/Desktop")
    home = os.path.expanduser("~").rstrip("/")
    return folder if os.path.isdir(folder) and folder.rstrip("/") != home else None


def linux():
    script = os.path.join(REPO, "lispy_machine.pyw")
    entry = DESKTOP_ENTRY.format(
        exec_line=" ".join(desktop_quote(a) for a in (sys.executable, script)) + " %F",
        repo=REPO, icon=os.path.join(HERE, "lispy_machine.png"))
    apps = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"),
                        "applications")
    targets = [os.path.join(apps, "lispy-machine.desktop")]
    desktop = desktop_folder()
    if desktop:
        targets.append(os.path.join(desktop, "lispy-machine.desktop"))
    for path in targets:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(entry)
        os.chmod(path, 0o755)
        print("Launcher created:", path)
    if desktop:
        # GNOME runs a desktop launcher only once it is marked trusted.
        try:
            subprocess.run(["gio", "set", targets[-1], "metadata::trusted", "true"],
                           capture_output=True)
        except OSError:
            pass


def main():
    if sys.platform == "win32":
        windows()
    elif sys.platform.startswith("linux"):
        linux()
    else:
        sys.exit("Launchers are made this way only on Windows and Linux.")


if __name__ == "__main__":
    main()
