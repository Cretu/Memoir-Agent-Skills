"""Adapter registry. Auto-pick order: OpenClaw > Claude Code > generic."""

from __future__ import annotations

from ..contract import Adapter
from .claude_code import ClaudeCodeAdapter
from .generic import GenericCronAdapter
from .openclaw import OpenClawAdapter

ADAPTERS: dict[str, type[Adapter]] = {
    a.id: a for a in (OpenClawAdapter, ClaudeCodeAdapter, GenericCronAdapter)
}


def get_adapter(adapter_id: str) -> Adapter:
    try:
        return ADAPTERS[adapter_id]()
    except KeyError:
        raise SystemExit(
            f"unknown adapter {adapter_id!r}; available: {', '.join(ADAPTERS)}"
        ) from None


def auto_pick() -> Adapter:
    for cls in ADAPTERS.values():
        if cls is GenericCronAdapter:
            continue
        if cls.detect().available:
            return cls()
    return GenericCronAdapter()
