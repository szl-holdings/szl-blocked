# szl-blocked

**SOFTWARE_LIMITED.** Software kernel slot for blocked / gated ops in the SZL kernel house. **Not a model. No weights. Not the pre-action core of a11oy.**

Source is this GitHub tree. Hub mirror: [`kernels/SZLHOLDINGS/szl-blocked`](https://huggingface.co/kernels/SZLHOLDINGS/szl-blocked). Card: [`SZLHOLDINGS/szl-blocked`](https://huggingface.co/SZLHOLDINGS/szl-blocked).

Public maturity stays limited while Hub residue (`model.joblib` if still listed) is quarantined and while product claims are forbidden by [szl-hf-frontier#7](https://github.com/szl-holdings/szl-hf-frontier/issues/7).

## What this is NOT

- Hub `model.joblib` is **QUARANTINED** executable serialization. Do not `joblib.load` it. GitHub source is the approved path.
- Not FlashAttention, not a drop-in blocker library
- No MEASURED latency or CUDA benches in this repo
- Not trained weights
- Not a production admission certificate for a-11-oy.com

## Load

```python
from kernels import get_kernel
get_kernel("SZLHOLDINGS/szl-blocked", revision="main", trust_remote_code=True)
```

A successful load is not a product qualification.

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.
