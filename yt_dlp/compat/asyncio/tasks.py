# flake8: noqa: F405

from asyncio.tasks import *  # noqa: F403

from ..compat_utils import passthrough_module

passthrough_module(__name__, 'asyncio.tasks')
del passthrough_module

try:  # >= 3.7
    all_tasks
except NameError:
    all_tasks = Task.all_tasks
