"""A stand-in for Python's turtle module, so the tests run without a window.

lispy3 imports turtle (and through it tkinter) at start-up and wraps every
name in turtle.__all__. The tests put this module in its place first:
each drawing command just records its name and arguments in `calls`.
"""
import types

calls: list = []

_state = {'position': (0.0, 0.0), 'heading': 0.0, 'isdown': True}


class Terminator(Exception):
    """Raised by the real turtle when its window has been closed."""


def _recorder(name):
    def command(*args):
        calls.append((name, args))
    command.__name__ = name
    command.__doc__ = f"Stub for turtle.{name}."
    return command


def position():
    return _state['position']


def heading():
    return _state['heading']


def isdown():
    return _state['isdown']


def setposition(*args):
    calls.append(('setposition', args))
    _state['position'] = args[0] if len(args) == 1 else tuple(args)


def setheading(angle):
    calls.append(('setheading', (angle,)))
    _state['heading'] = angle


def penup():
    calls.append(('penup', ()))
    _state['isdown'] = False


def pendown():
    calls.append(('pendown', ()))
    _state['isdown'] = True


_COMMANDS = ['fd', 'forward', 'bk', 'back', 'lt', 'left', 'rt', 'right', 'goto',
             'pu', 'pd', 'up', 'down', 'clear', 'reset', 'home', 'circle', 'dot',
             'tracer', 'update', 'bgcolor', 'pencolor', 'color', 'speed', 'hideturtle',
             'showturtle', 'width', 'pensize', 'mainloop', 'resetscreen', 'bye']

for _name in _COMMANDS:
    globals()[_name] = _recorder(_name)

__all__ = _COMMANDS + ['position', 'heading', 'isdown', 'setposition', 'setheading',
                       'penup', 'pendown', 'Terminator']

class _Canvas:
    """The Tk canvas, as far as onscroll uses it: bindings are kept in `bindings`."""

    def __init__(self):
        self.bindings = {}

    def bind(self, event_name, handler):
        self.bindings[event_name] = handler

    def unbind(self, event_name):
        self.bindings.pop(event_name, None)

    def canvasx(self, x):
        return x

    def canvasy(self, y):
        return y


canvas = _Canvas()
_screen = types.SimpleNamespace(xscale=1.0, yscale=1.0, getcanvas=lambda: canvas)


def Screen():
    calls.append(('Screen', ()))
    return _screen


TurtleScreen = types.SimpleNamespace(_RUNNING=True)
Turtle = types.SimpleNamespace(_screen=None)


def reset_stub():
    calls.clear()
    _state.update(position=(0.0, 0.0), heading=0.0, isdown=True)
    canvas.bindings.clear()
