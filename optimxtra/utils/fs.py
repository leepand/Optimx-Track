import fnmatch
import glob
import logging
import os
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp
from pathlib import Path

try:
    from types import NoneType
except:
    NoneType = type(None)

from joblib.externals.loky import get_reusable_executor

from optimxtra.utils.exceptions import InvalidInput

log = logging.getLogger(__name__)


@contextmanager
def tmpdir_ctx():
    """
    Create and enter a temporary directory, deleted as the context exits.
    if `shutdown_joblib_workers` is true, terminate the workers created y joblib.
    This ensures that the current directory is honored by all newly created workers.
    """
    try:
        old_dirname = os.getcwd()
        tmp_dirname = mkdtemp()
        os.chdir(tmp_dirname)

        yield tmp_dirname
    finally:
        os.chdir(old_dirname)
        rmtree(tmp_dirname)


@contextmanager
def chdir_ctx(dirname):
    """
    Enter `dirname` directory, and leave it
    as the context returns.
    """
    try:
        old_dirname = os.getcwd()
        os.chdir(dirname)

        # Joblib keeps the pool of workers alive, with their
        # currently defined active directory.

        # Since we chdir in temporary directories to run
        # tests and examples, if we run multiple examples
        # sequentially as in the tests, we might have
        # workers with an invalid current directory.
        # This is why, whenever we enter a context
        # with a new directory, we force the shutdown
        # of the workers.
        # https://github.com/joblib/joblib/issues/945

        get_reusable_executor().shutdown(wait=True)

        yield dirname
    finally:
        os.chdir(old_dirname)


def globs(src_dir, include="**/*", exclude=None, recursive=True):
    """
    Enumerate files matching the glob patterns in the `include` string list, excluding
    matches in `exclude` string list, inside directory `src_dir`.
    """

    if not os.path.isdir(src_dir):
        raise InvalidInput(f"Source directory '{src_dir}' does not exist")

    # Normalise include/exclude type to list of patterns
    if isinstance(include, str):
        include = [include]
    if isinstance(exclude, str):
        exclude = [exclude]
    if isinstance(exclude, NoneType):
        exclude = []

    candidates = []

    for pattern in include:
        # candidates += glob.glob(pattern, root_dir=src_dir, recursive=recursive)
        candidates += list(str(Path(src_dir).rglob(pattern)))

    # Drop duplicates
    candidates = set(candidates)

    # Let's identify matches we should drop accordingly to `excludes` patterns (or, if not a regular file).
    dropped = []
    for name in candidates:
        if not os.path.isfile(src_dir + os.sep + name):
            dropped.append(name)
        else:
            for pattern in exclude:
                if fnmatch.fnmatch(name, pattern):
                    dropped.append(name)
                    break

    matches = list(candidates - set(dropped))
    return matches
