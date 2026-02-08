"""
Polymorphism Rule - If Blocks Replaceable by Polymorphism.

This rule detects if/elif chains and switch-like patterns that could
be replaced by polymorphism (strategy pattern, state pattern, etc.).
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class PolymorphismRule(BaseRule):
    """
    Detects if blocks that could be replaced by polymorphism.

    Patterns detected:
    - Long if/elif chains checking the same variable
    - Type checking with isinstance() in conditionals
    - Checking object type/kind attributes
    - Switch-like patterns (match statements in Python 3.10+)
    """

    name = "polymorphism"
    description = "Find if blocks replaceable by polymorphism"
    severity = "warning"

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.min_branches = self.options.get("min_branches", 3)
        self.check_isinstance = self.options.get("check_isinstance", True)
        self.check_type_attributes = self.options.get("check_type_attributes", True)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for polymorphism opportunities."""
        visitor = PolymorphismVisitor(
            file_path=file_path,
            source=source,
            min_branches=self.min_branches,
            check_isinstance=self.check_isinstance,
            check_type_attributes=self.check_type_attributes,
        )
        visitor.visit(tree)

        return RuleResult(
            rule_name=self.name,
            violations=visitor.violations,
            summary={
                "total_opportunities": len(visitor.violations),
                "isinstance_checks": visitor.isinstance_count,
                "type_attribute_checks": visitor.type_attr_count,
                "long_if_chains": visitor.long_chain_count,
            },
            metadata={
                "patterns": visitor.patterns,
            },
        )


class PolymorphismVisitor(ast.NodeVisitor):
    """AST visitor that detects polymorphism opportunities."""

    TYPE_ATTRIBUTES = {"type", "kind", "category", "variant", "mode", "status"}

    def __init__(
        self,
        file_path: str,
        source: str,
        min_branches: int = 3,
        check_isinstance: bool = True,
        check_type_attributes: bool = True,
    ):
        self.file_path = file_path
        self.source = source
        self.min_branches = min_branches
        self.check_isinstance = check_isinstance
        self.check_type_attributes = check_type_attributes

        self.violations: list[RuleViolation] = []
        self.patterns: list[dict[str, Any]] = []
        self.isinstance_count = 0
        self.type_attr_count = 0
        self.long_chain_count = 0

        self._current_function: str | None = None
        self._current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context."""
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function context."""
        old_function = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async functions."""
        old_function = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = old_function

    def visit_If(self, node: ast.If) -> None:
        """Analyze if statements for polymorphism opportunities."""
        # Count branches in this if/elif chain
        branches = self._count_branches(node)

        if branches >= self.min_branches:
            # Check what kind of pattern this is
            pattern_info = self._analyze_if_pattern(node)

            if pattern_info:
                self._add_violation(node, branches, pattern_info)

        # Also check for isinstance in any if
        if self.check_isinstance:
            self._check_isinstance_pattern(node)

        # Check for type attribute comparisons
        if self.check_type_attributes:
            self._check_type_attribute_pattern(node)

        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Analyze match statements (Python 3.10+)."""
        num_cases = len(node.cases)

        if num_cases >= self.min_branches:
            self._add_match_violation(node, num_cases)

        self.generic_visit(node)

    def _count_branches(self, node: ast.If) -> int:
        """Count the number of branches in an if/elif chain."""
        count = 1  # The if itself

        # Count elif branches
        current = node
        while current.orelse:
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                count += 1
                current = current.orelse[0]
            else:
                # Has an else clause
                count += 1
                break

        return count

    def _analyze_if_pattern(self, node: ast.If) -> dict[str, Any] | None:
        """Analyze what variable/pattern the if chain is checking."""
        checked_vars: list[str] = []

        current: ast.If | None = node
        while current:
            var = self._get_checked_variable(current.test)
            if var:
                checked_vars.append(var)

            if current.orelse and len(current.orelse) == 1:
                if isinstance(current.orelse[0], ast.If):
                    current = current.orelse[0]
                else:
                    break
            else:
                break

        if not checked_vars:
            return None

        # Check if all branches check the same variable
        if len(set(checked_vars)) == 1:
            return {
                "type": "same_variable",
                "variable": checked_vars[0],
            }

        # Check if most branches check the same variable
        from collections import Counter

        counter = Counter(checked_vars)
        most_common = counter.most_common(1)[0]
        if most_common[1] >= len(checked_vars) * 0.7:
            return {
                "type": "mostly_same_variable",
                "variable": most_common[0],
                "consistency": most_common[1] / len(checked_vars),
            }

        return None

    def _get_checked_variable(self, test: ast.expr) -> str | None:
        """Extract the variable being checked in a condition."""
        if isinstance(test, ast.Compare):
            left = test.left
            if isinstance(left, ast.Attribute):
                return self._get_attribute_name(left)
            elif isinstance(left, ast.Name):
                return left.id

        if isinstance(test, ast.Call):
            if isinstance(test.func, ast.Name) and test.func.id == "isinstance":
                if test.args and isinstance(test.args[0], ast.Name):
                    return test.args[0].id

        if isinstance(test, ast.BoolOp):
            # Check first value
            if test.values:
                return self._get_checked_variable(test.values[0])

        return None

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full attribute name (e.g., 'obj.type')."""
        parts: list[str] = [node.attr]
        current = node.value

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        parts.reverse()
        return ".".join(parts)

    def _check_isinstance_pattern(self, node: ast.If) -> None:
        """Check for isinstance() usage in conditionals."""
        if self._contains_isinstance(node.test):
            self.isinstance_count += 1
            self.violations.append(
                RuleViolation(
                    rule_name="polymorphism",
                    message=(
                        "isinstance() check detected. This often indicates a need for polymorphism."
                    ),
                    file_path=self.file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    severity="warning",
                    suggestion=(
                        "Instead of checking types with isinstance(), consider "
                        "using polymorphism. Define a common interface/base class "
                        "and let each type implement its own behavior."
                    ),
                    code_snippet=self._get_source_line(node.lineno),
                    metadata={
                        "pattern": "isinstance_check",
                        "function": self._current_function,
                        "class": self._current_class,
                    },
                )
            )
            self.patterns.append(
                {
                    "type": "isinstance",
                    "line": node.lineno,
                }
            )

    def _contains_isinstance(self, node: ast.expr) -> bool:
        """Check if an expression contains isinstance()."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                return True

        if isinstance(node, ast.BoolOp):
            return any(self._contains_isinstance(v) for v in node.values)

        if isinstance(node, ast.UnaryOp):
            return self._contains_isinstance(node.operand)

        return False

    def _check_type_attribute_pattern(self, node: ast.If) -> None:
        """Check for type/kind attribute comparisons."""
        attr_name = self._get_type_attribute_check(node.test)
        if attr_name:
            self.type_attr_count += 1
            self.violations.append(
                RuleViolation(
                    rule_name="polymorphism",
                    message=(
                        f"Checking '{attr_name}' attribute suggests type-based branching. "
                        f"Consider using polymorphism instead."
                    ),
                    file_path=self.file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    severity="warning",
                    suggestion=(
                        f"Instead of checking the '{attr_name.split('.')[-1]}' attribute, "
                        f"consider using polymorphism. Create subclasses that implement "
                        f"the behavior directly."
                    ),
                    code_snippet=self._get_source_line(node.lineno),
                    metadata={
                        "pattern": "type_attribute",
                        "attribute": attr_name,
                        "function": self._current_function,
                        "class": self._current_class,
                    },
                )
            )
            self.patterns.append(
                {
                    "type": "type_attribute",
                    "attribute": attr_name,
                    "line": node.lineno,
                }
            )

    def _get_type_attribute_check(self, node: ast.expr) -> str | None:
        """Check if comparing a type-like attribute."""
        if isinstance(node, ast.Compare):
            left = node.left
            if isinstance(left, ast.Attribute):
                if left.attr.lower() in self.TYPE_ATTRIBUTES:
                    return self._get_attribute_name(left)

        if isinstance(node, ast.BoolOp):
            for value in node.values:
                result = self._get_type_attribute_check(value)
                if result:
                    return result

        return None

    def _add_violation(
        self,
        node: ast.If,
        branches: int,
        pattern_info: dict[str, Any],
    ) -> None:
        """Add a violation for a long if/elif chain."""
        self.long_chain_count += 1

        variable = pattern_info.get("variable", "unknown")

        self.violations.append(
            RuleViolation(
                rule_name="polymorphism",
                message=(
                    f"Long if/elif chain with {branches} branches checking '{variable}'. "
                    f"Consider replacing with polymorphism."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="warning",
                suggestion=(
                    f"This if/elif chain could be replaced with polymorphism. "
                    f"Consider using Strategy pattern, State pattern, or simple "
                    f"method dispatch based on the value of '{variable}'."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "long_if_chain",
                    "branches": branches,
                    "checked_variable": variable,
                    "function": self._current_function,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "long_if_chain",
                "branches": branches,
                "variable": variable,
                "line": node.lineno,
            }
        )

    def _add_match_violation(self, node: ast.Match, num_cases: int) -> None:
        """Add a violation for match statement."""
        self.violations.append(
            RuleViolation(
                rule_name="polymorphism",
                message=(
                    f"Match statement with {num_cases} cases. "
                    f"Consider if polymorphism would be more appropriate."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="info",
                suggestion=(
                    "While match statements are useful, many cases might indicate "
                    "an opportunity for polymorphism where each case becomes a class."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "match_statement",
                    "cases": num_cases,
                    "function": self._current_function,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "match_statement",
                "cases": num_cases,
                "line": node.lineno,
            }
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
