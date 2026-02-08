"""
Example: Type Code Rule

This file demonstrates type code conditionals that should be replaced by polymorphism.
The rule detects if/elif chains checking constants, enums, or type attributes.

References:
- https://refactoring.guru/replace-type-code-with-state-strategy
- https://refactoring.guru/replace-type-code-with-subclasses

Run: uv run python -m oop_analyzer.cli examples/type_code_example.py --rules type_code
"""

from abc import ABC, abstractmethod
from enum import Enum

# =============================================================================
# BAD: Type code with constants
# =============================================================================

EUROPEAN = 1
AFRICAN = 2
NORWEGIAN_BLUE = 3


class BirdBad:
    """BAD: Uses type code to determine behavior."""

    def __init__(self, bird_type: int):
        self.type = bird_type
        self.base_speed = 10
        self.load_factor = 2
        self.number_of_coconuts = 0
        self.voltage = 0
        self.is_nailed = False

    def get_speed(self) -> float:
        """BAD: Type code conditional - classic refactoring candidate."""
        if self.type == EUROPEAN:
            return self.base_speed
        elif self.type == AFRICAN:
            return self.base_speed - self.load_factor * self.number_of_coconuts
        elif self.type == NORWEGIAN_BLUE:
            return 0 if self.is_nailed else self.base_speed * self.voltage
        else:
            raise ValueError("Unknown bird type")

    def get_cry(self) -> str:
        """BAD: Another method with the same type code pattern."""
        if self.type == EUROPEAN:
            return "Squawk!"
        elif self.type == AFRICAN:
            return "Screech!"
        elif self.type == NORWEGIAN_BLUE:
            return "" if self.is_nailed else "Beautiful plumage!"
        else:
            return "Unknown"


# =============================================================================
# BAD: Type code with enum
# =============================================================================


class OrderStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderBad:
    """BAD: Uses enum as type code."""

    def __init__(self, status: OrderStatus):
        self.status = status

    def get_next_action(self) -> str:
        """BAD: Enum-based type code conditional."""
        if self.status == OrderStatus.PENDING:
            return "Process payment"
        elif self.status == OrderStatus.PROCESSING:
            return "Ship order"
        elif self.status == OrderStatus.SHIPPED:
            return "Track delivery"
        elif self.status == OrderStatus.DELIVERED:
            return "Request review"
        elif self.status == OrderStatus.CANCELLED:
            return "Process refund"
        else:
            return "Unknown"

    def can_cancel(self) -> bool:
        """BAD: Another type code conditional."""
        if self.status == OrderStatus.PENDING or self.status == OrderStatus.PROCESSING:
            return True
        elif (
            self.status == OrderStatus.SHIPPED
            or self.status == OrderStatus.DELIVERED
            or self.status == OrderStatus.CANCELLED
        ):
            return False
        return False


# =============================================================================
# GOOD: Replace Type Code with Subclasses
# =============================================================================


class Bird(ABC):
    """GOOD: Abstract base class - each type becomes a subclass."""

    def __init__(self):
        self._base_speed = 10

    @abstractmethod
    def get_speed(self) -> float:
        pass

    @abstractmethod
    def get_cry(self) -> str:
        pass


class EuropeanBird(Bird):
    """GOOD: Subclass for European birds."""

    def get_speed(self) -> float:
        return self._base_speed

    def get_cry(self) -> str:
        return "Squawk!"


class AfricanBird(Bird):
    """GOOD: Subclass for African birds."""

    def __init__(self, number_of_coconuts: int = 0):
        super().__init__()
        self._load_factor = 2
        self._number_of_coconuts = number_of_coconuts

    def get_speed(self) -> float:
        return self._base_speed - self._load_factor * self._number_of_coconuts

    def get_cry(self) -> str:
        return "Screech!"


class NorwegianBlueBird(Bird):
    """GOOD: Subclass for Norwegian Blue birds."""

    def __init__(self, voltage: float = 0, is_nailed: bool = False):
        super().__init__()
        self._voltage = voltage
        self._is_nailed = is_nailed

    def get_speed(self) -> float:
        return 0 if self._is_nailed else self._base_speed * self._voltage

    def get_cry(self) -> str:
        return "" if self._is_nailed else "Beautiful plumage!"


# =============================================================================
# GOOD: Replace Type Code with State Pattern
# =============================================================================


class OrderState(ABC):
    """GOOD: State pattern - each status becomes a state class."""

    @abstractmethod
    def get_next_action(self) -> str:
        pass

    @abstractmethod
    def can_cancel(self) -> bool:
        pass


class PendingState(OrderState):
    def get_next_action(self) -> str:
        return "Process payment"

    def can_cancel(self) -> bool:
        return True


class ProcessingState(OrderState):
    def get_next_action(self) -> str:
        return "Ship order"

    def can_cancel(self) -> bool:
        return True


class ShippedState(OrderState):
    def get_next_action(self) -> str:
        return "Track delivery"

    def can_cancel(self) -> bool:
        return False


class DeliveredState(OrderState):
    def get_next_action(self) -> str:
        return "Request review"

    def can_cancel(self) -> bool:
        return False


class CancelledState(OrderState):
    def get_next_action(self) -> str:
        return "Process refund"

    def can_cancel(self) -> bool:
        return False


class OrderGood:
    """GOOD: Order delegates to its state."""

    def __init__(self, state: OrderState):
        self._state = state

    def get_next_action(self) -> str:
        return self._state.get_next_action()

    def can_cancel(self) -> bool:
        return self._state.can_cancel()

    def transition_to(self, state: OrderState) -> None:
        self._state = state


# Usage
def demo():
    # BAD way
    bad_bird = BirdBad(EUROPEAN)
    print(bad_bird.get_speed())

    # GOOD way
    good_bird = EuropeanBird()
    print(good_bird.get_speed())

    # BAD way
    bad_order = OrderBad(OrderStatus.PENDING)
    print(bad_order.get_next_action())

    # GOOD way
    good_order = OrderGood(PendingState())
    print(good_order.get_next_action())
    good_order.transition_to(ShippedState())
    print(good_order.get_next_action())
