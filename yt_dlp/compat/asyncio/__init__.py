# flake8: noqa: F405

from asyncio import *  # noqa: F403

from . import tasks  # noqa: F401

try:
    run  # >= 3.7
except NameError:
    def run(coro):
        try:
            loop = get_event_loop()
        except RuntimeError:
            loop = new_event_loop()
            set_event_loop(loop)
        loop.run_until_complete(coro)
