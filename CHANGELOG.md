# Changelog

## 2026-10-13

- One Hub writer: `hf-kernel-publish` (`.github/hf-kernels.json`, `scripts/szl_kernel_publish.py`)
  replaces `hf-mirror.yml` (release mirror and runtime-publication lanes), `hub-joblib-quarantine.yml`
  and their scripts, docs and tests. It builds both noarch variants with `szl_euaiact`, publishes the
  kernel repo `main` and `v1` fast-forward, verifies `get_kernel(version=1)` and `revision="main"`, then
  makes the model repository a pointer card (`build/`, stale scripts and plates pruned; `model.joblib`
  kept absent).
- The committed `build/torch-universal/` copy is removed; the kernel tests now run against the source
  and both generated variants (`tests/conftest.py`). No kernel code changed.

## 2026-08-28

- Quarantine joblib/pickle: forge no longer dumps `model.joblib`; eval refuses the file; Hub deletion is a dispatched PR with exact parent commit.
Honesty README. No kernel math changed.
