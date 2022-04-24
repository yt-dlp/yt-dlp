# flake8: noqa: F405

from asyncio.tasks import *  # noqa: F403

try:  # >= 3.7
    all_tasks
except NameError:
    all_tasks = Task.all_tasks
