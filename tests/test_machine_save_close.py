import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from test_machine_args import machine


def app_and_tab(path=None):
    tab = Mock()
    tab.name, tab.path, tab.dirty = 'old.bas', path, False
    tab.text.edit_modified.return_value = False
    tab.get_content.return_value = 'PRINT "Mandelbrot"\nREM WAIT -1\n'
    app = Mock()
    app.current_tab.return_value = tab
    app.tabs = {'old.bas': tab}
    app.tab_order = ['old.bas']
    return app, tab


class SaveCloseTest(TestCase):
    def test_ctrl_shortcuts_are_bound_on_editor_and_consume_event(self):
        tab = Mock()
        callbacks = {}
        tab.text.bindtags.return_value=('Text',)
        tab.text.bind.side_effect = lambda event, callback: callbacks.update({event: callback})
        tab.app.bind_class.side_effect = lambda tag, event, callback: callbacks.update({event: callback})
        machine.EditorTab._setup_bindings(tab)
        for event, action in [('<Control-o>', 'open_file'), ('<Control-s>', 'save_current'), ('<Control-w>', 'close_current')]:
            self.assertIn(event, callbacks)
            self.assertEqual(callbacks[event](None), 'break')
            if action == 'save_current':
                getattr(tab.app, action).assert_called_once_with(confirm=True)
            else:
                getattr(tab.app, action).assert_called_once()

    def test_save_confirmation_is_shown_only_after_file_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'confirmed.bas')
            app, tab = app_and_tab(path)
            def confirm(title, message, **kwargs):
                self.assertEqual(title, 'File saved')
                self.assertIn(str(Path(path).resolve()), message)
                self.assertEqual(Path(path).read_text(encoding='utf-8'), tab.get_content())
                self.assertFalse(tab.dirty)
            with patch.object(machine.messagebox, 'showinfo', side_effect=confirm) as notice:
                self.assertTrue(machine.LispMachine.save_current(app, confirm=True))
            notice.assert_called_once()

    def test_failed_save_never_confirms_or_clears_dirty_flag(self):
        app, tab = app_and_tab('cannot-save.bas')
        tab.dirty = True
        with patch('builtins.open', side_effect=OSError('disk full')), patch.object(machine.messagebox, 'showerror') as error, patch.object(machine.messagebox, 'showinfo') as notice:
            self.assertFalse(machine.LispMachine.save_current(app, confirm=True))
        error.assert_called_once()
        notice.assert_not_called()
        self.assertTrue(tab.dirty)

    def test_save_as_confirmation_uses_final_path_and_cancel_has_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'renamed.bas')
            app, tab = app_and_tab()
            with patch.object(machine.filedialog, 'asksaveasfilename', return_value=path), patch.object(machine.messagebox, 'showinfo') as notice:
                self.assertTrue(machine.LispMachine.save_current_as(app, confirm=True))
            self.assertIn(str(Path(path).resolve()), notice.call_args.args[1])
            self.assertEqual(tab.path, path)
            with patch.object(machine.filedialog, 'asksaveasfilename', return_value=''), patch.object(machine.messagebox, 'showinfo') as notice:
                self.assertFalse(machine.LispMachine.save_current_as(app, confirm=True))
            notice.assert_not_called()

    def test_modifications_update_dirty_flag_and_save_event_clears_it(self):
        tab = Mock()
        tab._suppress_modified = False
        tab.text.edit_modified.return_value = True
        machine.EditorTab._on_modified(tab)
        self.assertIs(tab.dirty, True)
        tab.text.edit_modified.return_value = False
        machine.EditorTab._on_modified(tab)
        self.assertIs(tab.dirty, False)

    def test_key_release_does_not_mark_saved_text_modified(self):
        tab = Mock()
        machine.EditorTab._on_key(tab)
        tab.text.edit_modified.assert_not_called()

    def test_saved_basic_reopens_with_rem_wait(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'old.bas')
            app, tab = app_and_tab(path)
            self.assertTrue(machine.LispMachine.save_current(app))
            self.assertEqual(Path(path).read_text(encoding='utf-8'), tab.get_content())
            self.assertFalse(tab.dirty)

    def test_save_as_updates_identity_and_closes_renamed_buffer(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'mandel_opt.bas')
            app, tab = app_and_tab()
            with patch.object(machine.filedialog, 'asksaveasfilename', return_value=path):
                machine.LispMachine.save_current_as(app)
            self.assertEqual(list(app.tabs), ['mandel_opt.bas'])
            self.assertEqual(app.tab_order, ['mandel_opt.bas'])
            self.assertEqual(Path(path).read_text(encoding='utf-8'), tab.get_content())
            machine.LispMachine.close_current(app)
            self.assertEqual(app.tabs, {})
            self.assertEqual(app.tab_order, [])
            tab.destroy.assert_called_once()

    def test_failed_save_as_preserves_original_identity(self):
        app, tab = app_and_tab('old.bas')
        with patch.object(machine.filedialog, 'asksaveasfilename', return_value='new.bas'), patch('builtins.open', side_effect=OSError('disk full')), patch.object(machine.messagebox, 'showerror'):
            self.assertFalse(machine.LispMachine.save_current_as(app))
        self.assertEqual(tab.path, 'old.bas')
        self.assertEqual(tab.name, 'old.bas')
        self.assertEqual(app.tab_order, ['old.bas'])

    def test_close_can_save_edits_before_destroying_tab(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'old.bas')
            app, tab = app_and_tab(path)
            tab.dirty = True
            app.save_current.side_effect = lambda: machine.LispMachine.save_current(app)
            with patch.object(machine.messagebox, 'askyesnocancel', return_value=True):
                machine.LispMachine.close_current(app)
            self.assertIn('REM WAIT -1', Path(path).read_text(encoding='utf-8'))
            tab.destroy.assert_called_once()

    def test_cancel_or_failed_save_keeps_buffer_open(self):
        for answer in (None, True):
            with self.subTest(answer=answer):
                app, tab = app_and_tab('old.bas')
                tab.dirty = True
                app.save_current.return_value = False
                with patch.object(machine.messagebox, 'askyesnocancel', return_value=answer):
                    machine.LispMachine.close_current(app)
                tab.destroy.assert_not_called()
                self.assertEqual(app.tab_order, ['old.bas'])

    def test_save_as_does_not_overwrite_another_tab_with_same_basename(self):
        with tempfile.TemporaryDirectory() as folder:
            app, tab = app_and_tab()
            other = Mock()
            app.tabs['mandel.bas'] = other
            app.tab_order.append('mandel.bas')
            with patch.object(machine.filedialog, 'asksaveasfilename', return_value=str(Path(folder)/'mandel.bas')):
                machine.LispMachine.save_current_as(app)
            self.assertIs(app.tabs['mandel.bas'], other)
            self.assertIs(app.tabs['mandel.bas <2>'], tab)
            self.assertEqual(app.tab_order, ['mandel.bas <2>', 'mandel.bas'])
