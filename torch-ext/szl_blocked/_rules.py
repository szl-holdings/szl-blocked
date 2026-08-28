# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""A few honest, composable HARD security rules for the deny-by-default policy.

These are illustrative rules, not a complete security model. Each is a callable
(request_ctx) -> PolicyResult. They are HARD: a single DENY dominates and cannot
be overridden by the advisory Λ layer. The deny-by-default policy treats absence
of an explicit ALLOW as a DENY, so these rules ADD permission narrowly.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from ._gate import PolicyResult, SecurityPolicy


def allow_if_capability(required: str) -> SecurityPolicy:
    """ALLOW only when ``request['capabilities']`` contains ``required``.

    Returns allow=True (an explicit hard ALLOW) when the capability is present;
    otherwise abstains by returning allow=False with ABSTAIN code so the
    deny-by-default policy falls through to DENY_DEFAULT rather than a hard
    rule-deny. (deny-by-default needs at least one explicit ALLOW to permit.)
    """

    def _rule(ctx: Dict[str, Any]) -> PolicyResult:
        caps = ctx.get("capabilities") or []
        if required in caps:
            return PolicyResult(
                True, "capability granted: " + required, code="OK"
            )
        return PolicyResult(
            False,
            "missing required capability: " + required,
            code="ABSTAIN_NO_CAPABILITY",
            detail={"required": required, "have": list(caps)},
        )

    return _rule


def deny_if_flag(flag: str, *, code: str = "DENY_RULE") -> SecurityPolicy:
    """HARD DENY when ``request[flag]`` is truthy (e.g. ``'exfiltration'``).

    A matched deny dominates immediately and cannot be overridden by advisory Λ.
    """

    def _rule(ctx: Dict[str, Any]) -> PolicyResult:
        if ctx.get(flag):
            return PolicyResult(
                False,
                "hard-deny flag set: " + flag,
                code=code + ":" + flag,
                detail={"flag": flag},
            )
        # Not denied by this rule; abstain (let other rules speak / default).
        return PolicyResult(
            True, "flag not set: " + flag, code="OK"
        )

    return _rule


def deny_if_action_in(blocklist: Iterable[str]) -> SecurityPolicy:
    """HARD DENY when ``request['action']`` is in a blocklist of forbidden ops."""
    blocked = set(blocklist)

    def _rule(ctx: Dict[str, Any]) -> PolicyResult:
        action = ctx.get("action")
        if action in blocked:
            return PolicyResult(
                False,
                "hard-deny: action in blocklist: " + str(action),
                code="DENY_RULE:blocklist",
                detail={"action": action},
            )
        return PolicyResult(True, "action not blocklisted", code="OK")

    return _rule


__all__ = [
    "allow_if_capability",
    "deny_if_flag",
    "deny_if_action_in",
]
