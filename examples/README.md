# OOP Analyzer Examples

This directory contains example files demonstrating each rule in the OOP Analyzer.
Each file shows both **bad** patterns (what the rule detects) and **good** patterns (how to fix them).

## Running the Examples

Analyze all examples:
```bash
uv run python -m oop_analyzer.cli examples/
```

Analyze a specific example:
```bash
uv run python -m oop_analyzer.cli examples/encapsulation_example.py --rules encapsulation
```

Generate an HTML report:
```bash
uv run python -m oop_analyzer.cli examples/ -f html -o examples_report.html
```

## Examples

### 1. Encapsulation (Tell Don't Ask)
**File:** `encapsulation_example.py`

Demonstrates direct property access violations. We should "tell" objects what to do, not "ask" them for data.

```bash
uv run python -m oop_analyzer.cli examples/encapsulation_example.py --rules encapsulation
```

### 2. Coupling
**File:** `coupling_example.py`

Demonstrates high coupling through imports. Shows how to reduce coupling using dependency injection and abstractions.

```bash
uv run python -m oop_analyzer.cli examples/coupling_example.py --rules coupling
```

### 3. Null Object Pattern
**File:** `null_object_example.py`

Demonstrates None usage that could be replaced by the Null Object pattern.

```bash
uv run python -m oop_analyzer.cli examples/null_object_example.py --rules null_object
```

### 4. Polymorphism
**File:** `polymorphism_example.py`

Demonstrates if/elif chains and isinstance() checks that could be replaced by polymorphism.

```bash
uv run python -m oop_analyzer.cli examples/polymorphism_example.py --rules polymorphism
```

### 5. Functions to Objects
**File:** `functions_to_objects_example.py`

Demonstrates functions that could be better represented as objects (too many parameters, dict returns, related function groups).

```bash
uv run python -m oop_analyzer.cli examples/functions_to_objects_example.py --rules functions_to_objects
```

### 6. Type Code
**File:** `type_code_example.py`

Demonstrates type code conditionals (checking constants/enums) that should use State/Strategy pattern or subclasses.

```bash
uv run python -m oop_analyzer.cli examples/type_code_example.py --rules type_code
```

### 7. Reference Exposure
**File:** `reference_exposure_example.py`

Demonstrates methods that expose internal mutable state, breaking encapsulation.

```bash
uv run python -m oop_analyzer.cli examples/reference_exposure_example.py --rules reference_exposure
```

### 8. Dictionary Usage
**File:** `dictionary_usage_example.py`

Demonstrates dictionary usage that should be replaced by dataclasses or Pydantic models. Shows acceptable usage at API boundaries.

```bash
uv run python -m oop_analyzer.cli examples/dictionary_usage_example.py --rules dictionary_usage
```

### 9. Boolean Flag
**File:** `boolean_flag_example.py`

Demonstrates boolean flag parameters that cause behavior branching. Shows how to replace flags with separate methods, Strategy pattern, or composition.

```bash
uv run python -m oop_analyzer.cli examples/boolean_flag_example.py --rules boolean_flag
```

## Structure of Each Example

Each example file follows this structure:

1. **Header comment** - Explains the rule and how to run the analyzer
2. **BAD section** - Code that violates the rule (what the analyzer detects)
3. **GOOD section** - Refactored code that follows best practices
4. **Optional: BEST section** - Even better approaches using advanced patterns

## Learning Path

For learning OOP best practices, we recommend reading the examples in this order:

1. **encapsulation_example.py** - Foundation of OOP
2. **polymorphism_example.py** - Replacing conditionals with objects
3. **type_code_example.py** - Advanced polymorphism patterns
4. **null_object_example.py** - Handling absence without null checks
5. **reference_exposure_example.py** - Protecting internal state
6. **dictionary_usage_example.py** - Using proper types
7. **functions_to_objects_example.py** - When to create classes
8. **boolean_flag_example.py** - Avoiding behavior branching on flags
9. **coupling_example.py** - Managing dependencies
