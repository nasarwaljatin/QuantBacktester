# backend/tests/conftest.py
"""Test defaults: a local SQLite database and in-process (non-Celery) execution.

Uses setdefault, so an explicitly configured DATABASE_URL / USE_CELERY still wins.
Must run before app.config is imported, which pytest guarantees for conftest.py.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_quantbacktester.db")
os.environ.setdefault("USE_CELERY", "false")
