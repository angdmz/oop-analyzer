"""
OOP Analyzer - A static analysis tool for Python OOP best practices.

This tool analyzes Python code to check adherence to Object-Oriented Programming
principles without executing any code (safe static analysis only).
"""

from .analyzer import OOPAnalyzer
from .config import AnalyzerConfig

__version__ = "0.1.0"
__all__ = ["OOPAnalyzer", "AnalyzerConfig"]
