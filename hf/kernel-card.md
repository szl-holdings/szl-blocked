---
license: apache-2.0
library_name: kernels
tags:
  - kernel
  - szl-holdings
  - governance
  - eu-ai-act
  - annex-iv
  - doi:10.5281/zenodo.19944926
---

<!-- Native artwork: szl-brand@4309f6fce89179331b0b3ed8c99494e76c5be256; Orbit v2 icon SHA-256 6e2b7d72a3af3d9602b79de41df0194ede6496a9661f057108ec224c0efc92e6. -->
<p><a href="https://github.com/szl-holdings"><img src="https://raw.githubusercontent.com/szl-holdings/szl-brand/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/logos/orbit-v2/suite/szl-icon-32.svg" alt="SZL Holdings — Orbit v2" width="40" height="40" /></a></p>

<p><small>Orbit v2 artwork © SZL Holdings · <a href="https://github.com/szl-holdings/szl-brand/blob/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/LICENSE">CC BY 4.0</a>. Page documentation remains Apache-2.0.</small></p>

# {{KERNEL_NAME}}

Honest-BLOCKED as a first-class governed-layer state: apply an explicit policy before a
function call, refuse verifiably instead of degrading, and record the outcome in a receipt
chain. Pure-Python (noarch) software kernel. **No trained weights.**

Published from GitHub
[{{GITHUB_REPOSITORY}}](https://github.com/{{GITHUB_REPOSITORY}}) by its
`hf-kernel-publish` workflow. GitHub is the source of truth; this repository is
written only by that workflow.

## Load it

```python
# pip install "kernels>=0.17.2" torch
from kernels import get_kernel

blocked = get_kernel("{{REPO_ID}}", version={{KERNEL_VERSION}}, trust_remote_code=True)

policy = blocked.deny_by_default([blocked.allow_if_capability("run_norm")])
res = blocked.governed_call(
    lambda x: x * 2, policy=policy,
    request={"capabilities": ["run_norm"], "action": "rms_norm"},
    lambda_threshold=0.5, args=(21,),
)
assert res.blocked is False and res.output == 42
```

- `version={{KERNEL_VERSION}}` resolves the `v{{KERNEL_VERSION}}` branch, the stable API channel. It is
  republished on every release. The `kernels` library refuses a call that names neither a
  version nor a revision.
- `trust_remote_code` is required: SZLHOLDINGS is not a trusted kernel publisher on the Hub.
  The narrowest form is `trust_remote_code=["{{REPO_ID}}"]`. It permits running this
  repository's Python; review the source commit named in `SZL_KERNEL_SOURCE.json` first.
- CPU hosts load `build/torch-cpu`; CUDA and other hosts load `build/torch-universal`.
  Both variants carry identical code, built from the same GitHub commit.
- A BLOCKED call never runs the function and its `output` is always `None`. A hard DENY
  dominates; the advisory Λ can only tighten (Λ uniqueness is Conjecture 1, open).

### Companion package `szl_euaiact`

Each variant also ships `szl_euaiact/` beside `szl_blocked/`. It derives an EU AI Act
Annex IV-style documentation **draft skeleton** from a receipt-chain export. It is not
legal advice and not a conformity guarantee. `get_kernel` imports only `szl_blocked`;
load the companion from the same snapshot:

```python
import importlib.util, sys
from pathlib import Path

pkg = Path(blocked.__file__).parent.parent / "szl_euaiact"
spec = importlib.util.spec_from_file_location(
    "szl_euaiact", pkg / "__init__.py", submodule_search_locations=[str(pkg)])
euaiact = importlib.util.module_from_spec(spec)
sys.modules["szl_euaiact"] = euaiact
spec.loader.exec_module(euaiact)
```

### Pin an exact build (production)

```python
from huggingface_hub import HfApi
from kernels import get_kernel

refs = HfApi().list_repo_refs("{{REPO_ID}}", repo_type="kernel")
pin = next(b.target_commit for b in refs.branches if b.name == "v{{KERNEL_VERSION}}")
blocked = get_kernel("{{REPO_ID}}", revision=pin, trust_remote_code=["{{REPO_ID}}"])
```

Record `pin` (a commit of this kernel repository) in your lockfile.
`SZL_KERNEL_SOURCE.json` in this repository names the GitHub commit each build came from.
Commits of the model repository
[{{MODEL_TWIN_URL}}]({{MODEL_TWIN_URL}}) are not kernel revisions and do not resolve here.

## What this is not

- Not trained weights, not a model. Do not `pickle`/`joblib.load` anything from the Hub.
- No measured latency, CUDA speedup, tokens/s or joules are claimed.
- A successful load or an ALLOW receipt is not a product qualification or a certificate
  for the surrounding application.
