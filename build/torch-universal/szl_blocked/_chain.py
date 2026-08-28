# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""Minimal, torch-optional re-export of the szl_kernels UnifiedReceiptChain.

szl_blocked records its BLOCKED/ALLOWED verdicts into the SAME op-agnostic,
SHA3-256 hash-chained ``UnifiedReceiptChain`` the rest of the suite uses, so a
governed-gate decision sits in call order alongside norm / advisory-Λ / energy
receipts and re-walks as ONE tamper-evident sequence.

We prefer the installed ``szl_kernels`` chain (byte-identical digests). If it is
not importable in a headless review env, we fall back to a vendored copy whose
digest scheme is IDENTICAL (same canonical JSON body {seq,kernel,op,attrs,prev},
same SHA3-256, same GENESIS, same _DECIMALS) so receipts produced here verify
against the suite's own ``verify_json``. The vendored copy is a faithful
sub-port of szl_kernels/_chain.py — NOT a re-design.

HONESTY: the digest is an INTEGRITY fingerprint (tamper-evidence + ordering),
NOT a cryptographic signature and NOT proof of authorship. A BLOCKED receipt is
"signed-able" in the same out-of-band DSSE/sigstore sense as every other suite
receipt; signing itself is explicitly NOT claimed here.
"""
from __future__ import annotations

try:  # prefer the shipped suite chain so digests are byte-identical
    from szl_kernels._chain import (  # type: ignore
        GENESIS,
        UnifiedReceiptChain,
        tensor_digest,
    )
    _CHAIN_SOURCE = "szl_kernels"
except Exception:  # pragma: no cover - vendored fallback for standalone review
    import hashlib
    import json
    import threading
    import time
    from typing import Any, Dict, List

    try:
        import torch  # noqa: F401
        _HAS_TORCH = True
    except Exception:
        _HAS_TORCH = False

    GENESIS = "0" * 64
    _DECIMALS = 6
    _CHAIN_SOURCE = "vendored(szl_blocked)"

    def tensor_digest(t: "Any", decimals: int = _DECIMALS) -> str:
        """Deterministic SHA3-256 over rounded float32 contents (suite scheme)."""
        if _HAS_TORCH and hasattr(t, "detach"):
            flat = t.detach().to(torch.float32).reshape(-1)
            scaled = (
                torch.round(flat * (10 ** decimals))
                .to(torch.int64)
                .cpu()
                .numpy()
                .tobytes()
            )
            return hashlib.sha3_256(scaled).hexdigest()
        return hashlib.sha3_256(repr(t).encode("utf-8")).hexdigest()

    class UnifiedReceiptChain:  # noqa: D101 - mirrors szl_kernels._chain
        def __init__(self) -> None:
            self._lock = threading.RLock()
            self._records: List[Dict[str, Any]] = []

        @staticmethod
        def _digest_body(body: Dict[str, Any]) -> str:
            raw = json.dumps(
                body, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
            return hashlib.sha3_256(raw).hexdigest()

        def emit(self, kernel: str, op: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
            with self._lock:
                prev = self._records[-1]["digest"] if self._records else GENESIS
                seq = len(self._records)
                body = {
                    "seq": seq,
                    "kernel": str(kernel),
                    "op": str(op),
                    "attrs": attrs,
                    "prev": prev,
                }
                digest = self._digest_body(body)
                rec = dict(body, digest=digest, ts=time.time())
                self._records.append(rec)
                return rec

        def emit_lambda(
            self, score: float, threshold: float, passed: bool, k: int
        ) -> Dict[str, Any]:
            return self.emit(
                "lambda_gate",
                "lambda_gate",
                {
                    "score": float(score),
                    "threshold": float(threshold),
                    "passed": bool(passed),
                    "k": int(k),
                    "advisory": True,
                    "lambda_status": (
                        "Conjecture 1 (open) — advisory only, NOT proven trust"
                    ),
                },
            )

        def emit_energy(self, measurement: Dict[str, Any]) -> Dict[str, Any]:
            joules = measurement.get("joules", None)
            return self.emit(
                "energy_core",
                "measure_energy",
                {
                    "label": str(measurement.get("label", "UNKNOWN")),
                    "joules": (None if joules is None else float(joules)),
                    "source": str(measurement.get("source", "")),
                },
            )

        def head(self) -> str:
            with self._lock:
                return self._records[-1]["digest"] if self._records else GENESIS

        def count(self) -> int:
            with self._lock:
                return len(self._records)

        def tail(self, n: int = 10) -> List[Dict[str, Any]]:
            with self._lock:
                return list(self._records[-n:])

        def kernels_touched(self) -> List[str]:
            with self._lock:
                seen: List[str] = []
                for r in self._records:
                    if r["kernel"] not in seen:
                        seen.append(r["kernel"])
                return seen

        def verify(self):
            with self._lock:
                prev = GENESIS
                for i, rec in enumerate(self._records):
                    body = {
                        k: rec[k] for k in ("seq", "kernel", "op", "attrs", "prev")
                    }
                    if rec["prev"] != prev or rec["digest"] != self._digest_body(body):
                        return (False, len(self._records), i)
                    prev = rec["digest"]
                return (True, len(self._records), -1)

        def to_json(self) -> str:
            with self._lock:
                return json.dumps(
                    self._records, sort_keys=True, separators=(",", ":")
                )

        @staticmethod
        def verify_json(blob: str):
            records = json.loads(blob)
            prev = GENESIS
            for i, rec in enumerate(records):
                body = {k: rec[k] for k in ("seq", "kernel", "op", "attrs", "prev")}
                if rec["prev"] != prev or rec[
                    "digest"
                ] != UnifiedReceiptChain._digest_body(body):
                    return (False, len(records), i)
                prev = rec["digest"]
            return (True, len(records), -1)


__all__ = ["GENESIS", "UnifiedReceiptChain", "tensor_digest", "_CHAIN_SOURCE"]
