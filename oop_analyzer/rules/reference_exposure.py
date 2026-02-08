"""
Reference Exposure Rule.

This rule detects methods that return references to internal mutable state,
which can break encapsulation by allowing external code to modify the
object's internal representation and potentially break invariants.
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class ReferenceExposureRule(BaseRule):
    """
    Detects methods that expose internal mutable state.

    Patterns detected:
    - Getters returning self._collection directly (lists, dicts, sets)
    - Methods returning self._mutable_object without copying
    - Properties that expose internal mutable state

    These patterns allow external code to modify internal state,
    breaking encapsulation and potentially violating invariants.
    """

    name = "reference_exposure"
    description = "Detect methods exposing internal mutable state"
    severity = "warning"

    # Mutable collection types
    MUTABLE_TYPES = {"list", "dict", "set", "bytearray"}

    # Method names that suggest returning collections
    GETTER_PATTERNS = {
        "get_",
        "get",
        "items",
        "values",
        "keys",
        "all_",
        "list_",
        "fetch_",
        "retrieve_",
        "load_",
    }

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.check_properties = self.options.get("check_properties", True)
        self.check_getters = self.options.get("check_getters", True)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for reference exposure patterns."""
        visitor = ReferenceExposureVisitor(
            file_path=file_path,
            source=source,
            check_properties=self.check_properties,
            check_getters=self.check_getters,
            mutable_types=self.MUTABLE_TYPES,
            getter_patterns=self.GETTER_PATTERNS,
        )
        visitor.visit(tree)

        return RuleResult(
            rule_name=self.name,
            violations=visitor.violations,
            summary={
                "total_exposures": len(visitor.violations),
                "property_exposures": visitor.property_exposure_count,
                "getter_exposures": visitor.getter_exposure_count,
            },
            metadata={
                "patterns": visitor.patterns,
            },
        )


class ReferenceExposureVisitor(ast.NodeVisitor):
    """AST visitor that detects reference exposure patterns."""

    def __init__(
        self,
        file_path: str,
        source: str,
        check_properties: bool = True,
        check_getters: bool = True,
        mutable_types: set[str] | None = None,
        getter_patterns: set[str] | None = None,
    ):
        self.file_path = file_path
        self.source = source
        self.check_properties = check_properties
        self.check_getters = check_getters
        self.mutable_types = mutable_types or set()
        self.getter_patterns = getter_patterns or set()

        self.violations: list[RuleViolation] = []
        self.patterns: list[dict[str, Any]] = []
        self.property_exposure_count = 0
        self.getter_exposure_count = 0

        self._current_class: str | None = None
        self._class_attributes: dict[str, set[str]] = {}  # class -> private attributes
        self._in_property = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context and collect private attributes."""
        old_class = self._current_class
        self._current_class = node.name

        # Collect private attributes from __init__
        self._class_attributes[node.name] = self._collect_private_attributes(node)

        self.generic_visit(node)
        self._current_class = old_class

    def _collect_private_attributes(self, class_node: ast.ClassDef) -> set[str]:
        """Collect private attribute names from a class."""
        private_attrs: set[str] = set()

        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in ast.walk(item):
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if isinstance(target.value, ast.Name):
                                    if target.value.id == "self":
                                        if target.attr.startswith("_"):
                                            private_attrs.add(target.attr)

        return private_attrs

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze methods for reference exposure."""
        if not self._current_class:
            self.generic_visit(node)
            return

        # Check if it's a property
        is_property = self._is_property(node)

        if is_property and self.check_properties:
            self._check_method_for_exposure(node, is_property=True)
        elif self.check_getters and self._is_getter_method(node.name):
            self._check_method_for_exposure(node, is_property=False)
        elif self.check_getters:
            # Check any method that returns self._something
            self._check_method_for_exposure(node, is_property=False)

        self.generic_visit(node)

    def _is_property(self, node: ast.FunctionDef) -> bool:
        """Check if a method is decorated with @property."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "property":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "getter":
                return True
        return False

    def _is_getter_method(self, name: str) -> bool:
        """Check if method name suggests it's a getter."""
        name_lower = name.lower()
        for pattern in self.getter_patterns:
            if name_lower.startswith(pattern) or name_lower == pattern.rstrip("_"):
                return True
        return False

    def _check_method_for_exposure(
        self,
        node: ast.FunctionDef,
        is_property: bool,
    ) -> None:
        """Check if a method exposes internal mutable state."""
        # Find return statements
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value:
                exposure = self._check_return_value(stmt.value, node)
                if exposure:
                    self._add_violation(node, stmt, exposure, is_property)

    def _check_return_value(
        self,
        value: ast.expr,
        method: ast.FunctionDef,
    ) -> dict[str, Any] | None:
        """Check if a return value exposes internal state."""
        # Direct return of self._attribute
        if isinstance(value, ast.Attribute):
            if isinstance(value.value, ast.Name) and value.value.id == "self":
                attr_name = value.attr
                if attr_name.startswith("_"):
                    return {
                        "type": "direct_return",
                        "attribute": attr_name,
                        "is_private": True,
                    }

        # Return of self._attr.something (chained access)
        if isinstance(value, ast.Subscript) and isinstance(value.value, ast.Attribute):
            if isinstance(value.value.value, ast.Name):
                if value.value.value.id == "self":
                    attr_name = value.value.attr
                    if attr_name.startswith("_"):
                        return {
                            "type": "subscript_return",
                            "attribute": attr_name,
                            "is_private": True,
                        }

        # Check for returning mutable collection attributes
        if isinstance(value, ast.Attribute):
            if isinstance(value.value, ast.Name) and value.value.id == "self":
                # Check if it's a known mutable type based on naming conventions
                attr_name = value.attr
                if self._looks_like_collection(attr_name):
                    return {
                        "type": "collection_return",
                        "attribute": attr_name,
                        "is_private": attr_name.startswith("_"),
                    }

        return None

    def _looks_like_collection(self, name: str) -> bool:
        """Check if an attribute name suggests it's a collection."""
        collection_hints = {
            "list",
            "items",
            "elements",
            "entries",
            "records",
            "data",
            "values",
            "keys",
            "children",
            "nodes",
            "cache",
            "buffer",
            "queue",
            "stack",
            "pool",
            "mapping",
            "dict",
            "set",
            "collection",
            "array",
        }

        name_lower = name.lower().lstrip("_")

        # Check if name ends with 's' (plural) suggesting collection
        if name_lower.endswith("s") and len(name_lower) > 2:
            return True

        # Check for collection-like names
        return any(hint in name_lower for hint in collection_hints)

    def _add_violation(
        self,
        method: ast.FunctionDef,
        return_stmt: ast.Return,
        exposure: dict[str, Any],
        is_property: bool,
    ) -> None:
        """Add a violation for reference exposure."""
        attr_name = exposure.get("attribute", "unknown")
        exposure_type = exposure.get("type", "unknown")

        if is_property:
            self.property_exposure_count += 1
            method_type = "Property"
        else:
            self.getter_exposure_count += 1
            method_type = "Method"

        if exposure_type == "direct_return":
            message = (
                f"{method_type} '{method.name}' returns internal attribute 'self.{attr_name}' directly. "
                f"This exposes internal state and may break encapsulation."
            )
            suggestion = (
                f"Return a copy of the data instead: return self.{attr_name}.copy() for collections, "
                f"or return a defensive copy/immutable view. Consider if the data should be exposed at all."
            )
        elif exposure_type == "collection_return":
            message = (
                f"{method_type} '{method.name}' appears to return a mutable collection 'self.{attr_name}'. "
                f"External code could modify internal state."
            )
            suggestion = (
                f"Return a copy: return list(self.{attr_name}) or return self.{attr_name}.copy(). "
                f"For read-only access, consider returning a tuple or frozenset."
            )
        else:
            message = (
                f"{method_type} '{method.name}' may expose internal state through 'self.{attr_name}'. "
                f"This could allow external modification of object internals."
            )
            suggestion = (
                "Ensure you're returning a copy of mutable data, not a reference. "
                "Consider using defensive copying or returning immutable types."
            )

        self.violations.append(
            RuleViolation(
                rule_name="reference_exposure",
                message=message,
                file_path=self.file_path,
                line=return_stmt.lineno,
                column=return_stmt.col_offset,
                severity="warning",
                suggestion=suggestion,
                code_snippet=self._get_source_line(return_stmt.lineno),
                metadata={
                    "pattern": "reference_exposure",
                    "method": method.name,
                    "attribute": attr_name,
                    "exposure_type": exposure_type,
                    "is_property": is_property,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": exposure_type,
                "line": return_stmt.lineno,
                "method": method.name,
                "attribute": attr_name,
                "is_property": is_property,
            }
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
