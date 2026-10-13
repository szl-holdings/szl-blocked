# szl-blocked

**SOFTWARE_LIMITED.** Software kernel slot for blocked / gated ops in the SZL kernel house. **Not a model. No weights. Not the pre-action core of a11oy.**

<!-- szl:header v1 -->
<!-- Native identity: szl-brand@4309f6fce89179331b0b3ed8c99494e76c5be256; Orbit v2 icon. -->
<p>
  <a href="https://github.com/szl-holdings">
    <img src="https://raw.githubusercontent.com/szl-holdings/szl-brand/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/logos/orbit-v2/suite/szl-icon-32.svg" alt="SZL Holdings — Orbit v2" width="32" height="32" />
  </a>
</p>

**Control before action. Evidence after.**

[Product](https://a-11-oy.com) · [Proof](https://a11oy.net) · [GitHub organization](https://github.com/szl-holdings)
<!-- /szl:header -->

Source is this GitHub tree. Hub mirror: [`kernels/SZLHOLDINGS/szl-blocked`](https://huggingface.co/kernels/SZLHOLDINGS/szl-blocked). Card: [`SZLHOLDINGS/szl-blocked`](https://huggingface.co/SZLHOLDINGS/szl-blocked).

The only writer of both Hub repositories is [`hf-kernel-publish`](.github/workflows/hf-kernel-publish.yml), configured in [`.github/hf-kernels.json`](.github/hf-kernels.json). A published release builds `build/torch-cpu` and `build/torch-universal` from `torch-ext/` at the release commit, pushes them fast-forward to the kernel repo's `main` and `v1` branches, verifies the result through `get_kernel` in a fresh job, and only then turns the model repository into a pointer card. A weekly job re-verifies what the Hub serves.

Public maturity stays limited while Hub residue (`model.joblib` if still listed) is quarantined and while product claims are forbidden by [szl-hf-frontier#7](https://github.com/szl-holdings/szl-hf-frontier/issues/7).

## What this is NOT

- Hub `model.joblib` is **QUARANTINED** executable serialization. Do not `joblib.load` it. GitHub source is the approved path.
- Not FlashAttention, not a drop-in blocker library
- No MEASURED latency or CUDA benches in this repo
- Not trained weights
- Not a production admission certificate for a-11-oy.com

## Load

```python
# pip install "kernels>=0.17.2" torch
from kernels import get_kernel

blocked = get_kernel("SZLHOLDINGS/szl-blocked", version=1, trust_remote_code=True)
```

`version=1` resolves the `v1` branch of the first-class kernel repository
[`kernels/SZLHOLDINGS/szl-blocked`](https://huggingface.co/kernels/SZLHOLDINGS/szl-blocked),
the stable API channel republished from this repository on every release. CPU hosts load
`build/torch-cpu`; CUDA and other hosts load `build/torch-universal`; both carry the same
bytes. The companion `szl_euaiact` package ships beside `szl_blocked` in each variant (the
[kernel card](hf/kernel-card.md) shows how to load it).

`trust_remote_code=True` permits execution of the selected repository's Python; the
narrowest form is `trust_remote_code=["SZLHOLDINGS/szl-blocked"]`. Review the GitHub source
commit named in the Hub's `SZL_KERNEL_SOURCE.json` before enabling it. For production, pin
an immutable kernel-repo commit of `v1` instead of the branch:

```python
from huggingface_hub import HfApi
from kernels import get_kernel

refs = HfApi().list_repo_refs("SZLHOLDINGS/szl-blocked", repo_type="kernel")
pin = next(b.target_commit for b in refs.branches if b.name == "v1")
blocked = get_kernel("SZLHOLDINGS/szl-blocked", revision=pin, trust_remote_code=["SZLHOLDINGS/szl-blocked"])
```

The GitHub source commit, the model-repository commit and the kernel-repo commit are
separate identities; only the last one is a kernel revision.

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

