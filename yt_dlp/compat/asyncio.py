# flake8: noqa: F405
from asyncio import *  # noqa: F403

from .compat_utils import passthrough_module

passthrough_module(__name__, 'asyncio')
del passthrough_module

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

try:
    all_tasks  # >= 3.7
except NameError:
    all_tasks = Task.all_tasks
