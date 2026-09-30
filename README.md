# szl-blocked

**SOFTWARE_LIMITED.** Software kernel slot for blocked / gated ops in the SZL kernel house. **Not a model. No weights. Not the pre-action core of a11oy.**

Source is this GitHub tree. Hub mirror: [`kernels/SZLHOLDINGS/szl-blocked`](https://huggingface.co/kernels/SZLHOLDINGS/szl-blocked). Card: [`SZLHOLDINGS/szl-blocked`](https://huggingface.co/SZLHOLDINGS/szl-blocked).

The [source-bound runtime publication contract](docs/hf-runtime-publication.md) describes the canonical writer, exact-source admission, asset preservation, and publication readback.

Public maturity stays limited while Hub residue (`model.joblib` if still listed) is quarantined and while product claims are forbidden by [szl-hf-frontier#7](https://github.com/szl-holdings/szl-hf-frontier/issues/7).

## What this is NOT

- Hub `model.joblib` is **QUARANTINED** executable serialization. Do not `joblib.load` it. GitHub source is the approved path.
- Not FlashAttention, not a drop-in blocker library
- No MEASURED latency or CUDA benches in this repo
- Not trained weights
- Not a production admission certificate for a-11-oy.com

## Load

Set `SZL_BLOCKED_HF_REVISION` to the immutable **first-class Kernel Hub** commit
from a verified publication of [`kernels/SZLHOLDINGS/szl-blocked`](https://huggingface.co/kernels/SZLHOLDINGS/szl-blocked). Use the `kernels`
client version qualified with that publication. The GitHub source commit,
model-type mirror commit, and Kernel Hub commit are separate identities.
An observed head, a branch name, or a successful import does not qualify a release.

`trust_remote_code=True` permits execution of the selected repository's Python.
Review that exact revision, its provenance and publication evidence before enabling it.
The format check below only rejects missing or mutable revision inputs; it does not
verify hashes, publisher authorization or compatibility. If that evidence is unavailable,
stop the Hub load and use separately reviewed local source for development.

```python
import os
import re

hf_revision = os.environ.get("SZL_BLOCKED_HF_REVISION", "")
if re.fullmatch(r"[0-9a-f]{40}", hf_revision) is None:
    raise ValueError("A verified immutable Kernel Hub revision is required")

from kernels import get_kernel

get_kernel("SZLHOLDINGS/szl-blocked", revision=hf_revision, trust_remote_code=True)
```

A successful load is not a product qualification.

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.

## Source-only development

Review [`torch-ext/szl_blocked/`](https://github.com/szl-holdings/szl-blocked/tree/6501dec69ad862a09806136f841a75d0b2219616/torch-ext/szl_blocked)
at that immutable GitHub source revision, separately from any Hub release.
With the source's dependencies already available, run from the reviewed checkout root:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("torch-ext").resolve()))
import szl_blocked as local_kernel
```

This selects local Python source rather than calling the Hub loader. Importing local
source also executes Python. This documentation check does not run that import,
install dependencies, qualify a runtime or establish a Hub publication.

