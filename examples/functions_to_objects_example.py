"""
Example: Functions to Objects Rule

This file demonstrates functions that could be better represented as objects.
The rule detects functions with many parameters, dict returns, and related function groups.

Run: uv run python -m oop_analyzer.cli examples/functions_to_objects_example.py --rules functions_to_objects
"""

from dataclasses import dataclass

# =============================================================================
# BAD: Functions with many parameters
# =============================================================================


def create_user_bad(
    name: str,
    email: str,
    age: int,
    address: str,
    phone: str,
    role: str,
) -> dict:
    """BAD: Too many parameters - this should be a class."""
    return {
        "name": name,
        "email": email,
        "age": age,
        "address": address,
        "phone": phone,
        "role": role,
    }


def send_email_bad(
    to: str,
    subject: str,
    body: str,
    cc: str | None,
    bcc: str | None,
    reply_to: str,
    attachments: list,
) -> bool:
    """BAD: Too many parameters - consider an EmailMessage class."""
    print(f"Sending to {to}: {subject}")
    return True


# =============================================================================
# BAD: Related functions that should be a class
# =============================================================================


def user_create(name: str, email: str) -> dict:
    """BAD: Part of a group of related functions."""
    return {"name": name, "email": email, "id": 1}


def user_update(user: dict, **kwargs) -> dict:
    """BAD: Part of a group of related functions."""
    user.update(kwargs)
    return user


def user_delete(user: dict) -> bool:
    """BAD: Part of a group of related functions."""
    print(f"Deleting user {user['id']}")
    return True


def user_validate(user: dict) -> bool:
    """BAD: Part of a group of related functions."""
    return "name" in user and "email" in user


def user_serialize(user: dict) -> str:
    """BAD: Part of a group of related functions."""
    return str(user)


# =============================================================================
# BAD: Functions returning dictionaries
# =============================================================================


def get_user_stats_bad() -> dict:
    """BAD: Returns a dict with fixed keys - should be a dataclass."""
    return {
        "total_users": 100,
        "active_users": 80,
        "new_users_today": 5,
        "average_age": 32.5,
    }


def calculate_order_totals_bad(items: list) -> dict:
    """BAD: Returns a dict - should be a typed object."""
    subtotal = sum(item["price"] for item in items)
    tax = subtotal * 0.1
    return {
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
        "item_count": len(items),
    }


# =============================================================================
# GOOD: Using classes instead of functions with many parameters
# =============================================================================


@dataclass
class User:
    """GOOD: Parameters become attributes."""

    name: str
    email: str
    age: int
    address: str
    phone: str
    role: str


@dataclass
class EmailMessage:
    """GOOD: Email configuration as a class."""

    to: str
    subject: str
    body: str
    cc: str | None = None
    bcc: str | None = None
    reply_to: str | None = None
    attachments: list = None

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []

    def send(self) -> bool:
        """GOOD: Behavior is part of the object."""
        print(f"Sending to {self.to}: {self.subject}")
        return True


# =============================================================================
# GOOD: Related functions become a class
# =============================================================================


class UserService:
    """GOOD: Related functions become methods of a class."""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id = 1

    def create(self, name: str, email: str, **kwargs) -> User:
        user = User(name=name, email=email, **kwargs)
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def update(self, user_id: int, **kwargs) -> User:
        user = self._users[user_id]
        for key, value in kwargs.items():
            setattr(user, key, value)
        return user

    def delete(self, user_id: int) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    def validate(self, user: User) -> bool:
        return bool(user.name and user.email)


# =============================================================================
# GOOD: Dataclasses instead of dicts
# =============================================================================


@dataclass
class UserStats:
    """GOOD: Typed object instead of dict."""

    total_users: int
    active_users: int
    new_users_today: int
    average_age: float


@dataclass
class OrderTotals:
    """GOOD: Typed object instead of dict."""

    subtotal: float
    tax: float
    total: float
    item_count: int


def get_user_stats_good() -> UserStats:
    """GOOD: Returns a typed object."""
    return UserStats(
        total_users=100,
        active_users=80,
        new_users_today=5,
        average_age=32.5,
    )


def calculate_order_totals_good(items: list) -> OrderTotals:
    """GOOD: Returns a typed object."""
    subtotal = sum(item["price"] for item in items)
    tax = subtotal * 0.1
    return OrderTotals(
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        item_count=len(items),
    )
