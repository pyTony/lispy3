"""Tests for View > Open terminal: which terminal program is started, and how.

Run:  python -m unittest discover tests
"""
import unittest

from test_machine_args import machine


def which_of(*found):
    """A stand-in for shutil.which that finds only these programs."""
    return lambda name: "/bin/" + name if name in found else None


class TerminalCommand(unittest.TestCase):
    def command(self, platform, *found, **env):
        return machine.terminal_command("/work", platform, which_of(*found), env)

    def test_windows_prefers_windows_terminal(self):
        """On Windows, Windows Terminal is used when installed, opened in the folder."""
        self.assertEqual(self.command("win32", "wt.exe"), ["wt.exe", "-d", "/work"])

    def test_windows_falls_back_to_cmd(self):
        """Without Windows Terminal, cmd.exe or COMSPEC is used."""
        self.assertEqual(self.command("win32"), ["cmd.exe"])
        self.assertEqual(self.command("win32", COMSPEC=r"C:\cmd.exe"), [r"C:\cmd.exe"])

    def test_linux_uses_terminal_variable_first(self):
        """On Linux, the TERMINAL variable wins over other terminals."""
        self.assertEqual(self.command("linux", "foot", "xterm", TERMINAL="foot"), ["foot"])

    def test_linux_passes_the_folder_to_terminals_that_take_it(self):
        """Terminals that can start in a folder are told which one."""
        self.assertEqual(self.command("linux", "gnome-terminal", "xterm"),
                         ["gnome-terminal", "--working-directory=/work"])
        self.assertEqual(self.command("linux", "xterm"), ["xterm"])

    def test_wsl_without_linux_terminal_uses_windows_one(self):
        """In WSL with no Linux terminal, a Windows one opens WSL in the folder."""
        self.assertEqual(self.command("linux", "wt.exe", WSL_DISTRO_NAME="Ubuntu"),
                         ["wt.exe", "wsl.exe", "--cd", "/work"])
        self.assertEqual(self.command("linux", "cmd.exe", WSL_DISTRO_NAME="Ubuntu"),
                         ["cmd.exe", "/c", "start", "wsl.exe", "--cd", "/work"])

    def test_none_found(self):
        """With no terminal found, nothing is started."""
        self.assertIsNone(self.command("linux"))


if __name__ == "__main__":
    unittest.main()
