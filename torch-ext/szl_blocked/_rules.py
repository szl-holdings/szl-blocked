# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""A few honest, composable HARD security rules for the deny-by-default policy.

These are illustrative rules, not a complete security model. Each is a callable
(request_ctx) -> PolicyResult that answers ALLOW, DENY or ABSTAIN. They are HARD:
a single DENY dominates and cannot be overridden by the advisory Λ layer. A rule
that does not fire ABSTAINS and grants nothing. The deny-by-default policy treats
absence of an explicit ALLOW as a DENY, so allow rules ADD permission narrowly
and deny rules only ever take it away.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from ._gate import ABSTAIN, ALLOW, DENY, PolicyResult, SecurityPolicy


def allow_if_capability(required: str) -> SecurityPolicy:
    """ALLOW only when ``request['capabilities']`` contains ``required``.

    Returns an explicit hard ALLOW when the capability is present; otherwise
    ABSTAINS (code ``ABSTAIN_NO_CAPABILITY``) so the deny-by-default policy
    falls through to DENY_DEFAULT rather than a hard rule-deny, unless another
    rule explicitly allows. Several of these rules therefore mean "any of" the
    capabilities, not "all of" them.
    """

    def _rule(ctx: Dict[str, Any]) -> PolicyResult:
        caps = ctx.get("capabilities") or []
        if required in caps:
            return PolicyResult(
                ALLOW, "capability granted: " + required, code="OK"
            )
        return PolicyResult(
            ABSTAIN,
            "missing required capability: " + required,
            code="ABSTAIN_NO_CAPABILITY",
            detail={"required": required, "have": list(caps)},
        )

    return _rule


def deny_if_flag(flag: str, *, code: str = "DENY_RULE") -> SecurityPolicy:
    """HARD DENY when ``request[flag]`` is truthy (e.g. ``'exfiltration'``).

    A matched deny dominates immediately and cannot be overridden by advisory Λ.
    When the flag is not set the rule ABSTAINS; a deny rule never grants.
    """

    def _rule(ctx: Dict[str, Any]) -> PolicyResult:
        if ctx.get(flag):
            return PolicyResult(
                DENY,
                "hard-deny flag set: " + flag,
                code=code + ":" + flag,
                detail={"flag": flag},
            )
        # Not denied by this rule; abstain (let other rules speak / default).
        return PolicyResult(
            ABSTAIN, "flag not set: " + flag, code="ABSTAIN"
        )

    return _rule


def deny_if_action_in(blocklist: Iterable[str]) -> SecurityPolicy:
    """HARD DENY when ``request['action']`` is in a blocklist of forbidden ops.

    Any other action ABSTAINS; a deny rule never grants.
    """
    blocked = set(blocklist)

    def _rule(ctx: Dict[str, Any]) -> PolicyResult:
        action = ctx.get("action")
        if action in blocked:
            return PolicyResult(
                DENY,
                "hard-deny: action in blocklist: " + str(action),
                code="DENY_RULE:blocklist",
                detail={"action": action},
            )
        return PolicyResult(ABSTAIN, "action not blocklisted", code="ABSTAIN")

    return _rule


__all__ = [
    "allow_if_capability",
    "deny_if_flag",
    "deny_if_action_in",
]
