# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""honest-BLOCKED as a FIRST-CLASS governed-kernel state.

THE FRONTIER GAP THIS CLOSES
----------------------------
Every governed SZL kernel — and every leaderboard kernel on the Hub — optimizes
throughput and ALWAYS returns a tensor. An advisory Λ gate records a "pass/fail"
but never *refuses*: the math runs regardless (see szl_kernels._ops.GovernedBlock,
where the Λ gate is explicitly "advisory ... does NOT block, mask, or alter the
numerics"). There is no first-class, verifiable way for a governed layer to say
"I will NOT run this op, here is why, and here is a tamper-evident receipt of the
refusal." The two silent failure modes that fill that vacuum are both dishonest:

  * silent degrade  — quietly fall back to a weaker/no-op result, hiding refusal
  * fabricated output — emit a plausible-looking tensor with no governance basis
    ("fake green": a green checkmark over an op that never honestly passed)

``szl_blocked`` makes BLOCKED a structured, hash-chained, first-class RETURN:

  * ``GovernedGate.decide(...)``  -> a ``GateDecision`` (ALLOW or BLOCK) with a
    receipt emitted into the shared UnifiedReceiptChain, BEFORE any op runs.
  * ``governed_call(fn, policy, chain, ...)`` -> runs the deny-by-default HARD
    security policy + the ADVISORY Λ gate; if BLOCKED, the wrapped ``fn`` is
    NEVER called and a structured ``BlockedResult`` is returned with a BLOCKED
    receipt. If ALLOWED, ``fn`` runs and an ALLOWED receipt binds its output.

ORDERING DOCTRINE (Conjecture 1, advisory)
------------------------------------------
HARD security DENY DOMINATES. The advisory Λ gate may only ever TIGHTEN a
decision (ALLOW -> BLOCK); it can NEVER override a hard DENY into an ALLOW, and
it can NEVER, on its own, manufacture trust. Λ uniqueness is Conjecture 1 (OPEN);
a Λ "pass" is advisory, never proven trust. So the lattice is:

    HARD_DENY  >  (advisory Λ may tighten ALLOW->BLOCK)  >  HARD_ALLOW

A decision is ALLOW iff (hard policy ALLOWs) AND (advisory Λ does not veto).
A decision is BLOCK if EITHER the hard policy denies OR advisory Λ vetoes — and
a hard-policy deny is recorded with ``dominant="HARD_SECURITY"`` so an auditor
can see security dominated, not advisory Λ.

HONESTY
-------
* BLOCKED is honest refusal — never fake-green. ``BlockedResult.output is None``
  always; ``BlockedResult.blocked is True`` always; there is no code path that
  fabricates a substitute output.
* The BLOCKED/ALLOWED receipt is a SHA3-256 integrity fingerprint (the suite
  scheme) — tamper-evidence + ordering, "signed-able" out-of-band (DSSE/sigstore)
  exactly like every other suite receipt. Signing itself is NOT claimed here.
* Energy, when recorded, stays MEASURED-only (joules None when no NVML).
* Pure-Python; torch is OPTIONAL (only the wrapped ``fn`` may need it).
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from ._chain import UnifiedReceiptChain

# Verdict constants — a small, closed vocabulary so receipts are machine-checkable.
ALLOW = "ALLOW"
BLOCK = "BLOCK"

# Which authority produced a BLOCK (or carried an ALLOW). HARD_SECURITY dominates.
DOMINANT_HARD = "HARD_SECURITY"
DOMINANT_ADVISORY = "ADVISORY_LAMBDA"
DOMINANT_NONE = "NONE"


class PolicyResult:
    """Result of a HARD, deny-by-default security policy hook.

    ``allow`` is the binding decision of the hard layer. ``reason`` is a short
    human string. ``code`` is a stable machine token (e.g. ``"OK"``,
    ``"DENY_DEFAULT"``, ``"DENY_RULE:no_exfil"``). ``detail`` is a JSON-able dict
    of honest, reproducible context (never fabricated).
    """

    __slots__ = ("allow", "reason", "code", "detail")

    def __init__(
        self,
        allow: bool,
        reason: str,
        code: str = "",
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.allow = bool(allow)
        self.reason = str(reason)
        self.code = str(code) if code else ("OK" if allow else "DENY")
        self.detail = dict(detail or {})

    def as_dict(self) -> Dict[str, Any]:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "code": self.code,
            "detail": self.detail,
        }


# A hard security policy hook is any callable: (request_ctx) -> PolicyResult.
SecurityPolicy = Callable[[Dict[str, Any]], PolicyResult]


def deny_by_default(rules: Optional[List[SecurityPolicy]] = None) -> SecurityPolicy:
    """Build a HARD, deny-by-default security policy from allow/deny rules.

    Doctrine: the DEFAULT is DENY. A request is allowed ONLY if at least one
    rule explicitly returns ``allow=True`` AND no rule returns ``allow=False``.
    Any single hard DENY dominates (deny wins), and absence of an explicit ALLOW
    is itself a DENY (``DENY_DEFAULT``). This is the opposite of the
    optimize-throughput default and is what makes refusal the safe ground state.
    """
    rules = list(rules or [])

    def _policy(ctx: Dict[str, Any]) -> PolicyResult:
        explicit_allow = False
        for rule in rules:
            r = rule(ctx)
            if not r.allow:
                # First hard DENY dominates immediately.
                return PolicyResult(
                    False,
                    r.reason or "hard security rule denied",
                    code=r.code or "DENY_RULE",
                    detail=r.detail,
                )
            explicit_allow = True
        if not explicit_allow:
            return PolicyResult(
                False,
                "deny-by-default: no explicit hard ALLOW rule matched",
                code="DENY_DEFAULT",
                detail={"n_rules": len(rules)},
            )
        return PolicyResult(True, "all hard security rules allowed", code="OK")

    return _policy


def _lambda_advisory_score(
    axes: Optional[List[float]],
    weights: Optional[List[float]],
) -> Tuple[Optional[float], int]:
    """Pure-Python weighted-geometric-mean Λ with non-compensatory zero-routing.

    Faithful to szl_kernels Λ semantics: any zero / negative / non-finite axis
    drives Λ to 0 (a single failed axis cannot be compensated by others). No
    torch dependency — operates on plain floats so the gate is inspectable in a
    torch-less env. Returns (score_or_None, k). score is None iff axes is None
    (no advisory signal supplied — gate then does not veto).
    """
    if axes is None:
        return (None, 0)
    xs = [float(a) for a in axes]
    k = len(xs)
    if k == 0:
        return (0.0, 0)
    if weights is None:
        ws = [1.0 / k] * k
    else:
        ws = [float(w) for w in weights]
        s = sum(ws)
        ws = [w / s for w in ws] if s else [1.0 / k] * k
    import math

    acc = 0.0
    for x, w in zip(xs, ws):
        if not math.isfinite(x) or x <= 0.0:
            return (0.0, k)  # non-compensatory zero-route
        xc = 1.0 if x > 1.0 else x
        acc += math.log(xc) * w
    val = math.exp(acc)
    if val < 0.0:
        val = 0.0
    elif val > 1.0:
        val = 1.0
    return (val, k)


class GateDecision:
    """The first-class verdict object. ALLOW or BLOCK, fully auditable.

    Attributes
    ----------
    verdict      : ALLOW | BLOCK
    allowed      : bool  (verdict == ALLOW)
    blocked      : bool  (verdict == BLOCK)
    reason       : human string
    dominant     : which authority decided (HARD_SECURITY | ADVISORY_LAMBDA | NONE)
    policy       : the HARD PolicyResult as a dict
    advisory     : the advisory Λ block as a dict (advisory=True, status string)
    receipt      : the receipt emitted into the chain (None until emit())
    """

    __slots__ = ("verdict", "reason", "dominant", "policy", "advisory", "receipt")

    def __init__(
        self,
        verdict: str,
        reason: str,
        dominant: str,
        policy: Dict[str, Any],
        advisory: Dict[str, Any],
    ) -> None:
        self.verdict = verdict
        self.reason = reason
        self.dominant = dominant
        self.policy = policy
        self.advisory = advisory
        self.receipt: Optional[Dict[str, Any]] = None

    @property
    def allowed(self) -> bool:
        return self.verdict == ALLOW

    @property
    def blocked(self) -> bool:
        return self.verdict == BLOCK

    def as_attrs(self) -> Dict[str, Any]:
        """JSON-able, finite attrs for the receipt body (never fabricated)."""
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "dominant": self.dominant,
            "hard_allow": bool(self.policy.get("allow")),
            "hard_code": str(self.policy.get("code", "")),
            "advisory_score": self.advisory.get("score"),
            "advisory_threshold": self.advisory.get("threshold"),
            "advisory_passed": self.advisory.get("passed"),
            "advisory": True,
            "lambda_status": "Conjecture 1 (open) — advisory only, NOT proven trust",
            "doctrine": "HARD security DENY dominates; advisory Λ can only tighten",
        }


class GovernedGate:
    """A governed gate that yields an honest first-class ALLOW/BLOCK decision.

    Composition, in strict order:
      1. HARD, deny-by-default security policy hook  (BINDING)
      2. ADVISORY Λ gate over caller governance axes  (may TIGHTEN only)

    The hard layer is evaluated first and DOMINATES. If it denies, the advisory
    Λ result is still recorded for audit, but it CANNOT flip the verdict to
    ALLOW. If the hard layer allows, the advisory Λ gate may veto (tighten) the
    decision to BLOCK when its score is below threshold — recorded with
    ``dominant=ADVISORY_LAMBDA``. Advisory Λ NEVER manufactures an ALLOW.
    """

    def __init__(
        self,
        policy: Optional[SecurityPolicy] = None,
        lambda_threshold: float = 0.5,
        chain: Optional[UnifiedReceiptChain] = None,
    ) -> None:
        # Default hard policy is the strictest possible: pure deny-by-default
        # with NO allow rules => everything is denied until a policy is supplied.
        self.policy: SecurityPolicy = policy if policy is not None else deny_by_default()
        self.lambda_threshold = float(lambda_threshold)
        self.chain = chain if chain is not None else UnifiedReceiptChain()

    def decide(
        self,
        request: Optional[Dict[str, Any]] = None,
        gov_axes: Optional[List[float]] = None,
        gov_weights: Optional[List[float]] = None,
        kernel: str = "governed_gate",
        op: str = "gate_decision",
    ) -> GateDecision:
        """Evaluate hard policy + advisory Λ and emit ONE decision receipt.

        Returns a GateDecision. Always emits exactly one receipt (ALLOW or
        BLOCK) into the shared chain, in call order, BEFORE any wrapped op runs.
        """
        ctx = dict(request or {})

        # 1. HARD security policy (binding, deny-by-default, deny dominates).
        pol = self.policy(ctx)

        # 2. ADVISORY Λ gate (records; can only tighten an ALLOW).
        score, k = _lambda_advisory_score(gov_axes, gov_weights)
        if score is None:
            adv_passed = True  # no advisory signal supplied => no veto
            adv = {
                "score": None,
                "threshold": self.lambda_threshold,
                "passed": True,
                "k": 0,
                "advisory": True,
                "note": "no advisory Λ axes supplied; advisory layer abstains",
            }
        else:
            adv_passed = score >= self.lambda_threshold
            adv = {
                "score": score,
                "threshold": self.lambda_threshold,
                "passed": adv_passed,
                "k": k,
                "advisory": True,
            }

        # Combine under the ordering doctrine.
        if not pol.allow:
            verdict = BLOCK
            dominant = DOMINANT_HARD
            reason = "HARD security policy DENY: " + pol.reason
        elif not adv_passed:
            verdict = BLOCK
            dominant = DOMINANT_ADVISORY
            reason = (
                "advisory Λ veto (tightened ALLOW->BLOCK): score "
                "{:.6f} < threshold {:.6f}".format(
                    score if score is not None else 0.0, self.lambda_threshold
                )
            )
        else:
            verdict = ALLOW
            dominant = DOMINANT_NONE
            reason = "hard security ALLOW and advisory Λ did not veto"

        decision = GateDecision(
            verdict=verdict,
            reason=reason,
            dominant=dominant,
            policy=pol.as_dict(),
            advisory=adv,
        )
        # Emit exactly one decision receipt into the shared chain, in order.
        decision.receipt = self.chain.emit(kernel, op, decision.as_attrs())
        return decision


class BlockedResult:
    """The honest first-class BLOCKED return of ``governed_call``.

    There is NO output. ``output`` is always None; ``blocked`` is always True.
    This is the structural guarantee against fake-green: a BLOCKED run cannot
    carry a substitute tensor. The decision + its BLOCKED receipt explain WHY,
    verifiably, via the shared chain.
    """

    __slots__ = ("decision", "reason", "receipt")

    blocked = True
    allowed = False
    output = None

    def __init__(self, decision: GateDecision) -> None:
        self.decision = decision
        self.reason = decision.reason
        self.receipt = decision.receipt

    def as_dict(self) -> Dict[str, Any]:
        return {
            "blocked": True,
            "allowed": False,
            "output": None,
            "verdict": self.decision.verdict,
            "reason": self.reason,
            "dominant": self.decision.dominant,
            "receipt_digest": (self.receipt or {}).get("digest"),
        }

    def __repr__(self) -> str:
        return "BlockedResult(dominant={!r}, reason={!r})".format(
            self.decision.dominant, self.reason
        )


class AllowedResult:
    """The first-class ALLOWED return of ``governed_call``: real output + receipt.

    ``output`` is exactly what the wrapped ``fn`` produced (never substituted).
    A second ALLOWED receipt binds the produced output's digest into the chain
    AFTER the op ran, so the chain proves "this op was permitted, then ran, and
    produced this output" with nothing inserted between.
    """

    __slots__ = ("decision", "output", "output_receipt")

    blocked = False
    allowed = True

    def __init__(
        self,
        decision: GateDecision,
        output: Any,
        output_receipt: Optional[Dict[str, Any]],
    ) -> None:
        self.decision = decision
        self.output = output
        self.output_receipt = output_receipt

    def as_dict(self) -> Dict[str, Any]:
        return {
            "blocked": False,
            "allowed": True,
            "verdict": self.decision.verdict,
            "decision_digest": (self.decision.receipt or {}).get("digest"),
            "output_receipt_digest": (self.output_receipt or {}).get("digest"),
        }

    def __repr__(self) -> str:
        return "AllowedResult(output_type={!r})".format(type(self.output).__name__)


def _safe_output_digest(output: Any) -> Dict[str, Any]:
    """Honest, JSON-able fingerprint of a produced output for the receipt.

    Uses the suite tensor_digest for tensors; for plain Python values, a stable
    SHA3-256 over a canonical repr. Never fabricates a value it cannot derive.
    """
    import hashlib

    from ._chain import tensor_digest

    if hasattr(output, "detach") and hasattr(output, "reshape"):
        return {
            "out_kind": "tensor",
            "out_shape": list(getattr(output, "shape", [])),
            "out_digest": tensor_digest(output),
        }
    try:
        import json as _json

        raw = _json.dumps(output, sort_keys=True, separators=(",", ":"), default=repr)
    except Exception:
        raw = repr(output)
    return {
        "out_kind": type(output).__name__,
        "out_digest": hashlib.sha3_256(raw.encode("utf-8")).hexdigest(),
    }


def governed_call(
    fn: Callable[..., Any],
    policy: Optional[SecurityPolicy] = None,
    chain: Optional[UnifiedReceiptChain] = None,
    *,
    request: Optional[Dict[str, Any]] = None,
    gov_axes: Optional[List[float]] = None,
    gov_weights: Optional[List[float]] = None,
    lambda_threshold: float = 0.5,
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    kernel: str = "governed_gate",
):
    """Run ``fn`` ONLY if a governed ALLOW verdict is reached; else honest BLOCK.

    Flow (all into the shared chain, in order):
      1. ``GovernedGate.decide`` -> hard deny-by-default policy + advisory Λ.
         A decision receipt (ALLOW or BLOCK) is emitted BEFORE any op runs.
      2. If BLOCKED: ``fn`` is NEVER called. Return a ``BlockedResult``
         (output is None, blocked is True). honest-BLOCKED, not fake-green.
      3. If ALLOWED: call ``fn(*args, **kwargs)``, then emit a SECOND ALLOWED
         receipt binding the produced output's digest. Return ``AllowedResult``.

    Returns ``AllowedResult`` or ``BlockedResult`` — both first-class. The caller
    inspects ``.blocked`` / ``.allowed`` and uses ``.output`` only when allowed.
    """
    gate = GovernedGate(
        policy=policy, lambda_threshold=lambda_threshold, chain=chain
    )
    decision = gate.decide(
        request=request,
        gov_axes=gov_axes,
        gov_weights=gov_weights,
        kernel=kernel,
        op="gate_decision",
    )

    if decision.blocked:
        # HARD STOP. The wrapped op is NOT executed. No substitute output.
        return BlockedResult(decision)

    # ALLOWED: run the real op, then bind its output into the chain.
    kwargs = dict(kwargs or {})
    output = fn(*args, **kwargs)
    attrs = {"verdict": ALLOW, "bound_to_decision": (decision.receipt or {}).get("digest")}
    attrs.update(_safe_output_digest(output))
    out_receipt = gate.chain.emit(kernel, "op_executed", attrs)
    return AllowedResult(decision, output, out_receipt)
