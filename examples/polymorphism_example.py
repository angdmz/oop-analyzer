"""
Example: Polymorphism Rule

This file demonstrates if/elif chains that could be replaced by polymorphism.
The rule detects isinstance() checks and type-based conditionals.

Run: uv run python -m oop_analyzer.cli examples/polymorphism_example.py --rules polymorphism
"""

from abc import ABC, abstractmethod

# =============================================================================
# BAD: Long if/elif chains and isinstance() checks
# =============================================================================


class Dog:
    def __init__(self, name: str):
        self.name = name


class Cat:
    def __init__(self, name: str):
        self.name = name


class Bird:
    def __init__(self, name: str):
        self.name = name


def make_sound_bad(animal) -> str:
    """BAD: isinstance() checks - classic polymorphism candidate."""
    if isinstance(animal, Dog):
        return "Woof!"
    elif isinstance(animal, Cat):
        return "Meow!"
    elif isinstance(animal, Bird):
        return "Chirp!"
    else:
        return "Unknown sound"


def calculate_area_bad(shape: dict) -> float:
    """BAD: Checking a 'type' attribute."""
    if shape["type"] == "circle":
        return 3.14159 * shape["radius"] ** 2
    elif shape["type"] == "rectangle":
        return shape["width"] * shape["height"]
    elif shape["type"] == "triangle":
        return 0.5 * shape["base"] * shape["height"]
    else:
        raise ValueError(f"Unknown shape: {shape['type']}")


def process_payment_bad(payment: dict) -> str:
    """BAD: Long if/elif chain checking the same variable."""
    method = payment["method"]

    if method == "credit_card":
        return f"Processing credit card: {payment['card_number']}"
    elif method == "paypal":
        return f"Processing PayPal: {payment['email']}"
    elif method == "bank_transfer":
        return f"Processing bank transfer: {payment['account']}"
    elif method == "crypto":
        return f"Processing crypto: {payment['wallet']}"
    else:
        raise ValueError(f"Unknown payment method: {method}")


def get_tax_rate_bad(country: str) -> float:
    """BAD: Long if/elif chain."""
    if country == "US":
        return 0.08
    elif country == "UK":
        return 0.20
    elif country == "DE":
        return 0.19
    elif country == "FR":
        return 0.20
    elif country == "JP":
        return 0.10
    else:
        return 0.0


# =============================================================================
# GOOD: Using polymorphism
# =============================================================================


class Animal(ABC):
    def __init__(self, name: str):
        self._name = name

    @abstractmethod
    def make_sound(self) -> str:
        pass


class DogGood(Animal):
    def make_sound(self) -> str:
        return "Woof!"


class CatGood(Animal):
    def make_sound(self) -> str:
        return "Meow!"


class BirdGood(Animal):
    def make_sound(self) -> str:
        return "Chirp!"


def make_sound_good(animal: Animal) -> str:
    """GOOD: Just call the method - polymorphism handles the rest."""
    return animal.make_sound()


# Shapes with polymorphism
class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        pass


class Circle(Shape):
    def __init__(self, radius: float):
        self._radius = radius

    def area(self) -> float:
        return 3.14159 * self._radius**2


class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self._width = width
        self._height = height

    def area(self) -> float:
        return self._width * self._height


class Triangle(Shape):
    def __init__(self, base: float, height: float):
        self._base = base
        self._height = height

    def area(self) -> float:
        return 0.5 * self._base * self._height


def calculate_area_good(shape: Shape) -> float:
    """GOOD: No conditionals needed."""
    return shape.area()


# Payment processing with Strategy pattern
class PaymentProcessor(ABC):
    @abstractmethod
    def process(self) -> str:
        pass


class CreditCardProcessor(PaymentProcessor):
    def __init__(self, card_number: str):
        self._card_number = card_number

    def process(self) -> str:
        return f"Processing credit card: {self._card_number}"


class PayPalProcessor(PaymentProcessor):
    def __init__(self, email: str):
        self._email = email

    def process(self) -> str:
        return f"Processing PayPal: {self._email}"


class BankTransferProcessor(PaymentProcessor):
    def __init__(self, account: str):
        self._account = account

    def process(self) -> str:
        return f"Processing bank transfer: {self._account}"


def process_payment_good(processor: PaymentProcessor) -> str:
    """GOOD: Strategy pattern - no conditionals."""
    return processor.process()


# Tax rates with a registry (alternative to polymorphism for simple cases)
class TaxRegistry:
    _rates = {
        "US": 0.08,
        "UK": 0.20,
        "DE": 0.19,
        "FR": 0.20,
        "JP": 0.10,
    }
    _default = 0.0

    @classmethod
    def get_rate(cls, country: str) -> float:
        """GOOD: Dictionary lookup instead of if/elif chain."""
        return cls._rates.get(country, cls._default)


def get_tax_rate_good(country: str) -> float:
    """GOOD: Delegate to registry."""
    return TaxRegistry.get_rate(country)
