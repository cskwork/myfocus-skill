"""myfocus-skill scanner registry.

Each scanner module imports `register` and decorates its scan function.
Importing this package does not import the scanners — `collect.py` imports
the bundled modules explicitly so the registry is populated.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict


@dataclass(frozen=True)
class ScannerSpec:
    name: str
    fn: Callable
    default_base: Path


REGISTRY: Dict[str, ScannerSpec] = {}


def register(name: str, *, default_base: Path):
    """Decorator: register a scanner function under `name`."""
    def decorator(fn):
        REGISTRY[name] = ScannerSpec(name=name, fn=fn, default_base=default_base)
        return fn
    return decorator
