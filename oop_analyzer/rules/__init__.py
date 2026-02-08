"""
Rules module for OOP Analyzer.

Contains all the analysis rules for checking OOP best practices.
"""

from .base import BaseRule, RuleResult, RuleViolation
from .boolean_flag import BooleanFlagRule
from .coupling import CouplingRule
from .dictionary_usage import DictionaryUsageRule
from .encapsulation import EncapsulationRule
from .functions_to_objects import FunctionsToObjectsRule
from .null_object import NullObjectRule
from .polymorphism import PolymorphismRule
from .reference_exposure import ReferenceExposureRule
from .type_code import TypeCodeRule

__all__ = [
    "BaseRule",
    "RuleViolation",
    "RuleResult",
    "EncapsulationRule",
    "CouplingRule",
    "NullObjectRule",
    "PolymorphismRule",
    "FunctionsToObjectsRule",
    "TypeCodeRule",
    "ReferenceExposureRule",
    "DictionaryUsageRule",
    "BooleanFlagRule",
]

# Registry of all available rules
RULE_REGISTRY: dict[str, type["BaseRule"]] = {
    "encapsulation": EncapsulationRule,
    "coupling": CouplingRule,
    "null_object": NullObjectRule,
    "polymorphism": PolymorphismRule,
    "functions_to_objects": FunctionsToObjectsRule,
    "type_code": TypeCodeRule,
    "reference_exposure": ReferenceExposureRule,
    "dictionary_usage": DictionaryUsageRule,
    "boolean_flag": BooleanFlagRule,
}


def get_rule(rule_name: str) -> type["BaseRule"]:
    """Get a rule class by name."""
    if rule_name not in RULE_REGISTRY:
        raise ValueError(f"Unknown rule: {rule_name}")
    return RULE_REGISTRY[rule_name]


def get_all_rules() -> dict[str, type["BaseRule"]]:
    """Get all registered rules."""
    return RULE_REGISTRY.copy()
