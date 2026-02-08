"""
Example: Null Object Rule

This file demonstrates None usage that could be replaced by the Null Object pattern.
The Null Object pattern provides default behavior instead of null checks.

Run: uv run python -m oop_analyzer.cli examples/null_object_example.py --rules null_object
"""

from abc import ABC, abstractmethod

# =============================================================================
# BAD: Explicit None checks everywhere
# =============================================================================


class UserBad:
    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger  # Could be None

    def do_something(self) -> None:
        # BAD: None check before every use
        if self.logger is not None:
            self.logger.log("Doing something")

        print(f"{self.name} is doing something")

        # BAD: Another None check
        if self.logger is not None:
            self.logger.log("Done")


def find_user_bad(user_id: int) -> dict | None:
    """BAD: Returns None when not found."""
    users = {1: {"name": "Alice"}, 2: {"name": "Bob"}}
    if user_id in users:
        return users[user_id]
    return None  # BAD: Returning None


def process_user_bad(user_id: int) -> str:
    """BAD: Must check for None after every call."""
    user = find_user_bad(user_id)

    # BAD: None check required
    if user is None:
        return "Unknown"

    return user["name"]


def get_discount_bad(user=None) -> float:
    """BAD: None as default parameter."""
    # BAD: None check in function body
    if user is None:
        return 0.0
    return user.discount


def format_value_bad(value) -> str:
    """BAD: Ternary with None check."""
    # BAD: Ternary None check
    return str(value) if value is not None else "N/A"


# =============================================================================
# GOOD: Null Object Pattern
# =============================================================================


class Logger(ABC):
    @abstractmethod
    def log(self, message: str) -> None:
        pass


class RealLogger(Logger):
    def log(self, message: str) -> None:
        print(f"[LOG] {message}")


class NullLogger(Logger):
    """Null Object: Does nothing, but has the same interface."""

    def log(self, message: str) -> None:
        pass  # Intentionally does nothing


class UserGood:
    def __init__(self, name: str, logger: Logger | None = None):
        self.name = name
        # GOOD: Use Null Object instead of None
        self.logger = logger or NullLogger()

    def do_something(self) -> None:
        # GOOD: No None checks needed - just use it
        self.logger.log("Doing something")
        print(f"{self.name} is doing something")
        self.logger.log("Done")


# Null Object for User
class User(ABC):
    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_discount(self) -> float:
        pass


class RealUser(User):
    def __init__(self, name: str, discount: float = 0.0):
        self._name = name
        self._discount = discount

    def get_name(self) -> str:
        return self._name

    def get_discount(self) -> float:
        return self._discount


class NullUser(User):
    """Null Object: Represents a missing user with default behavior."""

    def get_name(self) -> str:
        return "Unknown"

    def get_discount(self) -> float:
        return 0.0


class UserRepository:
    def __init__(self):
        self._users = {
            1: RealUser("Alice", 0.1),
            2: RealUser("Bob", 0.2),
        }
        self._null_user = NullUser()

    def find(self, user_id: int) -> User:
        """GOOD: Always returns a User, never None."""
        return self._users.get(user_id, self._null_user)


def process_user_good(repo: UserRepository, user_id: int) -> str:
    """GOOD: No None checks needed."""
    user = repo.find(user_id)
    return user.get_name()  # Works for both real and null users


def get_discount_good(user: User) -> float:
    """GOOD: No None checks, just use the object."""
    return user.get_discount()


# Null Object for formatting
class Formatter(ABC):
    @abstractmethod
    def format(self, value) -> str:
        pass


class StringFormatter(Formatter):
    def format(self, value) -> str:
        return str(value)


class NullFormatter(Formatter):
    """Returns a default value for missing data."""

    def format(self, value) -> str:
        return "N/A"


def format_value_good(value, formatter: Formatter | None = None) -> str:
    """GOOD: Use Null Object for default behavior."""
    fmt = formatter or NullFormatter()
    return fmt.format(value)
