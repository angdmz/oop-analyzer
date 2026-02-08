"""
Dictionary Usage Rule.

This rule detects dictionary usage that should be replaced by proper objects
like dataclasses, Pydantic models, NamedTuples, or custom classes.

Dictionaries are acceptable for:
- Parsing RPC/REST API responses (at the boundary)
- Dynamic key-value storage where keys are truly dynamic
- Temporary data transformation

Dictionaries should NOT be used for:
- Passing data between abstraction layers
- Function parameters representing structured data
- Return values representing domain objects
- Class attributes storing structured data
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class DictionaryUsageRule(BaseRule):
    """
    Detects dictionary usage that should be replaced by objects.

    Patterns detected:
    - Functions returning dict literals with fixed keys
    - Functions accepting dict parameters for structured data
    - Dict literals with string keys used as structured data
    - Type hints using dict for structured data (Dict[str, Any])
    - Accessing dict with string literal keys repeatedly
    """

    name = "dictionary_usage"
    description = "Detect dictionary usage that should be objects"
    severity = "warning"

    # Patterns that suggest acceptable dict usage (API boundaries)
    API_BOUNDARY_PATTERNS = {
        "response",
        "request",
        "payload",
        "json",
        "data",
        "body",
        "parse",
        "serialize",
        "deserialize",
        "to_dict",
        "from_dict",
        "to_json",
        "from_json",
        "api",
        "http",
        "rest",
        "rpc",
    }

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.min_dict_keys = self.options.get("min_dict_keys", 2)
        self.check_return_dicts = self.options.get("check_return_dicts", True)
        self.check_dict_params = self.options.get("check_dict_params", True)
        self.check_dict_access = self.options.get("check_dict_access", True)
        self.allow_api_boundaries = self.options.get("allow_api_boundaries", True)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for dictionary usage patterns."""
        visitor = DictionaryUsageVisitor(
            file_path=file_path,
            source=source,
            min_dict_keys=self.min_dict_keys,
            check_return_dicts=self.check_return_dicts,
            check_dict_params=self.check_dict_params,
            check_dict_access=self.check_dict_access,
            allow_api_boundaries=self.allow_api_boundaries,
            api_boundary_patterns=self.API_BOUNDARY_PATTERNS,
        )
        visitor.visit(tree)

        return RuleResult(
            rule_name=self.name,
            violations=visitor.violations,
            summary={
                "total_dict_violations": len(visitor.violations),
                "dict_return_violations": visitor.dict_return_count,
                "dict_param_violations": visitor.dict_param_count,
                "dict_access_violations": visitor.dict_access_count,
                "dict_literal_violations": visitor.dict_literal_count,
            },
            metadata={
                "patterns": visitor.patterns,
            },
        )


class DictionaryUsageVisitor(ast.NodeVisitor):
    """AST visitor that detects problematic dictionary usage."""

    def __init__(
        self,
        file_path: str,
        source: str,
        min_dict_keys: int = 2,
        check_return_dicts: bool = True,
        check_dict_params: bool = True,
        check_dict_access: bool = True,
        allow_api_boundaries: bool = True,
        api_boundary_patterns: set[str] | None = None,
    ):
        self.file_path = file_path
        self.source = source
        self.min_dict_keys = min_dict_keys
        self.check_return_dicts = check_return_dicts
        self.check_dict_params = check_dict_params
        self.check_dict_access = check_dict_access
        self.allow_api_boundaries = allow_api_boundaries
        self.api_boundary_patterns = api_boundary_patterns or set()

        self.violations: list[RuleViolation] = []
        self.patterns: list[dict[str, Any]] = []
        self.dict_return_count = 0
        self.dict_param_count = 0
        self.dict_access_count = 0
        self.dict_literal_count = 0

        self._current_function: str | None = None
        self._current_class: str | None = None
        self._dict_key_accesses: dict[str, list[str]] = {}  # var_name -> [keys accessed]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context."""
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze function for dictionary patterns."""
        old_function = self._current_function
        self._current_function = node.name
        self._dict_key_accesses = {}

        # Check if this is an API boundary function
        is_api_boundary = self._is_api_boundary_context(node.name)

        # Check return type hint for Dict[str, Any]
        if self.check_return_dicts and not is_api_boundary:
            self._check_return_type_hint(node)

        # Check parameters for dict type hints
        if self.check_dict_params and not is_api_boundary:
            self._check_param_type_hints(node)

        self.generic_visit(node)

        # After visiting, check for repeated dict key access
        if self.check_dict_access and not is_api_boundary:
            self._check_dict_key_access_patterns(node)

        self._current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async functions."""
        old_function = self._current_function
        self._current_function = node.name
        self._dict_key_accesses = {}

        is_api_boundary = self._is_api_boundary_context(node.name)

        if self.check_return_dicts and not is_api_boundary:
            self._check_return_type_hint(node)

        if self.check_dict_params and not is_api_boundary:
            self._check_param_type_hints(node)

        self.generic_visit(node)

        if self.check_dict_access and not is_api_boundary:
            self._check_dict_key_access_patterns(node)

        self._current_function = old_function

    def visit_Return(self, node: ast.Return) -> None:
        """Check return statements for dict literals."""
        if not self.check_return_dicts:
            self.generic_visit(node)
            return

        if self._is_api_boundary_context(self._current_function):
            self.generic_visit(node)
            return

        if node.value and isinstance(node.value, ast.Dict):
            keys = self._extract_dict_keys(node.value)
            if len(keys) >= self.min_dict_keys:
                self._add_dict_return_violation(node, keys)

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Track dict key access patterns like data["key"]."""
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            if isinstance(node.value, ast.Name):
                var_name = node.value.id
                key = node.slice.value
                if var_name not in self._dict_key_accesses:
                    self._dict_key_accesses[var_name] = []
                self._dict_key_accesses[var_name].append(key)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check assignments of dict literals."""
        if isinstance(node.value, ast.Dict):
            keys = self._extract_dict_keys(node.value)
            if len(keys) >= self.min_dict_keys:
                # Check if it's being assigned to a variable (not returned)
                if not self._is_api_boundary_context(self._current_function):
                    self._add_dict_literal_violation(node, keys)

        self.generic_visit(node)

    def _is_api_boundary_context(self, name: str | None) -> bool:
        """Check if the current context suggests API boundary."""
        if not self.allow_api_boundaries or not name:
            return False

        name_lower = name.lower()
        for pattern in self.api_boundary_patterns:
            if pattern in name_lower:
                return True

        # Also check class name
        if self._current_class:
            class_lower = self._current_class.lower()
            for pattern in self.api_boundary_patterns:
                if pattern in class_lower:
                    return True

        return False

    def _check_return_type_hint(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Check if return type hint uses Dict[str, Any] or similar."""
        if node.returns and self._is_dict_type_hint(node.returns):
            self._add_dict_type_hint_violation(node, "return")

    def _check_param_type_hints(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Check if parameters use Dict type hints."""
        for arg in node.args.args:
            if arg.annotation and self._is_dict_type_hint(arg.annotation):
                # Skip 'self' and common acceptable patterns
                if arg.arg not in ("self", "cls", "kwargs", "options", "config"):
                    self._add_dict_param_violation(node, arg)

    def _is_dict_type_hint(self, node: ast.expr) -> bool:
        """Check if a type hint represents a dict type."""
        # dict or Dict
        if isinstance(node, ast.Name):
            return node.id in ("dict", "Dict")

        # Dict[str, Any] or dict[str, Any]
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                return node.value.id in ("dict", "Dict")
            if isinstance(node.value, ast.Attribute):
                return node.value.attr in ("Dict",)

        return False

    def _extract_dict_keys(self, node: ast.Dict) -> list[str]:
        """Extract string keys from a dict literal."""
        keys: list[str] = []
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.append(key.value)
        return keys

    def _check_dict_key_access_patterns(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Check for repeated dict key access suggesting structured data."""
        for var_name, keys in self._dict_key_accesses.items():
            unique_keys = set(keys)
            if len(unique_keys) >= self.min_dict_keys:
                self._add_dict_access_violation(node, var_name, list(unique_keys))

    def _add_dict_return_violation(
        self,
        node: ast.Return,
        keys: list[str],
    ) -> None:
        """Add violation for returning a dict literal."""
        self.dict_return_count += 1
        keys_str = ", ".join(f"'{k}'" for k in keys[:5])
        if len(keys) > 5:
            keys_str += ", ..."

        self.violations.append(
            RuleViolation(
                rule_name="dictionary_usage",
                message=(
                    f"Function '{self._current_function}' returns a dict literal with "
                    f"fixed keys [{keys_str}]. Consider using a dataclass or typed object."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="warning",
                suggestion=(
                    "Replace the dictionary with a dataclass, NamedTuple, or Pydantic model. "
                    "This provides type safety, IDE support, and clearer API contracts."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "dict_return",
                    "keys": keys,
                    "function": self._current_function,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "dict_return",
                "line": node.lineno,
                "keys": keys,
            }
        )

    def _add_dict_literal_violation(
        self,
        node: ast.Assign,
        keys: list[str],
    ) -> None:
        """Add violation for assigning a dict literal with fixed keys."""
        self.dict_literal_count += 1
        keys_str = ", ".join(f"'{k}'" for k in keys[:5])
        if len(keys) > 5:
            keys_str += ", ..."

        # Get the variable name if possible
        var_name = "<variable>"
        if node.targets and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id

        self.violations.append(
            RuleViolation(
                rule_name="dictionary_usage",
                message=(
                    f"Dict literal assigned to '{var_name}' with fixed keys [{keys_str}]. "
                    f"Consider using a dataclass or typed object instead."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "If this dictionary represents structured data with known keys, "
                    "consider using a dataclass or NamedTuple for better type safety."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "dict_literal",
                    "keys": keys,
                    "variable": var_name,
                    "function": self._current_function,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "dict_literal",
                "line": node.lineno,
                "keys": keys,
            }
        )

    def _add_dict_type_hint_violation(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        context: str,
    ) -> None:
        """Add violation for using Dict type hint."""
        self.dict_param_count += 1

        self.violations.append(
            RuleViolation(
                rule_name="dictionary_usage",
                message=(
                    f"Function '{node.name}' uses Dict type hint for {context}. "
                    f"Consider using a typed object instead."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "Using Dict[str, Any] loses type information. Consider defining "
                    "a dataclass, TypedDict, or Pydantic model for structured data."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "dict_type_hint",
                    "context": context,
                    "function": node.name,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "dict_type_hint",
                "line": node.lineno,
                "context": context,
            }
        )

    def _add_dict_param_violation(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        arg: ast.arg,
    ) -> None:
        """Add violation for dict parameter type hint."""
        self.dict_param_count += 1

        self.violations.append(
            RuleViolation(
                rule_name="dictionary_usage",
                message=(
                    f"Parameter '{arg.arg}' in function '{node.name}' uses Dict type hint. "
                    f"Consider using a typed object for structured data."
                ),
                file_path=self.file_path,
                line=arg.lineno,
                column=arg.col_offset,
                severity="warning",
                suggestion=(
                    f"Instead of passing a dict, define a dataclass or Pydantic model "
                    f"that represents the expected structure of '{arg.arg}'."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "dict_param",
                    "parameter": arg.arg,
                    "function": node.name,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "dict_param",
                "line": arg.lineno,
                "parameter": arg.arg,
            }
        )

    def _add_dict_access_violation(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        var_name: str,
        keys: list[str],
    ) -> None:
        """Add violation for repeated dict key access."""
        self.dict_access_count += 1
        keys_str = ", ".join(f"'{k}'" for k in keys[:5])
        if len(keys) > 5:
            keys_str += ", ..."

        self.violations.append(
            RuleViolation(
                rule_name="dictionary_usage",
                message=(
                    f"Variable '{var_name}' accessed with multiple string keys [{keys_str}] "
                    f"in function '{node.name}'. This suggests structured data."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    f"If '{var_name}' has a known structure, consider converting it to "
                    f"a dataclass or typed object for better type safety and IDE support."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "dict_access",
                    "variable": var_name,
                    "keys": keys,
                    "function": node.name,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "dict_access",
                "line": node.lineno,
                "variable": var_name,
                "keys": keys,
            }
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
