"""Small JSON configuration. Limits are host policy, never taken from project briefs."""
from dataclasses import dataclass
from pathlib import Path
import re

from .storage import StorageError
from .utils import read_json


@dataclass(frozen=True)
class FactoryConfig:
    timeout_seconds: int = 60
    max_tool_calls: int = 1
    max_output_bytes: int = 65536
    max_file_bytes: int = 10485760
    memory_enabled: bool = False
    python_image: str | None = None

    def __post_init__(self):
        limits = {"timeout_seconds": (1, 600), "max_tool_calls": (1, 10),
                  "max_output_bytes": (1024, 1048576), "max_file_bytes": (1024, 104857600)}
        for key, (low, high) in limits.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise StorageError("Invalid configuration limit: " + key)
        if self.memory_enabled is not False:
            raise StorageError("Automatic memory is not implemented")
        if self.python_image is not None and not re.fullmatch(r"python@sha256:[a-f0-9]{64}", self.python_image):
            raise StorageError("Python image must be pinned to an official-image digest")

    @classmethod
    def load(cls, path: Path):
        data = read_json(path)
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise StorageError("Invalid factory configuration keys")
        return cls(**data)
