# Source-bound Blocked runtime publication

The existing `hf-mirror.yml` is the canonical writer. Its explicit manual runtime
mode publishes GitHub's exact tested `szl_blocked` Python package to both existing
`SZLHOLDINGS/szl-blocked` distributions: the legacy model and first-class kernel.
Supply `publish_runtime=true`, `auth=pat`, no release tag, the exact reviewed main
SHA, and independently observed model/kernel main parent SHAs. The normal
additive tagged release and OIDC lanes retain their existing behavior and cannot
run alongside this runtime mode in the same invocation.

The runtime lane requires a verified source commit and its successful canonical
CPU contract. It reruns all source and publication tests before provider access.
Five immutable Git blobs from `torch-ext/szl_blocked` populate each of the CPU
and universal package slots. Loader metadata and `SZL_SOURCE_BINDING.json` bind
the resulting runtime files to the exact GitHub source SHA and SHA-256 hashes.

Both targets are prepared, and both authenticated Git write endpoints are
checked with dry-runs before the first push. Ordinary fast-forward pushes refuse
competing changes. GitHub main and each Hub parent are rechecked before mutation.
Every unmanaged path retains its exact mode/type/blob ID, including cards,
licenses, historical provenance, quarantined files, and other packages. The
publisher never deletes files, creates repositories, moves tags, changes
settings, or prints credentials. A fresh fetch and remote-head check verify
every managed byte and all preserved blobs after each write.

The two target commits cannot be atomic. A later provider failure is PARTIAL,
with earlier writes and their evidence retained. A changed parent requires fresh
observed inputs, never a force push. Actions stores publication or failure
evidence for 180 days. Runtime metadata version 1 is separate from the Python
package version 0.1.0.

This publishes software. It does not claim trained weights, a GPU benchmark,
new theorem membership, or production authorization. Existing advisory behavior
and pinned divergences are unchanged; hard denial remains dominant, and Lambda
remains Conjecture 1 and advisory.
