# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""Auto-derive an EU AI Act Annex IV-style technical-documentation SKELETON
from szl_kernels governance provenance (a UnifiedReceiptChain export).

THE FRONTIER GAP THIS CLOSES
----------------------------
Compliance documentation is normally a SEPARATE, manual workflow written long
after the system runs — disconnected from what actually happened on the wire.
The SZL suite already produces a tamper-evident, op-agnostic provenance chain of
every governed op (norm / advisory-Λ / energy / honest-BLOCKED gate). This module
turns that chain INTO the traceability backbone of an Annex IV-style technical
file, so compliance documentation is a BYPRODUCT of provenance, not a side task.

WHAT IT PRODUCES
----------------
``derive_annex_iv(record)`` consumes a governance record (a dict with a
``chain`` = the list exported by ``UnifiedReceiptChain.to_json()`` / ``.tail``,
plus optional human-supplied ``system`` metadata) and returns a structured dict
mirroring the nine elements of EU AI Act Annex IV. Provenance-derived sections
(traceability, energy disclosure, Λ-advisory risk caveats, BLOCKED events) are
POPULATED FROM THE CHAIN; human-supplied sections (intended purpose, etc.) are
copied verbatim and flagged ``TODO`` when missing — never invented.

``to_markdown(doc)`` renders the same content as a human-readable Markdown file.

HONESTY (binding)
-----------------
* This is a DRAFT SKELETON derived from provenance. It is NOT legal advice and
  NOT a conformity guarantee / declaration. Every output is labelled as such.
* Λ is ADVISORY only (Conjecture 1, OPEN). Recorded "passed" is never proven
  trust; the risk section says so explicitly.
* Energy is reported MEASURED-only: if the chain's energy receipts carry no
  joules (label UNAVAILABLE_NO_NVML / joules None), the doc DISCLOSES "no
  measured figure available" and fabricates NO number.
* honest-BLOCKED events from szl_blocked are surfaced as governance evidence,
  not hidden. A refusal is a feature of the record, not an embarrassment.
* No fabricated numbers anywhere. Missing human input => explicit TODO.
* Prior-art is named honestly (EU AI Act Annex IV; SPDX 3.0 AI profile / AI BOM)
  — this skeleton is INSPIRED BY those, not an official template of either.

Stdlib only. No torch, no network, no disk writes from inside this module.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "szl-annex-iv-skeleton/0.1.0"

# A standing, prominent honesty banner stamped on every artifact.
DISCLAIMER = (
    "DRAFT SKELETON — auto-derived from cryptographic governance provenance. "
    "This is NOT legal advice and NOT a declaration of conformity. It does not "
    "by itself satisfy EU AI Act Annex IV; it is a starting point a qualified "
    "provider/legal reviewer must complete and verify. Provenance-derived "
    "sections reflect ONLY what the receipt chain recorded."
)

PRIOR_ART = [
    {
        "name": "EU AI Act (Regulation (EU) 2024/1689), Annex IV",
        "role": "Structure mirrored: the nine technical-documentation elements.",
        "note": "Skeleton is INSPIRED BY Annex IV; not an official template.",
    },
    {
        "name": "SPDX 3.0 AI Profile / AI BOM",
        "role": "Provenance/BOM framing for AI components, energy, datasets.",
        "note": "Used as a cross-reference for the traceability/BOM section.",
    },
    {
        "name": "szl_kernels UnifiedReceiptChain",
        "role": "The SHA3-256 hash-chained provenance source this doc derives from.",
        "note": "Integrity fingerprint (tamper-evidence + ordering), not a signature.",
    },
]

# The nine Annex IV elements (paraphrased headings) we lay out as a skeleton.
ANNEX_IV_ELEMENTS = [
    "1_general_description",
    "2_detailed_description_elements_and_development",
    "3_monitoring_functioning_control",
    "4_performance_metrics_appropriateness",
    "5_risk_management_system",
    "6_lifecycle_changes",
    "7_standards_applied",
    "8_declaration_of_conformity_reference",
    "9_post_market_monitoring_plan",
]


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _sha3(s: str) -> str:
    return hashlib.sha3_256(s.encode("utf-8")).hexdigest()


def _todo(what: str) -> Dict[str, str]:
    """A structured, explicit gap marker. Never invent the missing content."""
    return {
        "status": "TODO",
        "needs": what,
        "note": "Human-supplied input required; NOT auto-derivable from provenance.",
    }


def _coerce_chain(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Accept several honest shapes for the provenance chain.

    Supported:
      * record[\"chain\"] as a list of receipt dicts
      * record[\"chain\"] as a JSON string (UnifiedReceiptChain.to_json output)
      * record[\"chain_json\"] as a JSON string
    Returns [] if no chain is present (the doc then says so honestly).
    """
    chain = record.get("chain")
    if chain is None:
        chain = record.get("chain_json")
    if isinstance(chain, str):
        try:
            chain = json.loads(chain)
        except Exception:
            return []
    if isinstance(chain, list):
        return [r for r in chain if isinstance(r, dict)]
    return []


def _summarize_chain(chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive honest, reproducible provenance facts from the receipt chain."""
    kernels_seen: List[str] = []
    ops: List[Dict[str, Any]] = []
    lambda_events: List[Dict[str, Any]] = []
    energy_events: List[Dict[str, Any]] = []
    blocked_events: List[Dict[str, Any]] = []
    allowed_gate_events: List[Dict[str, Any]] = []

    for rec in chain:
        kern = rec.get("kernel", "")
        if kern and kern not in kernels_seen:
            kernels_seen.append(kern)
        attrs = rec.get("attrs", {}) or {}
        ops.append(
            {
                "seq": rec.get("seq"),
                "kernel": kern,
                "op": rec.get("op"),
                "digest": rec.get("digest"),
            }
        )
        if "lambda_status" in attrs or (
            kern == "lambda_gate" and "score" in attrs
        ):
            lambda_events.append(
                {
                    "seq": rec.get("seq"),
                    "score": attrs.get("score") or attrs.get("advisory_score"),
                    "threshold": attrs.get("threshold")
                    or attrs.get("advisory_threshold"),
                    "passed": attrs.get("passed")
                    if "passed" in attrs
                    else attrs.get("advisory_passed"),
                }
            )
        if kern == "energy_core" or "joules" in attrs:
            energy_events.append(
                {
                    "seq": rec.get("seq"),
                    "label": attrs.get("label"),
                    "joules": attrs.get("joules"),
                    "source": attrs.get("source"),
                }
            )
        if attrs.get("verdict") == "BLOCK" or attrs.get("dominant") in (
            "HARD_SECURITY",
            "ADVISORY_LAMBDA",
        ):
            if attrs.get("verdict") == "BLOCK":
                blocked_events.append(
                    {
                        "seq": rec.get("seq"),
                        "reason": attrs.get("reason"),
                        "dominant": attrs.get("dominant"),
                        "digest": rec.get("digest"),
                    }
                )
        if attrs.get("verdict") == "ALLOW" and rec.get("op") in (
            "gate_decision",
            "op_executed",
        ):
            allowed_gate_events.append(
                {"seq": rec.get("seq"), "op": rec.get("op"), "digest": rec.get("digest")}
            )

    measured = [
        e
        for e in energy_events
        if e.get("joules") is not None and str(e.get("label", "")).upper() == "MEASURED"
    ]
    total_measured = sum(float(e["joules"]) for e in measured) if measured else None
    energy_disclosure = {
        "measured_joules_total": total_measured,
        "n_measured_readings": len(measured),
        "n_energy_receipts": len(energy_events),
        "labels_seen": sorted({str(e.get("label")) for e in energy_events}),
        "disclosure": (
            "No MEASURED energy figure available in this chain (e.g. no GPU/NVML; "
            "labels were UNAVAILABLE/UNKNOWN). No joule value is fabricated."
            if total_measured is None
            else "Total reflects ONLY receipts explicitly labelled MEASURED; "
            "non-MEASURED readings are excluded, not estimated."
        ),
    }

    return {
        "n_receipts": len(chain),
        "kernels_touched": kernels_seen,
        "ops": ops,
        "head_digest": chain[-1].get("digest") if chain else None,
        "lambda_events": lambda_events,
        "energy_events": energy_events,
        "energy_disclosure": energy_disclosure,
        "blocked_events": blocked_events,
        "allowed_gate_events": allowed_gate_events,
        "chain_present": bool(chain),
    }


def _verify_export(record: Dict[str, Any], chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Re-walk the chain offline (suite scheme) to attest integrity in the doc.

    Uses szl_kernels' verifier when importable; otherwise an identical inline
    re-walk. Records (ok, depth, first_break) so the technical file can state
    whether the provenance it was derived from verified as tamper-evident.
    """
    if not chain:
        return {"verified": None, "note": "no chain to verify"}
    blob = json.dumps(chain, sort_keys=True, separators=(",", ":"))
    try:
        from szl_kernels._chain import UnifiedReceiptChain  # type: ignore

        ok, depth, brk = UnifiedReceiptChain.verify_json(blob)
        src = "szl_kernels.verify_json"
    except Exception:
        ok, depth, brk = _inline_verify(chain)
        src = "inline(szl_euaiact)"
    return {
        "verified": bool(ok),
        "depth": depth,
        "first_break_seq": brk,
        "verifier": src,
        "note": (
            "Provenance re-walked offline: digests + prev-links recomputed. "
            "Integrity fingerprint only (NOT a signature)."
        ),
    }


def _inline_verify(chain: List[Dict[str, Any]]):
    genesis = "0" * 64
    prev = genesis
    for i, rec in enumerate(chain):
        body = {k: rec.get(k) for k in ("seq", "kernel", "op", "attrs", "prev")}
        digest = _sha3(_canonical(body))
        if rec.get("prev") != prev or rec.get("digest") != digest:
            return (False, len(chain), i)
        prev = rec.get("digest")
    return (True, len(chain), -1)


def derive_annex_iv(record: Dict[str, Any]) -> Dict[str, Any]:
    """Derive a structured Annex IV-style skeleton from a governance record."""
    record = dict(record or {})
    system = dict(record.get("system") or {})
    chain = _coerce_chain(record)
    prov = _summarize_chain(chain)
    integrity = _verify_export(record, chain)

    def have(key: str) -> Any:
        v = system.get(key)
        return v if (v is not None and v != "") else None

    annex = {
        "1_general_description": {
            "system_name": have("name") or _todo("AI system name"),
            "provider": have("provider") or _todo("provider / responsible entity"),
            "version": have("version") or _todo("system version identifier"),
            "intended_purpose": have("intended_purpose")
            or _todo("intended purpose statement"),
            "what_provenance_shows": {
                "governed_kernels_exercised": prov["kernels_touched"],
                "n_governed_ops_recorded": prov["n_receipts"],
            },
        },
        "2_detailed_description_elements_and_development": {
            "development_process": have("development_process")
            or _todo("development process description"),
            "components_bom": have("components")
            or _todo("AI BOM components (SPDX AI profile style)"),
            "provenance_derived_op_log": prov["ops"],
            "data_provenance": have("data_provenance")
            or _todo("training/validation/test data provenance"),
        },
        "3_monitoring_functioning_control": {
            "governance_controls_observed": {
                "advisory_lambda_gate_evaluations": len(prov["lambda_events"]),
                "honest_blocked_events": len(prov["blocked_events"]),
                "allowed_gate_events": len(prov["allowed_gate_events"]),
            },
            "honest_blocked_events_detail": prov["blocked_events"],
            "human_oversight": have("human_oversight")
            or _todo("human oversight measures"),
            "note": (
                "honest-BLOCKED events are a positive control signal: the system "
                "verifiably refused rather than silently degrading or fabricating "
                "output. HARD security deny dominates advisory Λ."
            ),
        },
        "4_performance_metrics_appropriateness": {
            "performance_metrics": have("performance_metrics")
            or _todo("validated performance metrics + methodology"),
            "caveat": (
                "No performance/accuracy numbers are auto-derived; the provenance "
                "chain records governance + integrity, not benchmark results. "
                "Any metric must be supplied and validated by the provider."
            ),
        },
        "5_risk_management_system": {
            "lambda_advisory_caveat": (
                "Λ is an ADVISORY weighted-geometric-mean aggregator. Its "
                "uniqueness is Conjecture 1 (OPEN). A recorded Λ 'passed=True' is "
                "a non-compensatory advisory signal, NEVER proven trust, and must "
                "NOT be presented as a safety guarantee."
            ),
            "advisory_lambda_events": prov["lambda_events"],
            "residual_risk_assessment": have("residual_risk")
            or _todo("residual risk assessment"),
            "spdx_safety_risk_assessment": have("safety_risk_assessment")
            or _todo("SPDX AI SafetyRiskAssessmentType (low/medium/high/serious)"),
        },
        "6_lifecycle_changes": {
            "change_log": have("change_log") or _todo("lifecycle change log"),
            "provenance_head_digest": prov["head_digest"],
            "note": (
                "The receipt-chain head digest pins THIS run's provenance state; "
                "successive runs produce successive heads for change tracking."
            ),
        },
        "7_standards_applied": {
            "standards": have("standards")
            or _todo("harmonised standards / specifications applied"),
            "prior_art_referenced": [p["name"] for p in PRIOR_ART],
        },
        "8_declaration_of_conformity_reference": {
            "declaration_reference": have("declaration_of_conformity")
            or _todo("EU declaration of conformity reference"),
            "warning": (
                "This skeleton is NOT a declaration of conformity and does not "
                "imply one exists. A declaration is a separate legal instrument."
            ),
        },
        "9_post_market_monitoring_plan": {
            "post_market_monitoring": have("post_market_monitoring")
            or _todo("post-market monitoring plan"),
            "energy_consumption_disclosure_measured_only": prov["energy_disclosure"],
            "provenance_integrity": integrity,
        },
    }

    doc = {
        "schema_version": SCHEMA_VERSION,
        "disclaimer": DISCLAIMER,
        "is_legal_advice": False,
        "is_conformity_guarantee": False,
        "artifact_type": "DRAFT_SKELETON",
        "prior_art": PRIOR_ART,
        "provenance_summary": {
            "chain_present": prov["chain_present"],
            "n_receipts": prov["n_receipts"],
            "kernels_touched": prov["kernels_touched"],
            "head_digest": prov["head_digest"],
            "integrity": integrity,
        },
        "annex_iv": annex,
    }
    doc["generated_digest"] = _sha3(_canonical(doc))
    return doc


def to_markdown(doc: Dict[str, Any]) -> str:
    """Render the derived skeleton as honest, human-readable Markdown."""
    L: List[str] = []
    a = doc.get("annex_iv", {})
    prov = doc.get("provenance_summary", {})

    L.append("# EU AI Act Annex IV — DRAFT Technical-Documentation Skeleton")
    L.append("")
    L.append("> **" + doc.get("disclaimer", DISCLAIMER) + "**")
    L.append("")
    L.append(
        "- Artifact type: **{}** | Legal advice: **{}** | Conformity guarantee: "
        "**{}**".format(
            doc.get("artifact_type"),
            doc.get("is_legal_advice"),
            doc.get("is_conformity_guarantee"),
        )
    )
    L.append("- Schema: `{}`".format(doc.get("schema_version")))
    L.append("- Self-fingerprint (SHA3-256): `{}`".format(doc.get("generated_digest")))
    L.append("")

    L.append("## Provenance backbone (auto-derived)")
    integ = prov.get("integrity", {})
    L.append("- Receipts in chain: **{}**".format(prov.get("n_receipts")))
    L.append(
        "- Governed kernels touched: {}".format(
            ", ".join(prov.get("kernels_touched") or []) or "(none)"
        )
    )
    L.append("- Chain head digest: `{}`".format(prov.get("head_digest")))
    L.append(
        "- Integrity re-walk: verified=**{}**, depth={}, first_break={}, "
        "verifier=`{}`".format(
            integ.get("verified"),
            integ.get("depth"),
            integ.get("first_break_seq"),
            integ.get("verifier"),
        )
    )
    L.append("")

    titles = {
        "1_general_description": "1. General description of the AI system",
        "2_detailed_description_elements_and_development": (
            "2. Detailed description of elements and development process"
        ),
        "3_monitoring_functioning_control": (
            "3. Monitoring, functioning and control"
        ),
        "4_performance_metrics_appropriateness": (
            "4. Appropriateness of performance metrics"
        ),
        "5_risk_management_system": "5. Risk management system",
        "6_lifecycle_changes": "6. Lifecycle changes",
        "7_standards_applied": "7. Standards and specifications applied",
        "8_declaration_of_conformity_reference": (
            "8. Reference to the EU declaration of conformity"
        ),
        "9_post_market_monitoring_plan": (
            "9. Post-market monitoring plan + energy disclosure"
        ),
    }
    for key in ANNEX_IV_ELEMENTS:
        L.append("## " + titles.get(key, key))
        section = a.get(key, {})
        L.append("")
        L.append("```json")
        L.append(json.dumps(section, indent=2, default=str))
        L.append("```")
        L.append("")

    L.append("## Honest prior-art notes")
    for p in doc.get("prior_art", []):
        L.append("- **{}** — {} _{}_".format(p["name"], p["role"], p["note"]))
    L.append("")
    L.append(
        "_This document was auto-derived from a szl_kernels UnifiedReceiptChain. "
        "Compliance is treated as a byproduct of provenance; it still requires "
        "human completion of all TODO items and qualified legal review._"
    )
    L.append("")
    return "\n".join(L)


__all__ = [
    "derive_annex_iv",
    "to_markdown",
    "DISCLAIMER",
    "PRIOR_ART",
    "SCHEMA_VERSION",
    "ANNEX_IV_ELEMENTS",
]
