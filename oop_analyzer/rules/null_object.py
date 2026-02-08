"""
Null Object Rule - None Usage Detection.

This rule detects usage of None that could be replaced by the Null Object pattern.
The Null Object pattern provides a default behavior instead of null checks.
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class NullObjectRule(BaseRule):
    """
    Detects None usage that could be replaced by Null Object pattern.

    Patterns detected:
    - `if x is None:` / `if x is not None:`
    - `if x == None:` / `if x != None:`
    - `x if x is not None else default`
    - `return None`
    - `x = None` as default parameter
    - Optional type hints suggesting None handling
    - Optional[T] / T | None type hints in parameters (evil optionals)
    """

    name = "null_object"
    description = "Detect None usage replaceable by Null Object pattern"
    severity = "info"

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.check_return_none = self.options.get("check_return_none", True)
        self.check_none_comparisons = self.options.get("check_none_comparisons", True)
        self.check_optional_params = self.options.get("check_optional_params", True)
        self.check_optional_type_hints = self.options.get("check_optional_type_hints", True)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for None usage patterns."""
        visitor = NoneUsageVisitor(
            file_path=file_path,
            source=source,
            check_return_none=self.check_return_none,
            check_none_comparisons=self.check_none_comparisons,
            check_optional_params=self.check_optional_params,
            check_optional_type_hints=self.check_optional_type_hints,
        )
        visitor.visit(tree)

        return RuleResult(
            rule_name=self.name,
            violations=visitor.violations,
            summary={
                "total_none_checks": visitor.none_check_count,
                "return_none_count": visitor.return_none_count,
                "optional_param_count": visitor.optional_param_count,
                "optional_type_hint_count": visitor.optional_type_hint_count,
            },
            metadata={
                "none_patterns": visitor.none_patterns,
            },
        )


class NoneUsageVisitor(ast.NodeVisitor):
    """AST visitor that detects None usage patterns."""

    def __init__(
        self,
        file_path: str,
        source: str,
        check_return_none: bool = True,
        check_none_comparisons: bool = True,
        check_optional_params: bool = True,
        check_optional_type_hints: bool = True,
    ):
        self.file_path = file_path
        self.source = source
        self.check_return_none = check_return_none
        self.check_none_comparisons = check_none_comparisons
        self.check_optional_params = check_optional_params
        self.check_optional_type_hints = check_optional_type_hints

        self.violations: list[RuleViolation] = []
        self.none_patterns: list[dict[str, Any]] = []
        self.none_check_count = 0
        self.return_none_count = 0
        self.optional_param_count = 0
        self.optional_type_hint_count = 0

        self._current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function context and check parameters."""
        old_function = self._current_function
        self._current_function = node.name

        if self.check_optional_params:
            self._check_optional_parameters(node)

        if self.check_optional_type_hints:
            self._check_optional_type_hints(node)

        self.generic_visit(node)
        self._current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async functions the same as regular functions."""
        old_function = self._current_function
        self._current_function = node.name

        if self.check_optional_params:
            self._check_optional_parameters(node)

        if self.check_optional_type_hints:
            self._check_optional_type_hints(node)

        self.generic_visit(node)
        self._current_function = old_function

    def visit_Compare(self, node: ast.Compare) -> None:
        """Detect `x is None` and `x == None` comparisons."""
        if not self.check_none_comparisons:
            self.generic_visit(node)
            return

        for i, (op, comparator) in enumerate(zip(node.ops, node.comparators, strict=False)):
            if self._is_none(comparator) or (i == 0 and self._is_none(node.left)):
                self.none_check_count += 1

                op_name = type(op).__name__
                if op_name in ("Is", "IsNot", "Eq", "NotEq"):
                    self._add_none_check_violation(node, op_name)

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Detect if statements that check for None."""
        if self.check_none_comparisons and self._is_none_check(node.test):
            self.none_check_count += 1
            self._add_if_none_violation(node)

        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        """Detect ternary expressions with None checks."""
        if self.check_none_comparisons and self._is_none_check(node.test):
            self.none_check_count += 1
            self._add_ternary_none_violation(node)

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Detect `return None` statements."""
        if not self.check_return_none:
            self.generic_visit(node)
            return

        if node.value is not None and self._is_none(node.value):
            self.return_none_count += 1
            self._add_return_none_violation(node)

        self.generic_visit(node)

    def _is_none(self, node: ast.expr) -> bool:
        """Check if a node represents None."""
        return isinstance(node, ast.Constant) and node.value is None

    def _is_none_check(self, node: ast.expr) -> bool:
        """Check if an expression is a None comparison."""
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if self._is_none(comparator):
                    return True
            if self._is_none(node.left):
                return True

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self._is_none_check(node.operand)

        return False

    def _check_optional_parameters(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Check for parameters with None as default."""
        defaults = node.args.defaults
        args = node.args.args

        # Match defaults to args (defaults are right-aligned)
        num_defaults = len(defaults)
        num_args = len(args)

        for i, default in enumerate(defaults):
            if self._is_none(default):
                arg_index = num_args - num_defaults + i
                if arg_index >= 0 and arg_index < len(args):
                    arg = args[arg_index]
                    self.optional_param_count += 1
                    self._add_optional_param_violation(node, arg)

        # Also check kw_defaults
        for i, kw_default in enumerate(node.args.kw_defaults):
            if kw_default is not None and self._is_none(kw_default):
                if i < len(node.args.kwonlyargs):
                    arg = node.args.kwonlyargs[i]
                    self.optional_param_count += 1
                    self._add_optional_param_violation(node, arg)

    def _check_optional_type_hints(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Check for Optional[T] or T | None type hints in parameters."""
        for arg in node.args.args + node.args.kwonlyargs:
            if arg.annotation and self._is_optional_type_hint(arg.annotation):
                # Skip 'self' and 'cls'
                if arg.arg in ("self", "cls"):
                    continue
                self.optional_type_hint_count += 1
                self._add_optional_type_hint_violation(node, arg)

    def _is_optional_type_hint(self, node: ast.expr) -> bool:
        """Check if a type annotation is Optional[T] or T | None."""
        # Check for Optional[T] - typing.Optional or just Optional
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "Optional":
                return True
            if isinstance(node.value, ast.Attribute) and node.value.attr == "Optional":
                return True

        # Check for T | None (Python 3.10+ union syntax)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Check if either side is None
            if self._is_none_type(node.left) or self._is_none_type(node.right):
                return True

        # Check for Union[T, None]
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "Union":
                if isinstance(node.slice, ast.Tuple):
                    for elt in node.slice.elts:
                        if self._is_none_type(elt):
                            return True
            if isinstance(node.value, ast.Attribute) and node.value.attr == "Union":
                if isinstance(node.slice, ast.Tuple):
                    for elt in node.slice.elts:
                        if self._is_none_type(elt):
                            return True

        return False

    def _is_none_type(self, node: ast.expr) -> bool:
        """Check if a node represents the None type."""
        # None as a constant
        if isinstance(node, ast.Constant) and node.value is None:
            return True
        # None as a name (in type context)
        return bool(isinstance(node, ast.Name) and node.id == "None")

    def _add_optional_type_hint_violation(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        arg: ast.arg,
    ) -> None:
        """Add a violation for Optional type hint in parameter."""
        self.violations.append(
            RuleViolation(
                rule_name="null_object",
                message=(
                    f"Parameter '{arg.arg}' in function '{func_node.name}' "
                    f"has Optional type hint. Optionals can introduce nulls."
                ),
                file_path=self.file_path,
                line=arg.lineno,
                column=arg.col_offset,
                severity="warning",
                suggestion=(
                    f"Consider whether '{arg.arg}' truly needs to be optional. "
                    f"If a default behavior is needed, use a Null Object instead of None."
                ),
                code_snippet=self._get_source_line(func_node.lineno),
                metadata={
                    "pattern": "optional_type_hint",
                    "function": func_node.name,
                    "parameter": arg.arg,
                },
            )
        )
        self.none_patterns.append(
            {
                "type": "optional_type_hint",
                "line": arg.lineno,
                "function": func_node.name,
                "parameter": arg.arg,
            }
        )

    def _add_none_check_violation(self, node: ast.Compare, op_name: str) -> None:
        """Add a violation for None comparison."""
        self.violations.append(
            RuleViolation(
                rule_name="null_object",
                message=(
                    "None comparison detected. Consider using Null Object pattern "
                    "to avoid explicit None checks."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "Instead of checking for None, consider using a Null Object "
                    "that provides default/no-op behavior."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "none_comparison",
                    "operator": op_name,
                    "function": self._current_function,
                },
            )
        )
        self.none_patterns.append(
            {
                "type": "comparison",
                "line": node.lineno,
                "operator": op_name,
            }
        )

    def _add_if_none_violation(self, node: ast.If) -> None:
        """Add a violation for if-None check."""
        self.violations.append(
            RuleViolation(
                rule_name="null_object",
                message=(
                    "If statement checks for None. This is a candidate for Null Object pattern."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "Consider replacing the None check with a Null Object that "
                    "provides default behavior, eliminating the need for this conditional."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "if_none_check",
                    "function": self._current_function,
                },
            )
        )
        self.none_patterns.append(
            {
                "type": "if_check",
                "line": node.lineno,
            }
        )

    def _add_ternary_none_violation(self, node: ast.IfExp) -> None:
        """Add a violation for ternary None check."""
        self.violations.append(
            RuleViolation(
                rule_name="null_object",
                message=("Ternary expression checks for None. Consider Null Object pattern."),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "The ternary `x if x is not None else default` pattern can often "
                    "be replaced by ensuring x is never None (using Null Object)."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "ternary_none_check",
                    "function": self._current_function,
                },
            )
        )
        self.none_patterns.append(
            {
                "type": "ternary",
                "line": node.lineno,
            }
        )

    def _add_return_none_violation(self, node: ast.Return) -> None:
        """Add a violation for return None."""
        self.violations.append(
            RuleViolation(
                rule_name="null_object",
                message=(
                    f"Explicit 'return None' in function '{self._current_function}'. "
                    f"Consider returning a Null Object instead."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "Instead of returning None, consider returning a Null Object "
                    "that implements the expected interface with no-op behavior."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "return_none",
                    "function": self._current_function,
                },
            )
        )
        self.none_patterns.append(
            {
                "type": "return_none",
                "line": node.lineno,
                "function": self._current_function,
            }
        )

    def _add_optional_param_violation(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        arg: ast.arg,
    ) -> None:
        """Add a violation for optional parameter with None default."""
        self.violations.append(
            RuleViolation(
                rule_name="null_object",
                message=(
                    f"Parameter '{arg.arg}' in function '{func_node.name}' "
                    f"has None as default. Consider using Null Object."
                ),
                file_path=self.file_path,
                line=arg.lineno,
                column=arg.col_offset,
                severity="info",
                suggestion=(
                    f"Instead of `{arg.arg}=None`, consider using a Null Object "
                    f"as the default that provides no-op behavior."
                ),
                code_snippet=self._get_source_line(func_node.lineno),
                metadata={
                    "pattern": "optional_param",
                    "function": func_node.name,
                    "parameter": arg.arg,
                },
            )
        )
        self.none_patterns.append(
            {
                "type": "optional_param",
                "line": arg.lineno,
                "function": func_node.name,
                "parameter": arg.arg,
            }
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
