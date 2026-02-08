"""
Example: Boolean Flag Rule

This file demonstrates boolean flag parameters that cause behavior branching.
Boolean flags violate the Single Responsibility Principle and make code harder to test.

References:
- https://refactoring.guru/smells/boolean-parameters
- Clean Code by Robert C. Martin

Run: uv run python -m oop_analyzer.cli examples/boolean_flag_example.py --rules boolean_flag
"""

from abc import ABC, abstractmethod

# =============================================================================
# BAD: Boolean flags causing behavior branching
# =============================================================================


class ReportGeneratorBad:
    """BAD: Uses boolean flags to control behavior."""

    def __init__(self, include_header: bool = True, use_cache: bool = False):
        """BAD: Constructor with boolean flags."""
        if use_cache:
            self._cache = {}
        else:
            self._cache = None
        self._include_header = include_header

    def generate(self, data, verbose: bool = False, as_html: bool = False):
        """BAD: Method with multiple boolean flags."""
        if verbose:
            print("Starting report generation...")

        result = self._generate_html(data) if as_html else self._generate_text(data)

        if verbose:
            print("Report generation complete.")

        return result

    def _generate_html(self, data):
        return f"<html>{data}</html>"

    def _generate_text(self, data):
        return str(data)


def save_file_bad(path: str, content: str, is_binary: bool = False):
    """BAD: Boolean flag determines completely different behavior."""
    if is_binary:
        with open(path, "wb") as f:
            f.write(content.encode())
    else:
        with open(path, "w") as f:
            f.write(content)


def fetch_data_bad(url: str, use_cache: bool = True, force_refresh: bool = False):
    """BAD: Multiple boolean flags with complex interaction."""
    if force_refresh:
        return _fetch_fresh(url)

    if use_cache:
        cached = _get_cached(url)
        if cached:
            return cached

    return _fetch_fresh(url)


def process_order_bad(order, skip_validation: bool = False, send_notification: bool = True):
    """BAD: Boolean flags control optional steps."""
    if not skip_validation:
        validate_order(order)

    result = execute_order(order)

    if send_notification:
        notify_customer(order)

    return result


# =============================================================================
# GOOD: Replace boolean flags with separate methods
# =============================================================================


class ReportGeneratorGood:
    """GOOD: Separate classes/methods instead of flags."""

    def __init__(self):
        self._cache = None

    def generate_text(self, data) -> str:
        """GOOD: Separate method for text generation."""
        return str(data)

    def generate_html(self, data) -> str:
        """GOOD: Separate method for HTML generation."""
        return f"<html>{data}</html>"


class CachedReportGenerator(ReportGeneratorGood):
    """GOOD: Separate class for cached behavior."""

    def __init__(self):
        super().__init__()
        self._cache = {}


class VerboseReportGenerator(ReportGeneratorGood):
    """GOOD: Decorator pattern for verbose behavior."""

    def __init__(self, generator: ReportGeneratorGood):
        super().__init__()
        self._generator = generator

    def generate_text(self, data) -> str:
        print("Starting report generation...")
        result = self._generator.generate_text(data)
        print("Report generation complete.")
        return result


def save_text_file(path: str, content: str) -> None:
    """GOOD: Separate function for text files."""
    with open(path, "w") as f:
        f.write(content)


def save_binary_file(path: str, content: bytes) -> None:
    """GOOD: Separate function for binary files."""
    with open(path, "wb") as f:
        f.write(content)


# =============================================================================
# GOOD: Use Strategy pattern instead of flags
# =============================================================================


class DataFetcher(ABC):
    """GOOD: Strategy pattern for fetching behavior."""

    @abstractmethod
    def fetch(self, url: str) -> str:
        pass


class DirectFetcher(DataFetcher):
    """GOOD: Always fetches fresh data."""

    def fetch(self, url: str) -> str:
        return _fetch_fresh(url)


class CachedFetcher(DataFetcher):
    """GOOD: Uses cache when available."""

    def __init__(self):
        self._cache = {}

    def fetch(self, url: str) -> str:
        if url in self._cache:
            return self._cache[url]
        result = _fetch_fresh(url)
        self._cache[url] = result
        return result


class ForcedRefreshFetcher(DataFetcher):
    """GOOD: Always refreshes, ignoring cache."""

    def __init__(self, cache: dict):
        self._cache = cache

    def fetch(self, url: str) -> str:
        result = _fetch_fresh(url)
        self._cache[url] = result
        return result


# =============================================================================
# GOOD: Use composition for optional behaviors
# =============================================================================


class OrderProcessor:
    """GOOD: Compose behaviors instead of flags."""

    def __init__(
        self,
        validator: "OrderValidator | None" = None,
        notifier: "OrderNotifier | None" = None,
    ):
        self._validator = validator
        self._notifier = notifier

    def process(self, order):
        if self._validator:
            self._validator.validate(order)

        result = execute_order(order)

        if self._notifier:
            self._notifier.notify(order)

        return result


class OrderValidator:
    def validate(self, order) -> None:
        pass


class OrderNotifier:
    def notify(self, order) -> None:
        pass


# Usage:
# processor = OrderProcessor(validator=OrderValidator(), notifier=OrderNotifier())
# processor_no_validation = OrderProcessor(notifier=OrderNotifier())
# processor_silent = OrderProcessor(validator=OrderValidator())


# =============================================================================
# Helper stubs
# =============================================================================


def _fetch_fresh(url: str) -> str:
    return f"data from {url}"


def _get_cached(url: str) -> str | None:
    return None


def validate_order(order) -> None:
    pass


def execute_order(order):
    return order


def notify_customer(order) -> None:
    pass
