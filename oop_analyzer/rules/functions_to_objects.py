"""
Functions to Objects Rule.

This rule detects standalone functions that could be better represented
as objects/classes, following OOP principles.
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class FunctionsToObjectsRule(BaseRule):
    """
    Detects functions that could be replaced by objects.

    Patterns detected:
    - Functions with many parameters (could be a class with attributes)
    - Functions that operate on the same data repeatedly (could be methods)
    - Groups of related functions (could be a class)
    - Functions with complex state management (could be objects)
    - Functions returning dictionaries that could be objects
    """

    name = "functions_to_objects"
    description = "Detect functions that could be objects"
    severity = "info"

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.max_params = self.options.get("max_params", 4)
        self.check_dict_returns = self.options.get("check_dict_returns", True)
        self.check_related_functions = self.options.get("check_related_functions", True)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for functions that could be objects."""
        visitor = FunctionVisitor(
            file_path=file_path,
            source=source,
            max_params=self.max_params,
            check_dict_returns=self.check_dict_returns,
        )
        visitor.visit(tree)

        violations = visitor.violations.copy()

        # Check for related functions (functions with similar prefixes/suffixes)
        if self.check_related_functions:
            related_violations = self._check_related_functions(
                visitor.function_info,
                file_path,
                source,
            )
            violations.extend(related_violations)

        return RuleResult(
            rule_name=self.name,
            violations=violations,
            summary={
                "total_functions": len(visitor.function_info),
                "functions_with_many_params": visitor.many_params_count,
                "functions_returning_dicts": visitor.dict_return_count,
                "related_function_groups": len(self._find_function_groups(visitor.function_info)),
            },
            metadata={
                "functions": visitor.function_info,
                "function_groups": self._find_function_groups(visitor.function_info),
            },
        )

    def _check_related_functions(
        self,
        function_info: list[dict[str, Any]],
        file_path: str,
        source: str,
    ) -> list[RuleViolation]:
        """Check for groups of related functions that could be a class."""
        violations: list[RuleViolation] = []
        groups = self._find_function_groups(function_info)

        for prefix, functions in groups.items():
            if len(functions) >= 3:
                func_names = [f["name"] for f in functions]
                first_line = min(f["line"] for f in functions)

                violations.append(
                    RuleViolation(
                        rule_name="functions_to_objects",
                        message=(
                            f"Found {len(functions)} related functions with prefix '{prefix}_': "
                            f"{', '.join(func_names[:5])}{'...' if len(func_names) > 5 else ''}. "
                            f"Consider grouping into a class."
                        ),
                        file_path=file_path,
                        line=first_line,
                        column=0,
                        severity="info",
                        suggestion=(
                            f"These functions appear related. Consider creating a class "
                            f"'{prefix.title().replace('_', '')}' with these as methods."
                        ),
                        metadata={
                            "pattern": "related_functions",
                            "prefix": prefix,
                            "functions": func_names,
                        },
                    )
                )

        return violations

    def _find_function_groups(
        self,
        function_info: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Find groups of functions with common prefixes."""
        from collections import defaultdict

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for func in function_info:
            name = func["name"]
            # Skip private/dunder functions
            if name.startswith("_"):
                continue

            # Extract prefix (first word before underscore)
            parts = name.split("_")
            if len(parts) >= 2:
                prefix = parts[0]
                if len(prefix) >= 3:  # Meaningful prefix
                    groups[prefix].append(func)

        # Filter to groups with multiple functions
        return {k: v for k, v in groups.items() if len(v) >= 2}


class FunctionVisitor(ast.NodeVisitor):
    """AST visitor that analyzes functions."""

    def __init__(
        self,
        file_path: str,
        source: str,
        max_params: int = 4,
        check_dict_returns: bool = True,
    ):
        self.file_path = file_path
        self.source = source
        self.max_params = max_params
        self.check_dict_returns = check_dict_returns

        self.violations: list[RuleViolation] = []
        self.function_info: list[dict[str, Any]] = []
        self.many_params_count = 0
        self.dict_return_count = 0

        self._in_class = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track when inside a class (skip methods)."""
        old_in_class = self._in_class
        self._in_class = True
        self.generic_visit(node)
        self._in_class = old_in_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze function definitions."""
        # Skip methods (inside classes)
        if self._in_class:
            self.generic_visit(node)
            return

        # Skip private/dunder functions for some checks
        is_private = node.name.startswith("_")

        # Count parameters
        num_params = self._count_params(node)

        # Check for dict returns
        returns_dict = self._returns_dict(node) if self.check_dict_returns else False

        # Store function info
        self.function_info.append(
            {
                "name": node.name,
                "line": node.lineno,
                "params": num_params,
                "returns_dict": returns_dict,
                "is_private": is_private,
            }
        )

        # Check for too many parameters
        if num_params > self.max_params and not is_private:
            self.many_params_count += 1
            self._add_many_params_violation(node, num_params)

        # Check for dict returns
        if returns_dict and not is_private:
            self.dict_return_count += 1
            self._add_dict_return_violation(node)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async functions same as regular functions."""
        if self._in_class:
            self.generic_visit(node)
            return

        is_private = node.name.startswith("_")
        num_params = self._count_params(node)
        returns_dict = self._returns_dict(node) if self.check_dict_returns else False

        self.function_info.append(
            {
                "name": node.name,
                "line": node.lineno,
                "params": num_params,
                "returns_dict": returns_dict,
                "is_private": is_private,
                "is_async": True,
            }
        )

        if num_params > self.max_params and not is_private:
            self.many_params_count += 1
            self._add_many_params_violation(node, num_params)

        if returns_dict and not is_private:
            self.dict_return_count += 1
            self._add_dict_return_violation(node)

        self.generic_visit(node)

    def _count_params(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Count the number of parameters in a function."""
        args = node.args
        count = len(args.args) + len(args.kwonlyargs)
        if args.vararg:
            count += 1
        if args.kwarg:
            count += 1
        return count

    def _returns_dict(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function returns a dictionary literal."""
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                if isinstance(child.value, ast.Dict):
                    return True
                # Check for dict() call
                if isinstance(child.value, ast.Call):
                    if isinstance(child.value.func, ast.Name):
                        if child.value.func.id == "dict":
                            return True
        return False

    def _add_many_params_violation(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        num_params: int,
    ) -> None:
        """Add violation for function with too many parameters."""
        self.violations.append(
            RuleViolation(
                rule_name="functions_to_objects",
                message=(
                    f"Function '{node.name}' has {num_params} parameters. "
                    f"Consider converting to a class."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "Functions with many parameters often indicate the need for an object. "
                    "Consider creating a class where parameters become attributes, "
                    "and the function becomes a method."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "many_parameters",
                    "function": node.name,
                    "param_count": num_params,
                },
            )
        )

    def _add_dict_return_violation(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Add violation for function returning a dict."""
        self.violations.append(
            RuleViolation(
                rule_name="functions_to_objects",
                message=(
                    f"Function '{node.name}' returns a dictionary. "
                    f"Consider using a dataclass or named tuple instead."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "Returning dictionaries loses type information and makes code "
                    "harder to maintain. Consider using a dataclass, named tuple, "
                    "or a proper class to represent the returned data."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "dict_return",
                    "function": node.name,
                },
            )
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
