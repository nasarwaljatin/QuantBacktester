# backend/app/engine/strategy_sandbox.py
"""Safe execution sandbox for user-submitted strategy code."""

import ast
import backtrader as bt
import numpy as np
import pandas as pd


# Default strategy template shown to users in the editor
DEFAULT_STRATEGY_CODE = '''class UserStrategy(bt.Strategy):
    params = dict(fast=3, slow=30)

    def __init__(self):
        self.fast_ma = bt.ind.EMA(period=self.p.fast)
        self.slow_ma = bt.ind.EMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
'''

# Restricted builtins — block dangerous operations
SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool,
    "dict": dict, "enumerate": enumerate, "filter": filter,
    "float": float, "frozenset": frozenset, "getattr": getattr,
    "hasattr": hasattr, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "len": len, "list": list,
    "map": map, "max": max, "min": min, "object": object,
    "pow": pow, "print": print, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set,
    "slice": slice, "sorted": sorted, "str": str,
    "sum": sum, "super": super, "tuple": tuple, "type": type,
    "zip": zip, "True": True, "False": False, "None": None,
    "__build_class__": __build_class__,
}

# Blocked AST node types for security
BLOCKED_NODE_TYPES = (
    ast.Import,
    ast.ImportFrom,
)

BLOCKED_FUNCTION_NAMES = {
    "open", "exec", "eval", "__import__", "compile",
    "globals", "locals", "vars", "dir", "breakpoint",
    "input", "exit", "quit",
}


def _validate_ast(code: str) -> None:
    """Validate the AST of user code for security issues.

    Args:
        code: Python source code string.

    Raises:
        ValueError: If dangerous constructs are detected.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in strategy code: {e}")

    for node in ast.walk(tree):
        # Block import statements
        if isinstance(node, BLOCKED_NODE_TYPES):
            raise ValueError(
                "Import statements are not allowed in strategy code. "
                "backtrader (bt), numpy (np), and pandas (pd) are pre-imported."
            )
        # Block dangerous function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_FUNCTION_NAMES:
                    raise ValueError(
                        f"Function '{node.func.id}' is not allowed in strategy code."
                    )
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in BLOCKED_FUNCTION_NAMES:
                    raise ValueError(
                        f"Method '{node.func.attr}' is not allowed in strategy code."
                    )

    # Verify UserStrategy class exists
    class_names = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    ]
    if "UserStrategy" not in class_names:
        raise ValueError(
            "Strategy code must define a class called 'UserStrategy' "
            "that extends bt.Strategy."
        )


def compile_user_strategy(code: str) -> type:
    """Safely compile and extract a UserStrategy class from user code.

    Args:
        code: Python source code defining a UserStrategy(bt.Strategy) class.

    Returns:
        The UserStrategy class ready for use with Backtrader.

    Raises:
        ValueError: If code is invalid, unsafe, or missing UserStrategy.
    """
    _validate_ast(code)

    # Create restricted execution namespace
    namespace = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__main__",
        "bt": bt,
        "np": np,
        "pd": pd,
    }

    try:
        exec(code, namespace)
    except Exception as e:
        raise ValueError(f"Error executing strategy code: {e}")

    strategy_class = namespace.get("UserStrategy")
    if strategy_class is None:
        raise ValueError("Strategy code must define a 'UserStrategy' class.")

    if not (isinstance(strategy_class, type) and issubclass(strategy_class, bt.Strategy)):
        raise ValueError("UserStrategy must be a class that extends bt.Strategy.")

    # Inject timeout wrappers to prevent infinite loops
    import time
    import threading
    from functools import wraps

    original_init = strategy_class.__init__
    original_next = strategy_class.next

    @wraps(original_init)
    def wrapped_init(self, *args, **kwargs):
        self._qbt_start_time = time.time()
        self._qbt_timeout = 5.0
        return original_init(self, *args, **kwargs)

    @wraps(original_next)
    def wrapped_next(self):
        if hasattr(self, "_qbt_start_time"):
            elapsed = time.time() - self._qbt_start_time
            if elapsed > self._qbt_timeout:
                raise TimeoutError("Strategy execution exceeded CPU time limit (5 seconds).")
        return original_next(self)

    strategy_class.__init__ = wrapped_init
    strategy_class.next = wrapped_next

    return strategy_class


def run_cerebro_with_timeout(cerebro, timeout: float = 30.0):
    """Run cerebro.run() with a hard timeout using a daemon thread.

    Args:
        cerebro: Configured Backtrader Cerebro instance.
        timeout: Maximum seconds to allow execution.

    Returns:
        Results from cerebro.run().

    Raises:
        TimeoutError: If execution exceeds the timeout.
    """
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(cerebro.run)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(
                f"Strategy execution exceeded CPU time limit ({timeout} seconds)."
            )

