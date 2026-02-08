"""
Encapsulation Rule - Tell Don't Ask principle.

This rule detects violations of encapsulation where objects are accessed
directly through their properties instead of through methods.

In OOP, we should "tell" objects what to do, not "ask" them for data
and then make decisions based on that data.
"""

import ast
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class EncapsulationRule(BaseRule):
    """
    Detects direct property access on objects (tell don't ask violations).

    Violations include:
    - Accessing object attributes directly: obj.property
    - Especially when followed by operations on that property
    - Chained attribute access: obj.prop1.prop2

    Exceptions:
    - Method calls: obj.method() is fine
    - Self access within a class: self.x is often necessary
    - Module-level constants: CONSTANT access
    - Module attribute access: json.JSONEncoder, redis.Redis (normal Python usage)
    - Named tuple / dataclass field access (configurable)
    """

    name = "encapsulation"
    description = "Check for direct property access (tell don't ask)"
    severity = "warning"

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.allow_self_access = self.options.get("allow_self_access", True)
        self.allow_private_access = self.options.get("allow_private_access", False)
        self.allow_dunder_access = self.options.get("allow_dunder_access", True)
        self.max_chain_length = self.options.get("max_chain_length", 1)
        self.warn_dependency_access = self.options.get("warn_dependency_access", True)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze the AST for encapsulation violations."""
        violations: list[RuleViolation] = []
        visitor = EncapsulationVisitor(
            file_path=file_path,
            source=source,
            allow_self_access=self.allow_self_access,
            allow_private_access=self.allow_private_access,
            allow_dunder_access=self.allow_dunder_access,
            max_chain_length=self.max_chain_length,
            warn_dependency_access=self.warn_dependency_access,
        )
        visitor.visit(tree)
        violations = visitor.violations

        return RuleResult(
            rule_name=self.name,
            violations=violations,
            summary={
                "total_violations": len(violations),
                "files_analyzed": 1,
                "module_access_skipped": visitor.module_access_skipped,
            },
        )


class EncapsulationVisitor(ast.NodeVisitor):
    """AST visitor that detects encapsulation violations."""

    def __init__(
        self,
        file_path: str,
        source: str,
        allow_self_access: bool = True,
        allow_private_access: bool = False,
        allow_dunder_access: bool = True,
        max_chain_length: int = 1,
        warn_dependency_access: bool = True,
    ):
        self.file_path = file_path
        self.source = source
        self.allow_self_access = allow_self_access
        self.allow_private_access = allow_private_access
        self.allow_dunder_access = allow_dunder_access
        self.max_chain_length = max_chain_length
        self.warn_dependency_access = warn_dependency_access
        self.violations: list[RuleViolation] = []
        self._in_class = False
        self._current_class: str | None = None
        self._call_targets: set[int] = set()  # IDs of nodes that are call targets
        self._imported_modules: set[str] = set()  # Names of imported modules
        self._class_bases: set[int] = set()  # IDs of nodes used as class bases
        self.module_access_skipped = 0

    def visit_Import(self, node: ast.Import) -> None:
        """Track imported module names."""
        for alias in node.names:
            # Use the alias if provided, otherwise the module name
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self._imported_modules.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track imported names from modules."""
        if node.module:
            # Track the module itself if imported with alias
            for alias in node.names:
                if alias.asname:
                    self._imported_modules.add(alias.asname)
                else:
                    self._imported_modules.add(alias.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track when we're inside a class definition."""
        # Mark base class nodes to skip them (e.g., json.JSONEncoder)
        for base in node.bases:
            self._mark_as_class_base(base)

        old_in_class = self._in_class
        old_class = self._current_class
        self._in_class = True
        self._current_class = node.name
        self.generic_visit(node)
        self._in_class = old_in_class
        self._current_class = old_class

    def _mark_as_class_base(self, node: ast.expr) -> None:
        """Recursively mark nodes used as class bases."""
        self._class_bases.add(id(node))
        if isinstance(node, ast.Attribute):
            self._class_bases.add(id(node.value))
            self._mark_as_class_base(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        """Mark call targets so we don't flag method calls as violations."""
        if isinstance(node.func, ast.Attribute):
            self._call_targets.add(id(node.func))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check attribute access for encapsulation violations."""
        # Skip if this is a method call (the attribute is the target of a Call)
        if id(node) in self._call_targets:
            self.generic_visit(node)
            return

        # Skip if this is a class base (e.g., class Foo(json.JSONEncoder))
        if id(node) in self._class_bases:
            self.module_access_skipped += 1
            self.generic_visit(node)
            return

        # Get the chain of attribute access
        chain = self._get_attribute_chain(node)

        if not chain:
            self.generic_visit(node)
            return

        base_name = chain[0]
        attr_names = chain[1:]

        # Skip self/cls access if allowed
        if self.allow_self_access and base_name in ("self", "cls"):
            self.generic_visit(node)
            return

        # Skip module attribute access (e.g., json.JSONEncoder, redis.Redis)
        # This is normal Python module usage, not an encapsulation violation
        if base_name in self._imported_modules:
            # Check if accessing a class/constant from a module (PascalCase or UPPER_CASE)
            if len(attr_names) == 1:
                attr = attr_names[0]
                # PascalCase (class) or UPPER_CASE (constant)
                if attr[0].isupper():
                    self.module_access_skipped += 1
                    self.generic_visit(node)
                    return

        # Skip dunder attributes if allowed
        if self.allow_dunder_access:
            if any(attr.startswith("__") and attr.endswith("__") for attr in attr_names):
                self.generic_visit(node)
                return

        # Skip private attributes if allowed
        if self.allow_private_access and any(attr.startswith("_") for attr in attr_names):
            self.generic_visit(node)
            return

        # Check for violations
        if len(attr_names) > 0:
            # Direct property access detected
            violation = self._create_violation(node, base_name, attr_names)
            if violation:
                self.violations.append(violation)

        self.generic_visit(node)

    def _get_attribute_chain(self, node: ast.Attribute) -> list[str]:
        """
        Get the full chain of attribute access.

        For `obj.prop1.prop2`, returns ["obj", "prop1", "prop2"]
        """
        chain: list[str] = []
        current: ast.expr = node

        while isinstance(current, ast.Attribute):
            chain.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            chain.append(current.id)
        else:
            # Complex expression, can't determine base
            return []

        chain.reverse()
        return chain

    def _create_violation(
        self,
        node: ast.Attribute,
        base_name: str,
        attr_names: list[str],
    ) -> RuleViolation | None:
        """Create a violation for direct property access."""
        # Skip module-level access patterns (all caps = constants)
        if all(c.isupper() or c == "_" for c in attr_names[-1]):
            return None

        # Skip common module access patterns
        if base_name in ("os", "sys", "math", "typing", "collections", "functools"):
            return None

        full_access = f"{base_name}.{'.'.join(attr_names)}"

        # Check chain length
        if len(attr_names) > self.max_chain_length:
            message = (
                f"Long attribute chain detected: '{full_access}'. "
                f"This violates the Law of Demeter. Consider using delegation."
            )
            suggestion = (
                f"Instead of accessing '{full_access}', consider adding a method "
                f"to '{base_name}' that encapsulates this behavior."
            )
        else:
            message = (
                f"Direct property access: '{full_access}'. "
                f"Consider using a method instead (Tell Don't Ask)."
            )
            suggestion = (
                f"Instead of accessing '{base_name}.{attr_names[0]}', "
                f"consider telling '{base_name}' what to do with a method call."
            )

        return RuleViolation(
            rule_name="encapsulation",
            message=message,
            file_path=self.file_path,
            line=node.lineno,
            column=node.col_offset,
            severity="warning",
            suggestion=suggestion,
            code_snippet=self._get_source_line(node.lineno),
            metadata={
                "base_object": base_name,
                "accessed_attributes": attr_names,
                "chain_length": len(attr_names),
            },
        )

    def _get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = self.source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
