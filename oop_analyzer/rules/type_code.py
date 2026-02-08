"""
Type Code Conditionals Rule.

This rule detects conditionals that check type codes, constants, or enums
which could be replaced by polymorphism using State/Strategy patterns
or subclasses.

References:
- https://refactoring.guru/replace-type-code-with-state-strategy
- https://refactoring.guru/replace-type-code-with-class
- https://refactoring.guru/replace-type-code-with-subclasses
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class TypeCodeRule(BaseRule):
    """
    Detects type code conditionals that could use polymorphism.

    Patterns detected:
    - if self.type == CONSTANT: ... elif self.type == OTHER_CONSTANT: ...
    - if obj.kind == SomeEnum.VALUE: ...
    - if status == STATUS_PENDING: ... elif status == STATUS_ACTIVE: ...
    - Comparisons against ALL_CAPS constants in conditionals
    """

    name = "type_code"
    description = "Detect type code conditionals replaceable by polymorphism"
    severity = "warning"

    # Common type code attribute names
    TYPE_CODE_ATTRIBUTES = {
        "type",
        "kind",
        "category",
        "status",
        "state",
        "mode",
        "variant",
        "style",
        "format",
        "action",
        "operation",
    }

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.min_branches = self.options.get("min_branches", 2)
        self.check_constants = self.options.get("check_constants", True)
        self.check_enums = self.options.get("check_enums", True)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for type code conditionals."""
        visitor = TypeCodeVisitor(
            file_path=file_path,
            source=source,
            min_branches=self.min_branches,
            check_constants=self.check_constants,
            check_enums=self.check_enums,
            type_code_attributes=self.TYPE_CODE_ATTRIBUTES,
        )
        visitor.visit(tree)

        return RuleResult(
            rule_name=self.name,
            violations=visitor.violations,
            summary={
                "total_type_code_conditionals": len(visitor.violations),
                "constant_comparisons": visitor.constant_comparison_count,
                "enum_comparisons": visitor.enum_comparison_count,
                "type_attribute_checks": visitor.type_attr_count,
            },
            metadata={
                "patterns": visitor.patterns,
            },
        )


class TypeCodeVisitor(ast.NodeVisitor):
    """AST visitor that detects type code conditional patterns."""

    def __init__(
        self,
        file_path: str,
        source: str,
        min_branches: int = 2,
        check_constants: bool = True,
        check_enums: bool = True,
        type_code_attributes: set[str] | None = None,
    ):
        self.file_path = file_path
        self.source = source
        self.min_branches = min_branches
        self.check_constants = check_constants
        self.check_enums = check_enums
        self.type_code_attributes = type_code_attributes or set()

        self.violations: list[RuleViolation] = []
        self.patterns: list[dict[str, Any]] = []
        self.constant_comparison_count = 0
        self.enum_comparison_count = 0
        self.type_attr_count = 0

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
        """Analyze if statements for type code patterns."""
        # Analyze the entire if/elif chain
        chain_info = self._analyze_if_chain(node)

        if chain_info and chain_info["is_type_code_pattern"]:
            self._add_violation(node, chain_info)

        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Analyze match statements for type code patterns."""
        # Check if matching against a type-like attribute
        subject = node.subject
        if self._is_type_code_subject(subject):
            num_cases = len(node.cases)
            if num_cases >= self.min_branches:
                self._add_match_violation(node, subject, num_cases)

        self.generic_visit(node)

    def _analyze_if_chain(self, node: ast.If) -> dict[str, Any] | None:
        """Analyze an if/elif chain for type code patterns."""
        branches: list[dict[str, Any]] = []
        current: ast.If | None = node

        while current:
            branch_info = self._analyze_condition(current.test)
            if branch_info:
                branches.append(branch_info)

            # Move to elif
            if current.orelse and len(current.orelse) == 1:
                if isinstance(current.orelse[0], ast.If):
                    current = current.orelse[0]
                else:
                    # else clause
                    break
            else:
                break

        if len(branches) < self.min_branches:
            return None

        # Check if all branches check the same type code pattern
        type_code_branches = [b for b in branches if b.get("is_type_code")]

        if len(type_code_branches) >= self.min_branches:
            # Check if they're checking the same attribute
            checked_attrs = [b.get("checked_attribute") for b in type_code_branches]
            if checked_attrs and len(set(checked_attrs)) == 1:
                return {
                    "is_type_code_pattern": True,
                    "checked_attribute": checked_attrs[0],
                    "branch_count": len(branches),
                    "type_code_branches": len(type_code_branches),
                    "comparison_values": [b.get("compared_to") for b in type_code_branches],
                    "pattern_type": type_code_branches[0].get("pattern_type"),
                }

        return None

    def _analyze_condition(self, test: ast.expr) -> dict[str, Any] | None:
        """Analyze a single condition for type code patterns."""
        if isinstance(test, ast.Compare):
            return self._analyze_compare(test)

        if isinstance(test, ast.BoolOp):
            # Check first operand
            if test.values:
                return self._analyze_condition(test.values[0])

        return None

    def _analyze_compare(self, node: ast.Compare) -> dict[str, Any] | None:
        """Analyze a comparison for type code patterns."""
        left = node.left

        # Check if comparing a type-like attribute
        if isinstance(left, ast.Attribute):
            attr_name = left.attr.lower()
            if attr_name in self.type_code_attributes:
                self.type_attr_count += 1
                compared_to = self._get_comparison_value(node)
                pattern_type = self._classify_comparison_value(node)

                return {
                    "is_type_code": True,
                    "checked_attribute": self._get_full_attribute(left),
                    "compared_to": compared_to,
                    "pattern_type": pattern_type,
                }

        # Check if comparing against constants (ALL_CAPS)
        if self.check_constants:
            for comparator in node.comparators:
                if self._is_constant(comparator):
                    self.constant_comparison_count += 1
                    return {
                        "is_type_code": True,
                        "checked_attribute": self._get_left_name(left),
                        "compared_to": self._get_constant_name(comparator),
                        "pattern_type": "constant",
                    }

        # Check if comparing against enum values
        if self.check_enums:
            for comparator in node.comparators:
                if self._is_enum_value(comparator):
                    self.enum_comparison_count += 1
                    return {
                        "is_type_code": True,
                        "checked_attribute": self._get_left_name(left),
                        "compared_to": self._get_enum_name(comparator),
                        "pattern_type": "enum",
                    }

        return None

    def _is_type_code_subject(self, node: ast.expr) -> bool:
        """Check if a match subject is a type code attribute."""
        if isinstance(node, ast.Attribute):
            return node.attr.lower() in self.type_code_attributes
        return False

    def _is_constant(self, node: ast.expr) -> bool:
        """Check if a node is an ALL_CAPS constant."""
        if isinstance(node, ast.Name):
            name = node.id
            return name.isupper() and len(name) > 1
        return False

    def _is_enum_value(self, node: ast.expr) -> bool:
        """Check if a node looks like an enum value (EnumClass.VALUE)."""
        if isinstance(node, ast.Attribute):
            # Check if it's ClassName.VALUE pattern
            if isinstance(node.value, ast.Name):
                # The attribute should be uppercase (enum value)
                return node.attr.isupper() or node.attr[0].isupper()
        return False

    def _get_full_attribute(self, node: ast.Attribute) -> str:
        """Get the full attribute access string."""
        parts: list[str] = [node.attr]
        current = node.value

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        parts.reverse()
        return ".".join(parts)

    def _get_left_name(self, node: ast.expr) -> str:
        """Get a string representation of the left side of comparison."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return self._get_full_attribute(node)
        return "<expression>"

    def _get_comparison_value(self, node: ast.Compare) -> str:
        """Get string representation of what's being compared to."""
        if node.comparators:
            comp = node.comparators[0]
            if isinstance(comp, ast.Name):
                return comp.id
            if isinstance(comp, ast.Attribute):
                return self._get_full_attribute(comp)
            if isinstance(comp, ast.Constant):
                return repr(comp.value)
        return "<value>"

    def _get_constant_name(self, node: ast.expr) -> str:
        """Get the name of a constant."""
        if isinstance(node, ast.Name):
            return node.id
        return "<constant>"

    def _get_enum_name(self, node: ast.expr) -> str:
        """Get the name of an enum value."""
        if isinstance(node, ast.Attribute):
            return self._get_full_attribute(node)
        return "<enum>"

    def _classify_comparison_value(self, node: ast.Compare) -> str:
        """Classify what type of value is being compared."""
        if node.comparators:
            comp = node.comparators[0]
            if isinstance(comp, ast.Name) and comp.id.isupper():
                return "constant"
            if isinstance(comp, ast.Attribute):
                return "enum"
            if isinstance(comp, ast.Constant):
                if isinstance(comp.value, str):
                    return "string_literal"
                return "literal"
        return "unknown"

    def _add_violation(self, node: ast.If, chain_info: dict[str, Any]) -> None:
        """Add a violation for type code conditional."""
        checked_attr = chain_info.get("checked_attribute", "type")
        branch_count = chain_info.get("branch_count", 0)
        pattern_type = chain_info.get("pattern_type", "unknown")
        values = chain_info.get("comparison_values", [])

        if pattern_type == "constant":
            refactoring = "Replace Type Code with State/Strategy or Subclasses"
            suggestion = (
                f"The conditional checks '{checked_attr}' against constants "
                f"({', '.join(str(v) for v in values[:3])}{'...' if len(values) > 3 else ''}). "
                f"Consider replacing with polymorphism: create a class hierarchy where "
                f"each constant becomes a subclass with its own behavior."
            )
        elif pattern_type == "enum":
            refactoring = "Replace Type Code with State/Strategy"
            suggestion = (
                f"The conditional checks '{checked_attr}' against enum values. "
                f"Consider using the State or Strategy pattern where each enum value "
                f"corresponds to a class that implements the varying behavior."
            )
        else:
            refactoring = "Replace Conditional with Polymorphism"
            suggestion = (
                f"The conditional on '{checked_attr}' with {branch_count} branches "
                f"suggests a type code pattern. Consider using polymorphism."
            )

        self.violations.append(
            RuleViolation(
                rule_name="type_code",
                message=(
                    f"Type code conditional detected: '{checked_attr}' checked against "
                    f"{branch_count} different values. {refactoring}."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="warning",
                suggestion=suggestion,
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "type_code_conditional",
                    "checked_attribute": checked_attr,
                    "branch_count": branch_count,
                    "pattern_type": pattern_type,
                    "comparison_values": values,
                    "function": self._current_function,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "if_chain",
                "line": node.lineno,
                "checked_attribute": checked_attr,
                "branch_count": branch_count,
                "pattern_type": pattern_type,
            }
        )

    def _add_match_violation(
        self,
        node: ast.Match,
        subject: ast.expr,
        num_cases: int,
    ) -> None:
        """Add a violation for match statement on type code."""
        subject_str = self._get_left_name(subject)

        self.violations.append(
            RuleViolation(
                rule_name="type_code",
                message=(
                    f"Match statement on type code '{subject_str}' with {num_cases} cases. "
                    f"Consider replacing with polymorphism."
                ),
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity="warning",
                suggestion=(
                    "Match statements on type codes can be replaced with polymorphism. "
                    "Each case can become a subclass or strategy that implements the behavior."
                ),
                code_snippet=self._get_source_line(node.lineno),
                metadata={
                    "pattern": "match_type_code",
                    "subject": subject_str,
                    "case_count": num_cases,
                    "function": self._current_function,
                    "class": self._current_class,
                },
            )
        )
        self.patterns.append(
            {
                "type": "match",
                "line": node.lineno,
                "subject": subject_str,
                "case_count": num_cases,
            }
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
