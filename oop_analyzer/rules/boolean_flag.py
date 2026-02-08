"""
Boolean Flag Rule - Detect behavior branching on flag parameters.

This rule detects boolean flag parameters in methods and constructors
that cause behavior branching. This is a code smell because:
- It violates the Single Responsibility Principle
- It makes the code harder to understand and test
- It often indicates that the method should be split into two methods

References:
- https://refactoring.guru/smells/boolean-parameters
- Clean Code by Robert C. Martin
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class BooleanFlagRule(BaseRule):
    """
    Detects boolean flag parameters that cause behavior branching.

    Patterns detected:
    - Methods with boolean parameters used in if statements
    - Constructors with boolean flags that determine behavior
    - Functions with bool type hints used for branching
    """

    name = "boolean_flag"
    description = "Detect boolean flag parameters causing behavior branching"
    severity = "warning"

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.check_constructors = self.options.get("check_constructors", True)
        self.check_methods = self.options.get("check_methods", True)
        self.check_functions = self.options.get("check_functions", True)
        self.min_flag_usages = self.options.get("min_flag_usages", 1)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for boolean flag patterns."""
        visitor = BooleanFlagVisitor(
            file_path=file_path,
            source=source,
            check_constructors=self.check_constructors,
            check_methods=self.check_methods,
            check_functions=self.check_functions,
            min_flag_usages=self.min_flag_usages,
        )
        visitor.visit(tree)

        return RuleResult(
            rule_name=self.name,
            violations=visitor.violations,
            summary={
                "total_boolean_flags": len(visitor.violations),
                "constructor_flags": visitor.constructor_flag_count,
                "method_flags": visitor.method_flag_count,
                "function_flags": visitor.function_flag_count,
            },
            metadata={
                "flag_patterns": visitor.flag_patterns,
            },
        )


class BooleanFlagVisitor(ast.NodeVisitor):
    """AST visitor that detects boolean flag parameters."""

    def __init__(
        self,
        file_path: str,
        source: str,
        check_constructors: bool = True,
        check_methods: bool = True,
        check_functions: bool = True,
        min_flag_usages: int = 1,
    ):
        self.file_path = file_path
        self.source = source
        self.check_constructors = check_constructors
        self.check_methods = check_methods
        self.check_functions = check_functions
        self.min_flag_usages = min_flag_usages

        self.violations: list[RuleViolation] = []
        self.flag_patterns: list[dict[str, Any]] = []
        self.constructor_flag_count = 0
        self.method_flag_count = 0
        self.function_flag_count = 0

        self._current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context."""
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function/method for boolean flag parameters."""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function/method for boolean flag parameters."""
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Check a function for boolean flag parameters."""
        is_constructor = node.name == "__init__"
        is_method = self._current_class is not None
        is_function = self._current_class is None

        # Check if we should analyze this type
        if is_constructor and not self.check_constructors:
            return
        if is_method and not is_constructor and not self.check_methods:
            return
        if is_function and not self.check_functions:
            return

        # Find boolean parameters
        bool_params = self._find_boolean_params(node)

        if not bool_params:
            return

        # Check if boolean params are used in conditionals
        for param_name in bool_params:
            usages = self._count_conditional_usages(node, param_name)
            if usages >= self.min_flag_usages:
                self._add_violation(node, param_name, usages, is_constructor, is_method)

    def _find_boolean_params(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[str]:
        """Find parameters that are boolean flags."""
        bool_params: list[str] = []

        all_args = node.args.args + node.args.kwonlyargs

        for arg in all_args:
            # Skip self/cls
            if arg.arg in ("self", "cls"):
                continue

            # Check type hint for bool
            if arg.annotation and self._is_bool_type(arg.annotation):
                bool_params.append(arg.arg)
                continue

            # Check if default is a boolean
            # Match defaults to args (defaults are right-aligned)
            default = self._get_default_for_arg(node, arg)
            if default is not None and isinstance(default, ast.Constant):
                if isinstance(default.value, bool):
                    bool_params.append(arg.arg)
                    continue

            # Check naming patterns suggesting boolean
            if self._is_boolean_name(arg.arg):
                bool_params.append(arg.arg)

        return bool_params

    def _is_bool_type(self, node: ast.expr) -> bool:
        """Check if a type annotation is bool."""
        return bool(isinstance(node, ast.Name) and node.id == "bool")

    def _is_boolean_name(self, name: str) -> bool:
        """Check if a parameter name suggests a boolean."""
        boolean_prefixes = (
            "is_",
            "has_",
            "can_",
            "should_",
            "will_",
            "did_",
            "enable_",
            "disable_",
            "use_",
            "allow_",
            "include_",
            "exclude_",
            "force_",
            "skip_",
            "ignore_",
            "check_",
        )
        boolean_names = (
            "enabled",
            "disabled",
            "active",
            "inactive",
            "visible",
            "hidden",
            "readonly",
            "required",
            "optional",
            "recursive",
            "verbose",
            "quiet",
            "debug",
            "dry_run",
            "force",
        )

        name_lower = name.lower()

        if any(name_lower.startswith(prefix) for prefix in boolean_prefixes):
            return True
        return name_lower in boolean_names

    def _get_default_for_arg(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        arg: ast.arg,
    ) -> ast.expr | None:
        """Get the default value for an argument if it exists."""
        # Check regular args
        args = node.args.args
        defaults = node.args.defaults
        num_defaults = len(defaults)
        num_args = len(args)

        try:
            arg_index = args.index(arg)
            default_index = arg_index - (num_args - num_defaults)
            if default_index >= 0:
                return defaults[default_index]
        except ValueError:
            pass

        # Check kwonly args
        kwonlyargs = node.args.kwonlyargs
        kw_defaults = node.args.kw_defaults

        try:
            kw_index = kwonlyargs.index(arg)
            if kw_index < len(kw_defaults) and kw_defaults[kw_index] is not None:
                return kw_defaults[kw_index]
        except ValueError:
            pass

        return None

    def _count_conditional_usages(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        param_name: str,
    ) -> int:
        """Count how many times a parameter is used in conditionals."""
        counter = ConditionalUsageCounter(param_name)
        counter.visit(node)
        return counter.count

    def _add_violation(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        param_name: str,
        usages: int,
        is_constructor: bool,
        is_method: bool,
    ) -> None:
        """Add a violation for boolean flag parameter."""
        if is_constructor:
            self.constructor_flag_count += 1
            context = f"Constructor of '{self._current_class}'"
            suggestion = (
                "Consider splitting into separate classes or using a factory method "
                "instead of a boolean flag in the constructor."
            )
        elif is_method:
            self.method_flag_count += 1
            context = f"Method '{node.name}' in class '{self._current_class}'"
            suggestion = (
                f"Consider splitting '{node.name}' into two methods with descriptive names "
                f"instead of using a boolean flag to control behavior."
            )
        else:
            self.function_flag_count += 1
            context = f"Function '{node.name}'"
            suggestion = (
                f"Consider splitting '{node.name}' into two functions with descriptive names "
                f"instead of using a boolean flag to control behavior."
            )

        self.violations.append(
            RuleViolation(
                rule_name="boolean_flag",
                message=(
                    f"{context} has boolean flag parameter '{param_name}' "
                    f"used in {usages} conditional(s). This causes behavior branching."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="warning",
                suggestion=suggestion,
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "parameter": param_name,
                    "function": node.name,
                    "class": self._current_class,
                    "is_constructor": is_constructor,
                    "conditional_usages": usages,
                },
            )
        )
        self.flag_patterns.append(
            {
                "type": "boolean_flag",
                "line": node.lineno,
                "parameter": param_name,
                "function": node.name,
                "class": self._current_class,
            }
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""


class ConditionalUsageCounter(ast.NodeVisitor):
    """Counts how many times a variable is used in conditionals."""

    def __init__(self, var_name: str):
        self.var_name = var_name
        self.count = 0

    def visit_If(self, node: ast.If) -> None:
        """Check if the variable is used in an if condition."""
        if self._uses_variable(node.test):
            self.count += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        """Check if the variable is used in a ternary expression."""
        if self._uses_variable(node.test):
            self.count += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Check if the variable is used in a while condition."""
        if self._uses_variable(node.test):
            self.count += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Check if the variable is used in a boolean operation."""
        for value in node.values:
            if self._uses_variable(value):
                self.count += 1
                break
        self.generic_visit(node)

    def _uses_variable(self, node: ast.expr) -> bool:
        """Check if an expression uses the target variable."""
        if isinstance(node, ast.Name) and node.id == self.var_name:
            return True

        if isinstance(node, ast.UnaryOp):
            return self._uses_variable(node.operand)

        if isinstance(node, ast.BoolOp):
            return any(self._uses_variable(v) for v in node.values)

        if isinstance(node, ast.Compare):
            if self._uses_variable(node.left):
                return True
            return any(self._uses_variable(c) for c in node.comparators)

        return False
