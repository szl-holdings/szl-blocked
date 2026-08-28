# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""szl_blocked — honest-BLOCKED as a FIRST-CLASS governed-kernel/layer state.

The SZL suite governs PROVENANCE across ops; every member still always returns a
tensor. ``szl_blocked`` adds the missing verdict: a governed layer that can
REFUSE, verifiably, instead of silently degrading or fabricating output.

    from szl_blocked import GovernedGate, governed_call, deny_by_default
    from szl_blocked import allow_if_capability, deny_if_action_in

    # A hard, deny-by-default security policy that needs an explicit capability:
    policy = deny_by_default([allow_if_capability("run_norm")])

    res = governed_call(
        my_op, policy=policy,
        request={"capabilities": ["run_norm"], "action": "rms_norm"},
        gov_axes=[0.95, 0.9, 0.92], lambda_threshold=0.5,
        args=(x,),
    )
    if res.blocked:
        print("honest BLOCKED:", res.reason)   # output is None — never fake-green
    else:
        y = res.output                         # the real op output, with receipts

HONESTY (SZL doctrine v11):
  * BLOCKED is honest refusal. ``BlockedResult.output`` is ALWAYS None; the op
    does NOT run. No code path fabricates a substitute output (no fake-green).
  * HARD security DENY DOMINATES. Advisory Λ can only TIGHTEN (ALLOW->BLOCK);
    it can NEVER override a hard DENY and NEVER manufactures trust. Λ uniqueness
    = Conjecture 1 (OPEN); a Λ pass is advisory, never proven trust.
  * Decision receipts are SHA3-256 integrity fingerprints in the SAME
    UnifiedReceiptChain the suite uses — tamper-evidence + ordering,
    "signed-able" out-of-band (DSSE/sigstore), NOT a signature here.
  * Energy stays MEASURED-only. Pure-Python; torch is OPTIONAL.
"""
from ._chain import GENESIS, UnifiedReceiptChain, tensor_digest
from ._gate import (
    ALLOW,
    BLOCK,
    DOMINANT_ADVISORY,
    DOMINANT_HARD,
    DOMINANT_NONE,
    AllowedResult,
    BlockedResult,
    GateDecision,
    GovernedGate,
    PolicyResult,
    deny_by_default,
    governed_call,
)
from ._rules import allow_if_capability, deny_if_action_in, deny_if_flag

__all__ = [
    "GovernedGate",
    "governed_call",
    "GateDecision",
    "BlockedResult",
    "AllowedResult",
    "PolicyResult",
    "deny_by_default",
    "allow_if_capability",
    "deny_if_flag",
    "deny_if_action_in",
    "UnifiedReceiptChain",
    "tensor_digest",
    "GENESIS",
    "ALLOW",
    "BLOCK",
    "DOMINANT_HARD",
    "DOMINANT_ADVISORY",
    "DOMINANT_NONE",
    "DOCTRINE_FOOTER",
    "__version__",
]

__version__ = "0.1.0"

DOCTRINE_FOOTER = (
    "SZL Holdings · honest-BLOCKED first-class state · hard security DENY "
    "dominates · advisory Λ tightens only (Conjecture 1, open) · energy "
    "MEASURED-only · honest refusal beats fake green"
)
