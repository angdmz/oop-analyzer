"""
Example: Reference Exposure Rule

This file demonstrates methods that expose internal mutable state,
which breaks encapsulation by allowing external code to modify internals.

Run: uv run python -m oop_analyzer.cli examples/reference_exposure_example.py --rules reference_exposure
"""

from collections.abc import Iterator
from dataclasses import dataclass

# =============================================================================
# BAD: Exposing internal mutable state
# =============================================================================


class ShoppingCartBad:
    """BAD: Exposes internal list directly."""

    def __init__(self):
        self._items = []

    def add_item(self, item: str) -> None:
        self._items.append(item)

    def get_items(self) -> list:
        """BAD: Returns the internal list directly.

        External code can now modify the cart's internal state:
        cart.get_items().clear()  # Oops! Cart is now empty.
        cart.get_items().append("free stuff")  # Added without validation!
        """
        return self._items


class UserManagerBad:
    """BAD: Exposes internal dictionary."""

    def __init__(self):
        self._users = {}

    def add_user(self, user_id: int, name: str) -> None:
        self._users[user_id] = name

    @property
    def users(self) -> dict:
        """BAD: Property exposing internal dict.

        External code can modify:
        manager.users[999] = "hacker"  # Added without validation!
        manager.users.clear()  # All users gone!
        """
        return self._users


class ConfigBad:
    """BAD: Exposes internal settings."""

    def __init__(self):
        self._settings = {
            "debug": False,
            "max_connections": 100,
        }

    def get_settings(self) -> dict:
        """BAD: External code can modify settings."""
        return self._settings


class CacheBad:
    """BAD: Exposes internal cache."""

    def __init__(self):
        self._cache = {}

    def get_cache(self) -> dict:
        """BAD: Cache can be corrupted by external code."""
        return self._cache


# =============================================================================
# GOOD: Defensive copying and immutable views
# =============================================================================


class ShoppingCartGood:
    """GOOD: Protects internal state."""

    def __init__(self):
        self._items: list[str] = []

    def add_item(self, item: str) -> None:
        self._items.append(item)

    def remove_item(self, item: str) -> bool:
        if item in self._items:
            self._items.remove(item)
            return True
        return False

    def get_items(self) -> list[str]:
        """GOOD: Returns a copy of the list."""
        return list(self._items)

    def get_items_readonly(self) -> tuple[str, ...]:
        """GOOD: Returns an immutable tuple."""
        return tuple(self._items)

    def __iter__(self) -> Iterator[str]:
        """GOOD: Allows iteration without exposing the list."""
        return iter(self._items.copy())

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: str) -> bool:
        return item in self._items


class UserManagerGood:
    """GOOD: Protects internal dictionary."""

    def __init__(self):
        self._users: dict[int, str] = {}

    def add_user(self, user_id: int, name: str) -> None:
        if user_id in self._users:
            raise ValueError(f"User {user_id} already exists")
        self._users[user_id] = name

    def get_user(self, user_id: int) -> str | None:
        """GOOD: Returns a single value, not the whole dict."""
        return self._users.get(user_id)

    def get_all_users(self) -> dict[int, str]:
        """GOOD: Returns a copy."""
        return dict(self._users)

    def get_user_ids(self) -> frozenset[int]:
        """GOOD: Returns an immutable set."""
        return frozenset(self._users.keys())

    @property
    def user_count(self) -> int:
        """GOOD: Expose derived data, not the collection."""
        return len(self._users)


@dataclass(frozen=True)
class Settings:
    """GOOD: Immutable settings object."""

    debug: bool
    max_connections: int


class ConfigGood:
    """GOOD: Uses immutable settings object."""

    def __init__(self):
        self._settings = Settings(debug=False, max_connections=100)

    @property
    def settings(self) -> Settings:
        """GOOD: Settings is immutable, safe to return."""
        return self._settings

    def update_settings(self, **kwargs) -> None:
        """GOOD: Controlled way to update settings."""
        current = self._settings
        self._settings = Settings(
            debug=kwargs.get("debug", current.debug),
            max_connections=kwargs.get("max_connections", current.max_connections),
        )


class CacheGood:
    """GOOD: Controlled cache access."""

    def __init__(self):
        self._cache: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        """GOOD: Single item access."""
        return self._cache.get(key)

    def set(self, key: str, value: object) -> None:
        """GOOD: Controlled modification."""
        self._cache[key] = value

    def delete(self, key: str) -> bool:
        """GOOD: Controlled deletion."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """GOOD: Explicit clear method."""
        self._cache.clear()

    def keys(self) -> frozenset[str]:
        """GOOD: Returns immutable view of keys."""
        return frozenset(self._cache.keys())

    def snapshot(self) -> dict[str, object]:
        """GOOD: Explicitly named method that returns a copy."""
        return dict(self._cache)


# =============================================================================
# Demonstration of the problem
# =============================================================================


def demonstrate_problem():
    """Shows why reference exposure is dangerous."""

    # BAD: External code can break invariants
    cart_bad = ShoppingCartBad()
    cart_bad.add_item("apple")
    cart_bad.add_item("banana")

    # Get the "items" and modify them directly
    items = cart_bad.get_items()
    items.clear()  # Oops! We just cleared the cart's internal state!
    items.append("stolen_item")  # Added without going through add_item()!

    print(f"Cart items (corrupted): {cart_bad.get_items()}")

    # GOOD: External code cannot break invariants
    cart_good = ShoppingCartGood()
    cart_good.add_item("apple")
    cart_good.add_item("banana")

    # Get the "items" - it's a copy
    items = cart_good.get_items()
    items.clear()  # Only clears the copy
    items.append("stolen_item")  # Only modifies the copy

    print(f"Cart items (protected): {cart_good.get_items()}")
