"""New/open buffers receive keyboard focus after notebook layout."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from test_machine_args import machine


class BufferFocusTest(TestCase):
    def test_new_buffer_focuses_its_editor_after_idle(self):
        tab = Mock()
        app = SimpleNamespace(tabs={}, tab_order=[], notebook=Mock(), _refresh_buffer_list=Mock(), after_idle=Mock(side_effect=lambda callback: callback()))
        with patch.object(machine, 'EditorTab', return_value=tab):
            self.assertIs(machine.LispMachine.new_buffer(app, 'test.lisp'), tab)
        app.notebook.select.assert_called_once_with(tab)
        app.after_idle.assert_called_once_with(tab.text.focus_set)
        tab.text.focus_set.assert_called_once_with()

    def test_open_existing_buffer_focuses_editor_without_reloading(self):
        import os
        tab = Mock()
        tab.path = os.path.abspath('already-open.lisp')
        app = SimpleNamespace(tabs={'test': tab}, notebook=Mock(), after_idle=Mock(side_effect=lambda callback: callback()))
        machine.LispMachine._open_source_path(app, tab.path)
        app.notebook.select.assert_called_once_with(tab)
        tab.text.focus_set.assert_called_once_with()
