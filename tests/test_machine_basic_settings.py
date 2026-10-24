"""Settings feedback remains visible after changing an option."""
import contextlib
from unittest import TestCase
from unittest.mock import Mock, patch
from test_machine_args import machine


class Variable:
    def __init__(self, *args, value=None, **kwargs):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class BasicSettingsTest(TestCase):
    def test_sdl_change_saves_without_closing_and_reopen_reuses_window(self):
        app = Mock()
        app.basic_settings_window = None
        app.settings = {}
        app.basic_output = Variable(value='listener')
        app.basic_pygame = Variable(value=False)
        window, radios, variables = Mock(), [], []
        combo = Mock()
        app._set_basic_number_printing = lambda style: machine.LispMachine._set_basic_number_printing(app, style)
        def variable(*args, **kwargs):
            value = Variable(*args, **kwargs)
            variables.append(value)
            return value
        def radio(*args, **kwargs):
            radios.append(kwargs)
            return Mock()
        with contextlib.ExitStack() as patches:
            top = patches.enter_context(patch.object(machine.tk, 'Toplevel', return_value=window))
            patches.enter_context(patch.object(machine.tk, 'StringVar', side_effect=variable))
            patches.enter_context(patch.object(machine.ttk, 'Radiobutton', side_effect=radio))
            choice = patches.enter_context(patch.object(machine.ttk, 'Combobox', return_value=combo))
            saved = patches.enter_context(patch.object(machine, 'save_settings'))
            for name in ('Frame', 'Label', 'LabelFrame', 'Entry', 'Button'):
                patches.enter_context(patch.object(machine.ttk, name, return_value=Mock()))
            patches.enter_context(patch.object(machine.ttk, 'Checkbutton', side_effect=radio))
            machine.LispMachine._open_basic_settings(app)
            self.assertEqual(len(radios), 1)
            self.assertIn('SDL graphics', radios[0]['text'])
            radios[0]['command']()
            app._save_basic_settings.assert_called_once()
            self.assertEqual(variables[0].get(), 'Saved. Applies to the next run.')
            choice.call_args.kwargs['textvariable'].set('MBASIC')
            combo.bind.call_args.args[1]()
            self.assertEqual(app.settings['basic_number_printing'], 'mbasic')
            self.assertEqual(app.basic_repl.print_style, 'mbasic')
            saved.assert_called_once_with(app.settings)
            self.assertIn('MBASIC', variables[0].get())
            window.destroy.assert_not_called()
            machine.LispMachine._open_basic_settings(app)
            top.assert_called_once()
            window.lift.assert_called_once()
