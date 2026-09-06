"""Honest verification availability and source/test fallback advice."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationSupport:
    available: bool
    reason: str | None
    fallback: str


def graph_verify_support() -> VerificationSupport:
    """`verify` executes a shell command; Windows requires an available POSIX sh."""
    if os.name == "nt" and shutil.which("sh") is None:
        return VerificationSupport(False, "POSIX shell (sh) is unavailable on this Windows environment.", "Run the recommended test command directly, then inspect the cited source.")
    return VerificationSupport(True, None, "Use a targeted test command and inspect the cited source if results are inconclusive.")
