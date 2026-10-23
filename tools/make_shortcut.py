"""Put a "Lispy Machine" launcher with the λ icon on the desktop (Windows or Linux).

    python tools/make_shortcut.py

Same as running icons/make_shortcut.py, which does the work: it uses
icons/lispy_machine.ico and needs no pywin32.
"""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons", "make_shortcut.py"),
               run_name="__main__")
