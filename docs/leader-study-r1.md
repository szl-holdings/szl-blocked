# szl-blocked domain leader study r1 (propose-only)

Date: 2026-11-25. Method: web-verified leader landscape + owner-direct execution under standing authority GREENLIGHT-RULING-2026-11-24-K1 rank5 OUROBOROS_NEXT_TRANCHE. The Kimi governing seat remains stood down per explicit owner directive (disclosed); owner-direct nonce T18-OWNER-DIRECT-20261125-K1. This card is documentation only; it changes no code, CI, config, or existing PR status. All absorb actions are FUTURE PROPOSALS (non-authorizing); implementation and merges remain separately reviewed and gated. Head SHA at study time: 20f352245bd768786dbd9ef55ad71f15da4a4730.

## Domain: gated/blocked ops kernel slot (capability-allow gate, Kernel Hub publish pipeline, quarantined legacy artifacts)

## Leaders studied (web-verified 2026-11-25)

1. huggingface_hub — https://github.com/huggingface/huggingface_hub — the Hub client whose kernel-repo refs the load/pin contract depends on; moat is immutable-revision pinning discipline, and this repo already teaches pinning a v1 branch commit over a moving branch.
2. Casbin — https://github.com/casbin/casbin — the canonical access-control model library; moat is explicit policy-model expressiveness. The contrast is itself the lesson: szl-blocked deliberately stays a tiny exact-name capability match with hard DENY_INVALID_CAPABILITIES on malformed input, not a general policy engine.
3. PyTorch — https://github.com/pytorch/pytorch — the extension/kernel ecosystem this repo builds torch-ext CPU and universal variants for; moat is the extension packaging discipline, not a claim this repo is FlashAttention, has MEASURED CUDA benches, or any latency numbers.

## Absorb actions (FUTURE PROPOSALS, non-authorizing)

1. (huggingface_hub) Propose documenting the three-identity separation (GitHub source commit, model-repo commit, kernel-repo commit) in one table with the only-writer rule for hf-kernel-publish unchanged.
2. (Casbin) Propose a doc-only boundary note: which casbin-style policy semantics are intentionally out of scope so the abstain-on-missing-capability and hard-deny semantics never drift.
3. (PyTorch) Propose documenting the build/torch-cpu and build/torch-universal same-bytes contract with its existing fresh-runner get_kernel verification; no dependency bump is proposed.
4. (baseline) Propose preserving the model.joblib QUARANTINE warning (never joblib.load) and the weekly Hub re-verification disclosure verbatim.
5. (baseline) Propose keeping maturity honest: SOFTWARE_LIMITED per szl-hf-frontier#7; a successful load is not a product qualification; no SLSA level or signing claim is made.

## Do not do (owner-direct lane doctrine)

Do not merge, bypass required checks, fabricate signatures, attestations, or signing/provenance claims, or claim implementation beyond this card. Verification status stays verification-unknown unless separately measured. Lambda stays Conjecture 1 (advisory, never a theorem).
