"""
Example: Encapsulation Rule (Tell Don't Ask)

This file demonstrates violations of the encapsulation principle.
The rule detects direct property access on objects - we should "tell"
objects what to do, not "ask" them for data.

Run: uv run python -m oop_analyzer.cli examples/encapsulation_example.py --rules encapsulation
"""


# =============================================================================
# BAD: Direct property access (Tell Don't Ask violations)
# =============================================================================


class User:
    def __init__(self, name: str, age: int, email: str):
        self.name = name
        self.age = age
        self.email = email


def process_user_bad(user: User) -> None:
    """BAD: Asking the object for data and making decisions externally."""
    # Violation: Direct property access
    print(f"Hello, {user.name}")

    # Violation: Asking for data to make a decision
    if user.age >= 18:
        print("User is an adult")

    # Violation: Chained property access
    print(user.email.upper())


def calculate_discount_bad(user: User, base_price: float) -> float:
    """BAD: Logic that should be in the User class."""
    # Violation: Accessing properties to calculate something
    if user.age < 18:
        return base_price * 0.5  # 50% discount for minors
    elif user.age >= 65:
        return base_price * 0.8  # 20% discount for seniors
    return base_price


# =============================================================================
# GOOD: Using methods (Tell Don't Ask)
# =============================================================================


class BetterUser:
    def __init__(self, name: str, age: int, email: str):
        self._name = name
        self._age = age
        self._email = email

    def greet(self) -> None:
        """Tell the object to greet - it knows how."""
        print(f"Hello, {self._name}")

    def is_adult(self) -> bool:
        """Ask about behavior, not raw data."""
        return self._age >= 18

    def is_senior(self) -> bool:
        return self._age >= 65

    def is_minor(self) -> bool:
        return self._age < 18

    def calculate_discount(self, base_price: float) -> float:
        """The object knows how to calculate its own discount."""
        if self.is_minor():
            return base_price * 0.5
        elif self.is_senior():
            return base_price * 0.8
        return base_price

    def get_formatted_email(self) -> str:
        """If we need formatted data, ask the object to format it."""
        return self._email.upper()


def process_user_good(user: BetterUser) -> None:
    """GOOD: Telling the object what to do."""
    user.greet()

    if user.is_adult():
        print("User is an adult")


def calculate_discount_good(user: BetterUser, base_price: float) -> float:
    """GOOD: Delegating to the object."""
    return user.calculate_discount(base_price)


# =============================================================================
# BEST: Even better - polymorphism instead of conditionals
# =============================================================================

from abc import ABC, abstractmethod


class Customer(ABC):
    def __init__(self, name: str, email: str):
        self._name = name
        self._email = email

    def greet(self) -> None:
        print(f"Hello, {self._name}")

    @abstractmethod
    def calculate_discount(self, base_price: float) -> float:
        pass


class RegularCustomer(Customer):
    def calculate_discount(self, base_price: float) -> float:
        return base_price  # No discount


class MinorCustomer(Customer):
    def calculate_discount(self, base_price: float) -> float:
        return base_price * 0.5  # 50% discount


class SeniorCustomer(Customer):
    def calculate_discount(self, base_price: float) -> float:
        return base_price * 0.8  # 20% discount


def process_order(customer: Customer, base_price: float) -> float:
    """BEST: No conditionals, no property access - pure polymorphism."""
    customer.greet()
    return customer.calculate_discount(base_price)
