"""Listener output from the Lisp thread is joined before the Tk thread shows it."""
import queue
import threading
from types import SimpleNamespace
from unittest import TestCase
from test_machine_args import machine

LM = machine.LispMachine


def fake_app():
    app = SimpleNamespace(_calls=queue.Queue(), _output_lock=threading.Lock(), _pending_output=None, shown=[])
    app.listener_write = lambda text, tag=None: app.shown.append(('write', text, tag))
    app.clear = lambda: app.shown.append(('clear',))
    return app


def on_worker(fn):
    thread = threading.Thread(target=fn)
    thread.start()
    thread.join()


def drain(app):
    while not app._calls.empty():
        fn, args, _box, _done = app._calls.get()
        fn(*args)


class ListenerOutputBatchingTest(TestCase):
    def test_characters_written_before_the_tk_thread_runs_are_one_write(self):
        app = fake_app()
        on_worker(lambda: [LM._ui_post(app, app.listener_write, ch, 'result') for ch in 'hello\n'])
        self.assertEqual(app._calls.qsize(), 1)
        drain(app)
        self.assertEqual(app.shown, [('write', 'hello\n', 'result')])

    def test_other_calls_keep_their_place_between_output(self):
        app = fake_app()
        def work():
            LM._ui_post(app, app.listener_write, 'before', 'result')
            LM._ui_post(app, app.clear)
            LM._ui_post(app, app.listener_write, 'after', 'result')
            LM._ui_post(app, app.listener_write, ' error', 'error')
        on_worker(work)
        drain(app)
        self.assertEqual(app.shown, [('write', 'before', 'result'), ('clear',),
                                     ('write', 'after', 'result'), ('write', ' error', 'error')])

    def test_output_after_it_was_shown_starts_a_new_write(self):
        app = fake_app()
        on_worker(lambda: LM._ui_post(app, app.listener_write, 'a', 'result'))
        drain(app)
        on_worker(lambda: LM._ui_post(app, app.listener_write, 'b', 'result'))
        drain(app)
        self.assertEqual([item[1] for item in app.shown], ['a', 'b'])
