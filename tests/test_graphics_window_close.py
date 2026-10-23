"""SDL close events work without opening a desktop window."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from lispy_support.lispy_graphics import Graphics


class GraphicsWindowCloseTest(TestCase):
    def test_quit_closes_display_before_rendering_another_frame(self):
        graphics = Graphics()
        pygame = Mock()
        pygame.QUIT = 256
        pygame.KEYDOWN = 768
        pygame.K_ESCAPE = 27
        event = SimpleNamespace(type=pygame.QUIT)
        pygame.event.get.return_value = [event]
        graphics._pygame = pygame
        graphics._screen = Mock()
        graphics._size = (graphics.width, graphics.height)
        self.assertEqual(graphics.present(), [event])
        pygame.display.quit.assert_called_once()
        pygame.display.flip.assert_not_called()
        self.assertFalse(graphics.window_open)
        self.assertEqual(graphics.present(), [])

    def test_present_before_open_still_reports_error(self):
        with self.assertRaisesRegex(RuntimeError, 'call open'):
            Graphics().present()

    def test_escape_also_closes_display(self):
        graphics = Graphics()
        pygame = Mock(QUIT=256, KEYDOWN=768, K_ESCAPE=27)
        pygame.event.get.return_value = [SimpleNamespace(type=768, key=27)]
        graphics._pygame = pygame
        graphics._screen = Mock()
        graphics._size = (graphics.width, graphics.height)
        graphics.present()
        pygame.display.quit.assert_called_once()
        self.assertFalse(graphics.window_open)


class ClippingTest(TestCase):
    def test_offscreen_line_does_not_walk_every_offscreen_pixel(self):
        graphics = Graphics()
        original = graphics.pixel
        graphics.pixel = Mock(side_effect=original)
        graphics.line(-1000,0,1000,0,(255,0,0))
        self.assertLessEqual(graphics.pixel.call_count, graphics.width)
        self.assertEqual(graphics.get_pixel(0,0), (255,0,0))
        self.assertEqual(graphics.get_pixel(graphics.width-1,0), (255,0,0))
