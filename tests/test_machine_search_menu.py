from unittest import TestCase
from unittest.mock import Mock, patch
from test_machine_args import machine


class SearchMenuTest(TestCase):
    def test_edit_menu_opens_existing_find_and_replace_bar(self):
        menus=[]
        def menu(*args,**kwargs):
            result=Mock()
            menus.append(result)
            return result
        app=Mock()
        with patch.object(machine.tk,'Menu',side_effect=menu):
            machine.LispMachine._build_menu(app)
        edit=next(call.kwargs['menu'] for call in menus[0].add_cascade.call_args_list if call.kwargs.get('label')=='Edit')
        commands={call.kwargs.get('label'):call.kwargs for call in edit.add_command.call_args_list}
        for label,shortcut,replace in [('Find…','Ctrl+F',False),('Replace…','Ctrl+H',True)]:
            with self.subTest(label=label):
                self.assertIn(label,commands)
                self.assertEqual(commands[label]['accelerator'],shortcut)
                app.search_bar.show_bar.reset_mock()
                commands[label]['command']()
                app.search_bar.show_bar.assert_called_once_with(replace)
