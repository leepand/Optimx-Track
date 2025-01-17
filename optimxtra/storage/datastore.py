from __future__ import annotations

import os
from shutil import rmtree
from urllib.parse import urlparse

from optimxtra.opts import options
from optimxtra.storage import serialization
from optimxtra.storage.database import next_uuid
from optimxtra.utils.bunch import Bunch
from optimxtra.utils.exceptions import InvalidInput, T, validate_type


class DataStore(Bunch):
    """
    Extends Bunch by providing a flexible storage manager for the values.
    """

    def to_url(self) -> str:
        """
        Stores the object, and returns a relative url pointing to it.
        """
        return DataStoreIO.serialize_write(dict(self)).url

    @staticmethod
    def from_url(url) -> DataStore:
        """
        Loads an object from an url.
        """
        obj = DataStoreIO(url).read_deserialize(expected_type=dict)
        return DataStore(obj)


class DataStoreIO:
    """
    Handling of data storage outside database.
    Currently, supporting only filesystem storage.
    """

    # Attributes to store and serialize.
    __slots__ = ("url",)
    __state__ = ("url",)

    def __init__(self, url: str):
        """
        Create a new linked object.
        """
        self.url = url

    @classmethod
    def get_filepath(cls, url_unparsed: str) -> str:
        """
        Get pathname prefix, given an url.
        """

        url = urlparse(url_unparsed)
        if url.scheme == "file":
            if not url_unparsed.startswith("file:///"):
                raise InvalidInput(
                    f"Invalid file path, it must start with file:/// but found {url_unparsed}"
                )
            return url.path[1:]
        else:
            raise InvalidInput(f"Unsupported URL scheme: {url.scheme}")

    @classmethod
    def delete(cls, relative_path_prefix: str):
        """
        Delete directory `relative_path_prefix`, used to drop directory
        associated to an experiment being deleted.
        """
        pathdir = (
            DataStoreIO.get_filepath(options().get("datastore.url"))
            + os.sep
            + relative_path_prefix
        )
        rmtree(pathdir, ignore_errors=True)

    @classmethod
    def serialize_write(
        cls, obj: any, relative_path_prefix: str | None = None
    ) -> DataStoreIO:
        """
        Serialize object to file.
        """
        data = serialization.serialize(obj)
        return cls.write(data, relative_path_prefix=relative_path_prefix)

    @classmethod
    def get_pathname_from_url(cls, url):
        pathdir = cls.get_filepath(options().get("datastore.url"))
        pathname = pathdir + os.sep + cls.get_filepath(url)
        return pathname

    @classmethod
    def get_next_pathname_url(cls, relative_path_prefix: str | None = None):
        """
        Generate the next pathname and url to store a new resource.
        """

        relative_path_prefix = options().default_if_null(
            relative_path_prefix, "datastore.relative_path_prefix"
        )
        pathdir = (
            DataStoreIO.get_filepath(options().get("datastore.url"))
            + os.sep
            + relative_path_prefix
        )
        os.makedirs(pathdir, exist_ok=True)
        basename = next_uuid().hex
        pathname = pathdir + os.sep + basename
        url = "file:///" + relative_path_prefix + os.sep + basename
        return pathname, url

    @classmethod
    def write(cls, data: bytes, relative_path_prefix: str | None = None) -> DataStoreIO:
        """
        Create a new linked object "/.../optional relative path prefix/..., write to it,
        and return a DataStore instance.
        """

        pathname, url = cls.get_next_pathname_url(relative_path_prefix)
        with open(pathname, "wb") as f:
            f.write(data)
        return DataStoreIO(url)

    def read(self) -> bytes:
        """
        Return the contents of the linked object.
        """

        pathname = self.get_pathname_from_url(self.url)
        with open(pathname, "rb") as f:
            return f.read()

    def read_deserialize(self, expected_type: T | None = None) -> any:
        data = DataStoreIO(self.url).read()
        obj = serialization.deserialize(data)

        if expected_type:
            validate_type(obj, expected_type)
        return obj

    def __getstate__(self):
        """
        Create state for pickling. Only attributes in `__state__` are considered.
        """
        state = {key: getattr(self, key) for key in self.__state__}
        return state

    def __setstate__(self, state):
        """
        Set state for unpickling.
        """
        # Set state
        for k, v in state.items():
            self.__setattr__(k, v)
