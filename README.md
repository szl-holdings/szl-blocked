# szl-blocked

Software kernel slot for blocked / gated ops in the SZL kernel house. **Not a model. No weights.**

Source is this GitHub tree. Hub mirror: [`kernels/SZLHOLDINGS/szl-blocked`](https://huggingface.co/kernels/SZLHOLDINGS/szl-blocked). Card: [`SZLHOLDINGS/szl-blocked`](https://huggingface.co/SZLHOLDINGS/szl-blocked).

## What this is NOT

- Not FlashAttention, not a drop-in blocker library
- No MEASURED latency or CUDA benches in this repo
- Not trained weights

## Load

```python
from kernels import get_kernel
get_kernel("SZLHOLDINGS/szl-blocked", revision="main", trust_remote_code=True)
```

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.
