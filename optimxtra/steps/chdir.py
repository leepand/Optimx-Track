import os
from functools import partial

from optimxtra import Run


def step_chdir(run: Run, path: str = None):
    """
    Change current directory to `path`.
    """

    if path:
        os.chdir(path)


def chdir(path: str = None) -> callable:
    """
    Change the current directory. If `path` is None,
    it changes the current directory on the worker process
    to the main process directory.
    """

    if not path:
        path = os.getcwd()

    return partial(step_chdir, path=path)
