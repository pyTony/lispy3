"""Exercise real SDL plus GUI worker dispatch in an isolated process."""
import os
from pathlib import Path
import subprocess
import sys
from unittest import TestCase
from support import REPO_DIR


class GraphicsSDLIntegrationTest(TestCase):
    def test_sdl_close_and_gui_idle_event_pump(self):
        script = r'''
import importlib.machinery, importlib.util, sys, threading, time
from unittest.mock import patch
try:
    import pygame
except ImportError:
    sys.exit(77)
loader=importlib.machinery.SourceFileLoader('machine_probe','lispy_machine.pyw')
spec=importlib.util.spec_from_loader(loader.name,loader)
m=importlib.util.module_from_spec(spec);sys.modules[loader.name]=m;loader.exec_module(m)
with patch.object(m,'load_settings',return_value={'startup_run':False,'startup_show_buffer':False}), patch.object(m,'save_settings'):
    try:
        app=m.LispMachine([])
    except m.tk.TclError as error:
        if 'display' in str(error).lower():sys.exit(77)
        raise
    app.withdraw()
    try:
        m.L.load_workspace('mini-basic')
        result=[]
        app._start(lambda:m.L.eval_exp(m.L.parse('(bbc-run "MODE 9:GCOL 1:MOVE 0,0:DRAW 12,0")'),m.L.global_env),lambda value,stopped:result.append(value))
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update();time.sleep(.005)
        assert app._job is None and result == [False],result
        assert m.L.eval_exp(m.L.parse('(graphics-window-open?)'),m.L.global_env)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        deadline=time.monotonic()+3
        while m.L.eval_exp(m.L.parse('(graphics-window-open?)'),m.L.global_env) and time.monotonic()<deadline:
            app.update();time.sleep(.005)
        assert not m.L.eval_exp(m.L.parse('(graphics-window-open?)'),m.L.global_env)
        m.L.eval_exp(m.L.parse('(bbc-run "MODE 9")'),m.L.global_env)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        from lispy_graphics import pump_windows
        assert not pump_windows()
        # Imported mini-basic owns a separate library environment. Its native
        # graphics calls must dispatch even though it bypasses workspace hooks.
        m.L.workspaces.new()
        m.L.eval_exp(m.L.parse('(import (only mini-basic bbc-run))'),m.L.global_env)
        from lispy_graphics import Graphics
        owner_threads=[]
        original_open=Graphics.open
        def tracked_open(self,*args,**kwargs):
            owner_threads.append(threading.current_thread())
            return original_open(self,*args,**kwargs)
        result.clear()
        with patch.object(Graphics,'open',tracked_open):
            app._start(lambda:m.L.eval_exp(m.L.parse('(bbc-run "MODE 9:GCOL 1:PLOT 0,0")'),m.L.global_env),lambda value,stopped:result.append(value))
            deadline=time.monotonic()+10
            while app._job is not None and time.monotonic()<deadline:
                app.update();time.sleep(.005)
        assert app._job is None and result == [False],result
        assert owner_threads == [threading.main_thread()],owner_threads
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        assert not pump_windows()
    finally:
        pygame.display.quit();app.destroy()
'''
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
        result=subprocess.run([sys.executable,'-c',script],cwd=REPO_DIR,env=env,text=True,capture_output=True,timeout=25)
        if result.returncode==77:
            self.skipTest('pygame or Tk display unavailable')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
