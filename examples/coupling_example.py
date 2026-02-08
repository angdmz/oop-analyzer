"""
Example: Coupling Rule

This file demonstrates high coupling through imports.
The rule measures dependencies and identifies where abstractions might be missing.

Run: uv run python -m oop_analyzer.cli examples/ --rules coupling
"""

# =============================================================================
# BAD: High coupling - too many direct dependencies
# =============================================================================

import datetime
import hashlib
import json
import logging
import os
import pathlib
import subprocess
import tempfile
import uuid


class HighlyCoupledService:
    """
    BAD: This class depends on many modules directly.
    Changes in any of these modules could affect this class.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = pathlib.Path(tempfile.gettempdir())

    def process_file(self, file_path: str) -> dict:
        # Direct dependency on os
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        # Direct dependency on pathlib
        path = pathlib.Path(file_path)

        # Direct dependency on json
        with open(path) as f:
            data = json.load(f)

        # Direct dependency on datetime
        data["processed_at"] = datetime.datetime.now().isoformat()

        # Direct dependency on uuid
        data["id"] = str(uuid.uuid4())

        # Direct dependency on hashlib
        data["hash"] = hashlib.md5(str(data).encode()).hexdigest()

        return data

    def run_command(self, cmd: str) -> str:
        # Direct dependency on subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.stdout.decode()


# =============================================================================
# GOOD: Lower coupling through abstractions
# =============================================================================

from dataclasses import dataclass
from typing import Protocol


# Define interfaces/protocols for dependencies
class FileSystem(Protocol):
    def exists(self, path: str) -> bool: ...
    def read_json(self, path: str) -> dict: ...


class Clock(Protocol):
    def now(self) -> str: ...


class IdGenerator(Protocol):
    def generate(self) -> str: ...


class Hasher(Protocol):
    def hash(self, data: str) -> str: ...


@dataclass
class ProcessedFile:
    """GOOD: Using a dataclass instead of dict."""

    data: dict
    processed_at: str
    id: str
    hash: str


class LooselyCoupledService:
    """
    GOOD: Dependencies are injected through abstractions.
    This class doesn't know about os, json, datetime, etc.
    """

    def __init__(
        self,
        file_system: FileSystem,
        clock: Clock,
        id_generator: IdGenerator,
        hasher: Hasher,
    ):
        self._fs = file_system
        self._clock = clock
        self._id_gen = id_generator
        self._hasher = hasher

    def process_file(self, file_path: str) -> ProcessedFile:
        if not self._fs.exists(file_path):
            raise FileNotFoundError(file_path)

        data = self._fs.read_json(file_path)

        return ProcessedFile(
            data=data,
            processed_at=self._clock.now(),
            id=self._id_gen.generate(),
            hash=self._hasher.hash(str(data)),
        )


# Concrete implementations (these have the actual dependencies)
class RealFileSystem:
    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def read_json(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)


class RealClock:
    def now(self) -> str:
        return datetime.datetime.now().isoformat()


class UUIDGenerator:
    def generate(self) -> str:
        return str(uuid.uuid4())


class MD5Hasher:
    def hash(self, data: str) -> str:
        return hashlib.md5(data.encode()).hexdigest()


# Now testing is easy - just inject mocks!
class FakeFileSystem:
    def __init__(self, files: dict[str, dict]):
        self._files = files

    def exists(self, path: str) -> bool:
        return path in self._files

    def read_json(self, path: str) -> dict:
        return self._files[path]


class FakeClock:
    def __init__(self, fixed_time: str):
        self._time = fixed_time

    def now(self) -> str:
        return self._time
