# OOP Analyzer

A static analysis tool for Python that checks adherence to Object-Oriented Programming best practices. **Safe by design** - analyzes code using AST parsing only, never executes any code.

## Features

- **Encapsulation Rule**: Detects direct property access violations (Tell Don't Ask principle)
- **Coupling Rule**: Measures coupling, builds dependency graphs, differentiates stdlib (soft warning) vs external dependencies (warning)
- **Null Object Rule**: Finds None usage and Optional type hints that could introduce nulls
- **Polymorphism Rule**: Detects if/elif chains replaceable by polymorphism
- **Functions to Objects Rule**: Identifies functions that could be better represented as objects
- **Type Code Rule**: Detects conditionals checking constants/enums that should use State/Strategy pattern
- **Reference Exposure Rule**: Finds methods returning internal mutable state that breaks encapsulation
- **Dictionary Usage Rule**: Detects dictionaries that should be dataclasses/Pydantic models (allows API boundaries)
- **Boolean Flag Rule**: Detects boolean flag parameters causing behavior branching

## Installation

### From PyPI (recommended)

```bash
pip install oop-analyzer
```

### From source

```bash
# Clone the repository
git clone https://github.com/agustindorda/oop-analyzer.git
cd oop-analyzer

# Install with pip
pip install .

# Or install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Using uv

```bash
uv add oop-analyzer
```

## Usage

### Command Line

```bash
# Analyze a single file
oop-analyzer path/to/file.py

# Analyze a directory
oop-analyzer path/to/project/

# Analyze a module
oop-analyzer path/to/module/

# Specify output format (json, xml, html)
oop-analyzer path/to/file.py -f html -o report.html

# Enable only specific rules
oop-analyzer path/to/file.py --rules encapsulation coupling

# Disable specific rules
oop-analyzer path/to/file.py --disable-rules functions_to_objects

# List available rules
oop-analyzer --list-rules

# Generate default config file
oop-analyzer --init-config oop-analyzer.json
```

### Python API

```python
from oop_analyzer import OOPAnalyzer, AnalyzerConfig

# Default configuration (all rules enabled)
analyzer = OOPAnalyzer()

# Analyze source code
report = analyzer.analyze_source('''
def process(user):
    print(user.name)  # Encapsulation violation
''')

# Analyze a file
report = analyzer.analyze_file("path/to/file.py")

# Analyze a directory or module
report = analyzer.analyze("path/to/project/")

# Get formatted output
json_output = analyzer.format_report(report, "json")
html_output = analyzer.format_report(report, "html")
xml_output = analyzer.format_report(report, "xml")

# Custom configuration
config = AnalyzerConfig()
config.enable_only("encapsulation", "null_object")
config.output_format = "html"

analyzer = OOPAnalyzer(config)
```

## Configuration

Create a `oop-analyzer.json` file:

```json
{
  "rules": {
    "encapsulation": {
      "enabled": true,
      "severity": "warning",
      "options": {
        "allow_self_access": true,
        "max_chain_length": 1
      }
    },
    "coupling": {
      "enabled": true,
      "options": {
        "max_imports_warning": 10
      }
    },
    "null_object": true,
    "polymorphism": {
      "enabled": true,
      "options": {
        "min_branches": 3
      }
    },
    "functions_to_objects": {
      "enabled": true,
      "options": {
        "max_params": 4
      }
    }
  },
  "output_format": "json",
  "exclude_patterns": ["**/test_*.py", "**/*_test.py", "**/tests/**"]
}
```

## Rules

### Encapsulation (Tell Don't Ask)

Detects direct property access on objects. In OOP, we should "tell" objects what to do, not "ask" them for data.

**Bad:**
```python
if user.age > 18:
    print(user.name)
```

**Good:**
```python
if user.is_adult():
    user.greet()
```

**Better:**
```python
adult_user.greet()
```

### Coupling

Measures module coupling through import analysis. Shows dependency graphs and identifies highly-coupled modules where abstractions might be missing.

### Null Object

Detects None usage patterns that could be replaced by the Null Object pattern:
- `if x is None` checks
- `return None` statements
- Parameters with `None` defaults

### Polymorphism

Finds if/elif chains and type checks that could be replaced by polymorphism:
- Long if/elif chains checking the same variable
- `isinstance()` checks
- Type/kind attribute comparisons

### Functions to Objects

Identifies functions that might be better as objects:
- Functions with many parameters
- Functions returning dictionaries
- Groups of related functions with common prefixes

### Type Code (NEW)

Detects type code conditionals that should be replaced with polymorphism:

**Bad:**
```python
class Bird:
    def getSpeed(self):
        if self.type == EUROPEAN:
            return self.getBaseSpeed()
        elif self.type == AFRICAN:
            return self.getBaseSpeed() - self.getLoadFactor()
        elif self.type == NORWEGIAN_BLUE:
            return 0 if self.isNailed else self.getBaseSpeed(self.voltage)
```

**Good:** Use State/Strategy pattern or subclasses:
```python
class Bird(ABC):
    @abstractmethod
    def getSpeed(self) -> float: pass

class EuropeanBird(Bird):
    def getSpeed(self) -> float:
        return self.getBaseSpeed()

class AfricanBird(Bird):
    def getSpeed(self) -> float:
        return self.getBaseSpeed() - self.getLoadFactor()
```

References:
- https://refactoring.guru/replace-type-code-with-state-strategy
- https://refactoring.guru/replace-type-code-with-subclasses

### Reference Exposure (NEW)

Detects methods that return references to internal mutable state, breaking encapsulation:

**Bad:**
```python
class Container:
    def __init__(self):
        self._items = []
    
    def get_items(self):
        return self._items  # External code can modify internal state!
```

**Good:** Return a copy or immutable view:
```python
class Container:
    def __init__(self):
        self._items = []
    
    def get_items(self):
        return list(self._items)  # Return a copy
    
    # Or return a tuple for immutability
    def get_items_readonly(self):
        return tuple(self._items)
```

### Dictionary Usage (NEW)

Detects dictionary usage that should be replaced by proper objects (dataclasses, Pydantic models, etc.). Dictionaries are acceptable at API boundaries (parsing REST responses), but abstraction layers should use typed objects.

**Bad:**
```python
def get_user():
    return {"name": "John", "age": 30, "email": "john@example.com"}

def process(user: dict):
    print(user["name"])  # No type safety, easy to typo keys
```

**Good:** Use dataclasses or Pydantic models:
```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
    email: str

def get_user() -> User:
    return User(name="John", age=30, email="john@example.com")

def process(user: User):
    print(user.name)  # Type-safe, IDE autocomplete
```

**Acceptable** (API boundary):
```python
def parse_api_response(response: dict) -> User:
    # Converting from dict at the boundary is fine
    return User(**response)
```

## Extending with New Rules

Create a new rule by inheriting from `BaseRule`:

```python
from oop_analyzer.rules.base import BaseRule, RuleResult, RuleViolation

class MyCustomRule(BaseRule):
    name = "my_rule"
    description = "My custom OOP rule"
    
    def analyze(self, tree, source, file_path):
        violations = []
        # Analyze the AST tree
        # Add violations as needed
        return RuleResult(
            rule_name=self.name,
            violations=violations,
        )
```

Register in `oop_analyzer/rules/__init__.py`:

```python
RULE_REGISTRY["my_rule"] = MyCustomRule
```

## Safety

The analyzer is designed to be safe:
- **No code execution**: Only AST parsing, never `exec()` or `eval()`
- **File validation**: Checks file existence, type, and size limits
- **Syntax validation**: Gracefully handles malformed code

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=oop_analyzer

# Run specific test file
pytest tests/test_rules/test_encapsulation.py
```

## License

MIT
