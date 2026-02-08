"""
Coupling Rule - Dependency Graph Analysis.

This rule measures coupling between modules by analyzing imports
and building a dependency graph. It identifies:
- Most used dependencies (internal and external)
- Coupling chains
- Where abstractions might be missing
"""

import ast
from collections import defaultdict
from typing import Any

from .base import BaseRule, RuleResult, RuleViolation


class CouplingRule(BaseRule):
    """
    Measures coupling and builds dependency graph.

    Analyzes:
    - Import statements to build dependency graph
    - Frequency of imports to identify high coupling
    - External vs internal dependencies
    - Coupling chains (A -> B -> C)
    """

    name = "coupling"
    description = "Measure coupling and show dependency graph"
    severity = "info"

    def __init__(self, options: dict[str, Any] | None = None):
        super().__init__(options)
        self.max_imports_warning = self.options.get("max_imports_warning", 10)
        self.max_coupling_depth = self.options.get("max_coupling_depth", 5)

    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """Analyze a single file for imports."""
        visitor = ImportVisitor(file_path)
        visitor.visit(tree)

        violations: list[RuleViolation] = []

        # Check for too many imports
        total_imports = len(visitor.imports)
        if total_imports > self.max_imports_warning:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message=(
                        f"High coupling detected: {total_imports} imports. "
                        f"Consider breaking this module into smaller pieces."
                    ),
                    file_path=file_path,
                    line=1,
                    severity="warning",
                    suggestion=(
                        "High number of imports often indicates a module is doing too much. "
                        "Consider applying the Single Responsibility Principle."
                    ),
                    metadata={"import_count": total_imports},
                )
            )

        return RuleResult(
            rule_name=self.name,
            violations=violations,
            summary={
                "total_imports": total_imports,
                "internal_imports": len(visitor.internal_imports),
                "stdlib_imports": len(visitor.stdlib_imports),
                "external_imports": len(visitor.external_imports),
            },
            metadata={
                "imports": visitor.imports,
                "internal_imports": visitor.internal_imports,
                "stdlib_imports": visitor.stdlib_imports,
                "external_imports": visitor.external_imports,
                "import_details": visitor.import_details,
                "import_locations": dict(visitor.import_locations.items()),
            },
        )

    def analyze_multiple(
        self,
        files: list[tuple[ast.Module, str, str]],
    ) -> RuleResult:
        """
        Analyze multiple files to build complete dependency graph.

        This is where the real coupling analysis happens - we need
        to see all files to understand the full dependency structure.
        """
        all_violations: list[RuleViolation] = []
        dependency_graph: dict[str, set[str]] = defaultdict(set)
        import_frequency: dict[str, int] = defaultdict(int)
        external_deps: dict[str, int] = defaultdict(int)
        stdlib_deps: dict[str, int] = defaultdict(int)
        internal_deps: dict[str, int] = defaultdict(int)
        file_imports: dict[str, list[str]] = {}
        # Track all import locations across files: module -> [(file, line), ...]
        all_import_locations: dict[str, list[tuple[str, int]]] = defaultdict(list)

        # Collect all internal module names
        internal_modules = set()
        for _, _, file_path in files:
            module_name = self._file_to_module(file_path)
            if module_name:
                internal_modules.add(module_name)
                # Also add parent packages
                parts = module_name.split(".")
                for i in range(1, len(parts)):
                    internal_modules.add(".".join(parts[:i]))

        # Analyze each file
        for tree, source, file_path in files:
            result = self.analyze(tree, source, file_path)
            all_violations.extend(result.violations)

            module_name = self._file_to_module(file_path) or file_path
            imports = result.metadata.get("imports", [])
            file_imports[file_path] = imports

            # Merge import locations
            for mod, locations in result.metadata.get("import_locations", {}).items():
                all_import_locations[mod].extend(locations)

            # Classify imports
            for detail in result.metadata.get("import_details", []):
                imp = detail["module"]
                imp_type = detail["type"]

                dependency_graph[module_name].add(imp)
                import_frequency[imp] += 1

                if imp_type == "internal" or self._is_internal(imp, internal_modules):
                    internal_deps[imp] += 1
                elif imp_type == "stdlib":
                    stdlib_deps[imp] += 1
                else:
                    external_deps[imp] += 1

        # Find most coupled modules
        most_used = sorted(
            import_frequency.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        most_used_external = sorted(
            external_deps.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        most_used_stdlib = sorted(
            stdlib_deps.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        most_used_internal = sorted(
            internal_deps.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Find coupling chains
        coupling_chains = self._find_coupling_chains(dependency_graph)

        # Add violations for highly coupled external (third-party) modules - WARNING
        for module, count in most_used_external:
            if count >= 3:  # Lower threshold for external deps
                locations = all_import_locations.get(module, [])
                location_str = ", ".join(f"{fp}:{ln}" for fp, ln in locations[:5])
                if len(locations) > 5:
                    location_str += f" (+{len(locations) - 5} more)"

                all_violations.append(
                    RuleViolation(
                        rule_name=self.name,
                        message=(
                            f"External dependency '{module}' is imported {count} times. "
                            f"High coupling to third-party libraries increases risk."
                        ),
                        file_path="<project>",
                        line=0,
                        severity="warning",
                        suggestion=(
                            f"Consider wrapping '{module}' behind an abstraction/interface "
                            f"to reduce coupling to external dependencies."
                        ),
                        code_snippet=f"Imported at: {location_str}",
                        metadata={
                            "module": module,
                            "import_count": count,
                            "type": "external",
                            "locations": locations,
                        },
                    )
                )

        # Add violations for highly coupled stdlib modules - INFO (soft warning)
        for module, count in most_used_stdlib:
            if count >= 5:  # Higher threshold for stdlib
                locations = all_import_locations.get(module, [])
                location_str = ", ".join(f"{fp}:{ln}" for fp, ln in locations[:5])
                if len(locations) > 5:
                    location_str += f" (+{len(locations) - 5} more)"

                all_violations.append(
                    RuleViolation(
                        rule_name=self.name,
                        message=(
                            f"Standard library module '{module}' is imported {count} times. "
                            f"Consider if an abstraction would help."
                        ),
                        file_path="<project>",
                        line=0,
                        severity="info",
                        suggestion=(
                            f"While stdlib dependencies are stable, high usage of '{module}' "
                            f"might still benefit from a wrapper for testability."
                        ),
                        code_snippet=f"Imported at: {location_str}",
                        metadata={
                            "module": module,
                            "import_count": count,
                            "type": "stdlib",
                            "locations": locations,
                        },
                    )
                )

        return RuleResult(
            rule_name=self.name,
            violations=all_violations,
            summary={
                "total_files": len(files),
                "total_unique_imports": len(import_frequency),
                "external_dependencies": len(external_deps),
                "stdlib_dependencies": len(stdlib_deps),
                "internal_dependencies": len(internal_deps),
                "most_used_modules": most_used,
                "most_used_external": most_used_external,
                "most_used_stdlib": most_used_stdlib,
                "most_used_internal": most_used_internal,
            },
            metadata={
                "dependency_graph": {k: list(v) for k, v in dependency_graph.items()},
                "import_frequency": dict(import_frequency),
                "external_deps": dict(external_deps),
                "stdlib_deps": dict(stdlib_deps),
                "internal_deps": dict(internal_deps),
                "coupling_chains": coupling_chains,
                "file_imports": file_imports,
                "import_locations": dict(all_import_locations.items()),
            },
        )

    def _file_to_module(self, file_path: str) -> str | None:
        """Convert a file path to a module name."""
        if not file_path.endswith(".py"):
            return None

        # Remove .py extension
        module_path = file_path[:-3]

        # Convert path separators to dots
        module_name = module_path.replace("/", ".").replace("\\", ".")

        # Remove __init__ suffix
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]

        # Get just the last parts (relative module name)
        parts = module_name.split(".")
        if len(parts) > 2:
            return ".".join(parts[-2:])
        return parts[-1] if parts else None

    def _is_internal(self, module: str, internal_modules: set[str]) -> bool:
        """Check if a module is internal to the project."""
        if module in internal_modules:
            return True

        # Check if it's a submodule of an internal module
        return any(module.startswith(internal + ".") for internal in internal_modules)

    def _find_coupling_chains(
        self,
        graph: dict[str, set[str]],
        max_depth: int | None = None,
    ) -> list[list[str]]:
        """Find chains of dependencies (A -> B -> C)."""
        max_depth = max_depth or self.max_coupling_depth
        chains: list[list[str]] = []

        def dfs(node: str, path: list[str], visited: set[str]) -> None:
            if len(path) > max_depth:
                return
            if node in visited:
                return

            visited.add(node)
            path.append(node)

            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        dfs(neighbor, path.copy(), visited.copy())

            if len(path) >= 3:  # Only record chains of 3 or more
                chains.append(path)

        for start_node in graph:
            dfs(start_node, [], set())

        # Sort by length and return top chains
        chains.sort(key=len, reverse=True)
        return chains[:20]


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that collects import information."""

    # Standard library modules (comprehensive list)
    STDLIB_MODULES = {
        "abc",
        "aifc",
        "argparse",
        "array",
        "ast",
        "asynchat",
        "asyncio",
        "asyncore",
        "atexit",
        "audioop",
        "base64",
        "bdb",
        "binascii",
        "binhex",
        "bisect",
        "builtins",
        "bz2",
        "calendar",
        "cgi",
        "cgitb",
        "chunk",
        "cmath",
        "cmd",
        "code",
        "codecs",
        "codeop",
        "collections",
        "colorsys",
        "compileall",
        "concurrent",
        "configparser",
        "contextlib",
        "contextvars",
        "copy",
        "copyreg",
        "cProfile",
        "crypt",
        "csv",
        "ctypes",
        "curses",
        "dataclasses",
        "datetime",
        "dbm",
        "decimal",
        "difflib",
        "dis",
        "distutils",
        "doctest",
        "email",
        "encodings",
        "enum",
        "errno",
        "faulthandler",
        "fcntl",
        "filecmp",
        "fileinput",
        "fnmatch",
        "fractions",
        "ftplib",
        "functools",
        "gc",
        "getopt",
        "getpass",
        "gettext",
        "glob",
        "graphlib",
        "grp",
        "gzip",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "http",
        "idlelib",
        "imaplib",
        "imghdr",
        "imp",
        "importlib",
        "inspect",
        "io",
        "ipaddress",
        "itertools",
        "json",
        "keyword",
        "lib2to3",
        "linecache",
        "locale",
        "logging",
        "lzma",
        "mailbox",
        "mailcap",
        "marshal",
        "math",
        "mimetypes",
        "mmap",
        "modulefinder",
        "multiprocessing",
        "netrc",
        "nis",
        "nntplib",
        "numbers",
        "operator",
        "optparse",
        "os",
        "ossaudiodev",
        "pathlib",
        "pdb",
        "pickle",
        "pickletools",
        "pipes",
        "pkgutil",
        "platform",
        "plistlib",
        "poplib",
        "posix",
        "posixpath",
        "pprint",
        "profile",
        "pstats",
        "pty",
        "pwd",
        "py_compile",
        "pyclbr",
        "pydoc",
        "queue",
        "quopri",
        "random",
        "re",
        "readline",
        "reprlib",
        "resource",
        "rlcompleter",
        "runpy",
        "sched",
        "secrets",
        "select",
        "selectors",
        "shelve",
        "shlex",
        "shutil",
        "signal",
        "site",
        "smtpd",
        "smtplib",
        "sndhdr",
        "socket",
        "socketserver",
        "spwd",
        "sqlite3",
        "ssl",
        "stat",
        "statistics",
        "string",
        "stringprep",
        "struct",
        "subprocess",
        "sunau",
        "symtable",
        "sys",
        "sysconfig",
        "syslog",
        "tabnanny",
        "tarfile",
        "telnetlib",
        "tempfile",
        "termios",
        "test",
        "textwrap",
        "threading",
        "time",
        "timeit",
        "tkinter",
        "token",
        "tokenize",
        "tomllib",
        "trace",
        "traceback",
        "tracemalloc",
        "tty",
        "turtle",
        "turtledemo",
        "types",
        "typing",
        "unicodedata",
        "unittest",
        "urllib",
        "uu",
        "uuid",
        "venv",
        "warnings",
        "wave",
        "weakref",
        "webbrowser",
        "winreg",
        "winsound",
        "wsgiref",
        "xdrlib",
        "xml",
        "xmlrpc",
        "zipapp",
        "zipfile",
        "zipimport",
        "zlib",
        "zoneinfo",
    }

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: list[str] = []
        self.internal_imports: list[str] = []
        self.external_imports: list[str] = []
        self.stdlib_imports: list[str] = []
        self.import_details: list[dict[str, Any]] = []
        # Track import locations: module -> [(file, line)]
        self.import_locations: dict[str, list[tuple[str, int]]] = defaultdict(list)

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            module_name = alias.name
            self.imports.append(module_name)
            self.import_locations[module_name].append((self.file_path, node.lineno))
            self._classify_import(module_name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        module_name = node.module or ""

        # Handle relative imports
        if node.level > 0:
            module_name = "." * node.level + module_name
            self.imports.append(module_name)
            self.internal_imports.append(module_name)
            self.import_locations[module_name].append((self.file_path, node.lineno))
            self.import_details.append(
                {
                    "module": module_name,
                    "names": [a.name for a in node.names],
                    "line": node.lineno,
                    "file": self.file_path,
                    "is_relative": True,
                    "type": "internal",
                }
            )
        else:
            self.imports.append(module_name)
            self.import_locations[module_name].append((self.file_path, node.lineno))
            self._classify_import(module_name, node.lineno, [a.name for a in node.names])

        self.generic_visit(node)

    def _classify_import(
        self,
        module_name: str,
        line: int,
        names: list[str] | None = None,
    ) -> None:
        """Classify an import as internal, stdlib, or external (third-party)."""
        base_module = module_name.split(".")[0]

        if base_module in self.STDLIB_MODULES:
            import_type = "stdlib"
            self.stdlib_imports.append(module_name)
        elif module_name.startswith("."):
            import_type = "internal"
            self.internal_imports.append(module_name)
        else:
            # External (third-party) dependency
            import_type = "external"
            self.external_imports.append(module_name)

        self.import_details.append(
            {
                "module": module_name,
                "names": names or [],
                "line": line,
                "file": self.file_path,
                "is_relative": False,
                "type": import_type,
            }
        )
