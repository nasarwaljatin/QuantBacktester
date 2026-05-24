# backend/app/__init__.py
"""QuantBacktester backend application package."""

import collections
import collections.abc

# Monkey-patch collections to fix Backtrader compatibility on Python 3.10+
if not hasattr(collections, "Iterable"):
    collections.Iterable = collections.abc.Iterable
if not hasattr(collections, "Callable"):
    collections.Callable = collections.abc.Callable

