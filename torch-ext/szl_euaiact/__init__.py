# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""szl_euaiact — compliance as a BYPRODUCT of cryptographic provenance.

Auto-derive an EU AI Act Annex IV-style technical-documentation SKELETON from a
szl_kernels governance record (a UnifiedReceiptChain export), instead of writing
it as a separate manual workflow.

    from szl_euaiact import derive_annex_iv, to_markdown
    doc = derive_annex_iv({"system": {"name": "MyModel", ...}, "chain": chain_list})
    md  = to_markdown(doc)        # human-readable
    import json; json.dumps(doc)  # machine-readable JSON

HONESTY (binding):
  * DRAFT SKELETON only — NOT legal advice, NOT a conformity guarantee. Labelled
    as such on every artifact.
  * Λ advisory (Conjecture 1, OPEN) — a recorded pass is never proven trust.
  * Energy reported MEASURED-only; no measured figure => disclosed as such, never
    fabricated.
  * honest-BLOCKED events from szl_blocked are surfaced as governance evidence.
  * Missing human input => explicit TODO markers; nothing is invented.
  * Prior-art named honestly (EU AI Act Annex IV; SPDX 3.0 AI profile / AI BOM).

Stdlib only. No torch, no network, no disk writes from inside this package.
"""
from ._annex_iv import (
    ANNEX_IV_ELEMENTS,
    DISCLAIMER,
    PRIOR_ART,
    SCHEMA_VERSION,
    derive_annex_iv,
    to_markdown,
)

__all__ = [
    "derive_annex_iv",
    "to_markdown",
    "DISCLAIMER",
    "PRIOR_ART",
    "SCHEMA_VERSION",
    "ANNEX_IV_ELEMENTS",
    "__version__",
]

__version__ = "0.1.0"
