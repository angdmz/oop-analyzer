"""
Pytest configuration and fixtures for OOP Analyzer tests.
"""

import tempfile
from pathlib import Path

import pytest

from oop_analyzer import AnalyzerConfig, OOPAnalyzer


@pytest.fixture
def default_config() -> AnalyzerConfig:
    """Default analyzer configuration with all rules enabled."""
    return AnalyzerConfig.default()


@pytest.fixture
def minimal_config() -> AnalyzerConfig:
    """Minimal configuration with only essential rules."""
    return AnalyzerConfig.minimal()


@pytest.fixture
def analyzer(default_config: AnalyzerConfig) -> OOPAnalyzer:
    """Analyzer with default configuration."""
    return OOPAnalyzer(default_config)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_python_file(temp_dir: Path):
    """Factory fixture to create temporary Python files."""

    def _create_file(content: str, name: str = "test_file.py") -> Path:
        file_path = temp_dir / name
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create_file


@pytest.fixture
def temp_module(temp_dir: Path):
    """Factory fixture to create temporary Python modules."""

    def _create_module(files: dict[str, str], module_name: str = "test_module") -> Path:
        module_dir = temp_dir / module_name
        module_dir.mkdir(parents=True, exist_ok=True)

        # Create __init__.py if not provided
        if "__init__.py" not in files:
            (module_dir / "__init__.py").write_text("", encoding="utf-8")

        for filename, content in files.items():
            file_path = module_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        return module_dir

    return _create_module


# Sample code fixtures for testing different rules


@pytest.fixture
def encapsulation_violation_code() -> str:
    """Code with encapsulation violations."""
    return """
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

def process_user(user):
    # Violation: direct property access
    print(user.name)
    if user.age > 18:
        print("Adult")

    # Violation: chained access
    print(user.name.upper())
"""


@pytest.fixture
def encapsulation_clean_code() -> str:
    """Code without encapsulation violations."""
    return """
class User:
    def __init__(self, name, age):
        self._name = name
        self._age = age

    def get_display_name(self):
        return self._name

    def is_adult(self):
        return self._age >= 18

    def greet(self):
        print(f"Hello, {self._name}")

def process_user(user):
    # Good: using methods
    user.greet()
    if user.is_adult():
        print("Adult")
"""


@pytest.fixture
def coupling_high_code() -> str:
    """Code with high coupling (many imports)."""
    return """
import os
import sys
import json
import logging
import datetime
import collections
import functools
import itertools
import pathlib
import typing
import dataclasses
import abc

def do_something():
    pass
"""


@pytest.fixture
def null_object_violation_code() -> str:
    """Code with None usage that could use Null Object pattern."""
    return """
def find_user(user_id):
    if user_id == 0:
        return None
    return {"id": user_id, "name": "Test"}

def process(data=None):
    if data is None:
        return
    print(data)

def get_value(obj):
    result = obj.get_data()
    if result is not None:
        return result.value
    return "default"

def check(x):
    return x if x is not None else "empty"
"""


@pytest.fixture
def polymorphism_violation_code() -> str:
    """Code with if/elif chains that could use polymorphism."""
    return """
class Shape:
    def __init__(self, shape_type):
        self.type = shape_type

def calculate_area(shape):
    if shape.type == "circle":
        return 3.14 * shape.radius ** 2
    elif shape.type == "rectangle":
        return shape.width * shape.height
    elif shape.type == "triangle":
        return 0.5 * shape.base * shape.height
    elif shape.type == "square":
        return shape.side ** 2
    else:
        return 0

def process_animal(animal):
    if isinstance(animal, Dog):
        animal.bark()
    elif isinstance(animal, Cat):
        animal.meow()
    elif isinstance(animal, Bird):
        animal.chirp()
"""


@pytest.fixture
def functions_to_objects_code() -> str:
    """Code with functions that could be objects."""
    return """
def user_create(name, email, age, address, phone, role):
    return {"name": name, "email": email, "age": age}

def user_validate(user):
    pass

def user_save(user):
    pass

def user_delete(user):
    pass

def user_update(user, **kwargs):
    pass

def get_stats():
    return {"count": 10, "average": 5.5, "max": 20}
"""


@pytest.fixture
def clean_oop_code() -> str:
    """Well-designed OOP code with minimal violations."""
    return """
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        pass

    @abstractmethod
    def perimeter(self) -> float:
        pass

class Circle(Shape):
    def __init__(self, radius: float):
        self._radius = radius

    def area(self) -> float:
        return 3.14159 * self._radius ** 2

    def perimeter(self) -> float:
        return 2 * 3.14159 * self._radius

class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self._width = width
        self._height = height

    def area(self) -> float:
        return self._width * self._height

    def perimeter(self) -> float:
        return 2 * (self._width + self._height)

def calculate_total_area(shapes: list[Shape]) -> float:
    return sum(shape.area() for shape in shapes)
"""


@pytest.fixture
def malformed_code() -> str:
    """Syntactically invalid Python code."""
    return """
def broken_function(
    print("missing closing paren"
"""


@pytest.fixture
def empty_code() -> str:
    """Empty Python file."""
    return ""
