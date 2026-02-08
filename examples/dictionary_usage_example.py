"""
Example: Dictionary Usage Rule

This file demonstrates dictionary usage that should be replaced by proper objects.
Dictionaries are acceptable at API boundaries, but abstraction layers should use typed objects.

Run: uv run python -m oop_analyzer.cli examples/dictionary_usage_example.py --rules dictionary_usage
"""

import json
from dataclasses import dataclass

# =============================================================================
# BAD: Using dictionaries for structured data
# =============================================================================


def create_user_bad(name: str, email: str, age: int) -> dict:
    """BAD: Returns a dict with fixed keys."""
    return {
        "name": name,
        "email": email,
        "age": age,
        "created_at": "2024-01-01",
    }


def process_user_bad(user: dict) -> None:
    """BAD: Takes a dict parameter - no type safety."""
    # Easy to typo keys
    print(f"Hello, {user['name']}")
    print(f"Email: {user['email']}")
    # What if someone passes {"nome": "John"}? Runtime error!


def calculate_order_bad(items: list) -> dict:
    """BAD: Returns a dict for structured data."""
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    tax = subtotal * 0.1
    shipping = 5.0 if subtotal < 50 else 0.0

    return {
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": subtotal + tax + shipping,
    }


def get_config_bad() -> dict:
    """BAD: Config as dict - no validation, no defaults."""
    return {
        "debug": True,
        "max_retries": 3,
        "timeout": 30,
        "base_url": "https://api.example.com",
    }


class ServiceBad:
    """BAD: Passes dicts between methods."""

    def fetch_user(self, user_id: int) -> dict:
        return {"id": user_id, "name": "John", "email": "john@example.com"}

    def update_user(self, user: dict, updates: dict) -> dict:
        """BAD: Both parameters are untyped dicts."""
        user.update(updates)
        return user

    def validate_user(self, user: dict) -> bool:
        """BAD: Must remember all required keys."""
        return "name" in user and "email" in user


# =============================================================================
# ACCEPTABLE: Dictionaries at API boundaries
# =============================================================================


def parse_api_response(response_text: str) -> dict:
    """ACCEPTABLE: Parsing external API response - this is the boundary."""
    return json.loads(response_text)


def to_json(obj) -> dict:
    """ACCEPTABLE: Serializing to JSON for external API."""
    return {"data": str(obj)}


class ApiClient:
    """ACCEPTABLE: API client deals with raw dicts at the boundary."""

    def get_response(self, endpoint: str) -> dict:
        """ACCEPTABLE: Raw API response."""
        return {"status": "ok", "data": []}

    def post_request(self, endpoint: str, payload: dict) -> dict:
        """ACCEPTABLE: Sending to external API."""
        return {"success": True}


# =============================================================================
# GOOD: Using dataclasses and typed objects
# =============================================================================


@dataclass
class User:
    """GOOD: Typed, validated, IDE-friendly."""

    name: str
    email: str
    age: int
    created_at: str = "2024-01-01"

    def __post_init__(self):
        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email: {self.email}")
        if self.age < 0:
            raise ValueError(f"Invalid age: {self.age}")


@dataclass
class OrderSummary:
    """GOOD: Typed order summary."""

    subtotal: float
    tax: float
    shipping: float
    total: float

    @classmethod
    def calculate(cls, items: list["OrderItem"]) -> "OrderSummary":
        subtotal = sum(item.total for item in items)
        tax = subtotal * 0.1
        shipping = 5.0 if subtotal < 50 else 0.0
        return cls(
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            total=subtotal + tax + shipping,
        )


@dataclass
class OrderItem:
    """GOOD: Typed order item."""

    name: str
    price: float
    quantity: int

    @property
    def total(self) -> float:
        return self.price * self.quantity


@dataclass
class Config:
    """GOOD: Typed config with defaults and validation."""

    debug: bool = False
    max_retries: int = 3
    timeout: int = 30
    base_url: str = "https://api.example.com"

    def __post_init__(self):
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


def create_user_good(name: str, email: str, age: int) -> User:
    """GOOD: Returns a typed object."""
    return User(name=name, email=email, age=age)


def process_user_good(user: User) -> None:
    """GOOD: Takes a typed parameter - IDE autocomplete, type checking."""
    print(f"Hello, {user.name}")
    print(f"Email: {user.email}")
    # Typos are caught by the type checker!


class ServiceGood:
    """GOOD: Uses typed objects between methods."""

    def fetch_user(self, user_id: int) -> User:
        return User(id=user_id, name="John", email="john@example.com", age=30)

    def update_user(self, user: User, name: str | None = None, email: str | None = None) -> User:
        """GOOD: Explicit parameters instead of **kwargs dict."""
        return User(
            name=name or user.name,
            email=email or user.email,
            age=user.age,
        )

    def validate_user(self, user: User) -> bool:
        """GOOD: Validation is built into the dataclass."""
        return True  # If we have a User, it's already valid


# =============================================================================
# GOOD: Converting at the boundary
# =============================================================================


class UserRepository:
    """GOOD: Converts dicts to objects at the boundary."""

    def __init__(self, api_client: ApiClient):
        self._api = api_client

    def get_user(self, user_id: int) -> User:
        """GOOD: Converts API dict to typed object immediately."""
        response = self._api.get_response(f"/users/{user_id}")
        data = response["data"]

        # Convert at the boundary
        return User(
            name=data["name"],
            email=data["email"],
            age=data["age"],
        )

    def save_user(self, user: User) -> bool:
        """GOOD: Converts typed object to dict only for the API."""
        payload = {
            "name": user.name,
            "email": user.email,
            "age": user.age,
        }
        response = self._api.post_request("/users", payload)
        return response.get("success", False)


# =============================================================================
# Demonstration
# =============================================================================


def demonstrate():
    # BAD: Dict-based approach
    user_dict = create_user_bad("John", "john@example.com", 30)
    process_user_bad(user_dict)

    # What if we typo a key?
    user_dict["emial"] = "typo@example.com"  # No error until runtime!

    # GOOD: Object-based approach
    user_obj = create_user_good("John", "john@example.com", 30)
    process_user_good(user_obj)

    # Typos are caught by the type checker
    # user_obj.emial = "typo@example.com"  # AttributeError!
