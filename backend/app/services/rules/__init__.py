"""Rule engine. Importing the package registers every rule module in this folder."""

import importlib
import pkgutil

for _module in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_module.name}")

from app.services.rules.base import RULES, Rule, RuleResult, Status, register  # noqa: E402
from app.services.rules.engine import ENGINE_VERSION, RuleRun, run_rules  # noqa: E402

__all__ = [
    "ENGINE_VERSION",
    "RULES",
    "Rule",
    "RuleResult",
    "RuleRun",
    "Status",
    "register",
    "run_rules",
]
