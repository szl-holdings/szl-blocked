# SPDX-License-Identifier: Apache-2.0
"""Smoke hook for hf-kernel-publish (szl-blocked).

`smoke(kernel)` receives the module that the `kernels` loader imported, from a local
build (check-local) or from the Hub (verify). Raise, or return False, to fail the run.
CPU-only, deterministic and fast. The result's repr is written to the receipt.

It proves the doctrine on the served bytes: a BLOCKED call never runs the function and
returns no output, an explicit ALLOW runs it, the receipt chain verifies, and the
companion `szl_euaiact` package shipped beside `szl_blocked` derives a draft from it.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _companion(kernel):
    pkg = Path(kernel.__file__).parent.parent / "szl_euaiact"
    if not (pkg / "__init__.py").is_file():
        raise AssertionError(f"companion szl_euaiact is not shipped beside {kernel.__file__}")
    name = f"_szl_euaiact_smoke_{abs(hash(str(pkg)))}"
    spec = importlib.util.spec_from_file_location(name, pkg / "__init__.py",
                                                  submodule_search_locations=[str(pkg)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def smoke(kernel):
    ran = []

    def op(value):
        ran.append(value)
        return value * 2

    policy = kernel.deny_by_default([kernel.allow_if_capability("smoke"),
                                     kernel.deny_if_action_in({"exfiltrate"})])
    chain = kernel.UnifiedReceiptChain()
    blocked = kernel.governed_call(op, policy=policy, chain=chain, lambda_threshold=0.5,
                                   request={"capabilities": ["smoke"], "action": "exfiltrate"},
                                   args=(21,))
    if blocked.blocked is not True or blocked.output is not None or ran:
        raise AssertionError("a hard DENY must block without running the op")
    allowed = kernel.governed_call(op, policy=policy, chain=chain, lambda_threshold=0.5,
                                   request={"capabilities": ["smoke"], "action": "summarize"},
                                   args=(21,))
    if allowed.blocked is not False or allowed.output != 42 or ran != [21]:
        raise AssertionError("an explicit ALLOW must run the op exactly once")
    deny_only = kernel.deny_by_default([kernel.deny_if_action_in({"exfiltrate"})])
    quiet = kernel.governed_call(op, policy=deny_only, lambda_threshold=0.5,
                                 request={"action": "summarize"}, args=(1,))
    if quiet.blocked is not True or ran != [21]:
        raise AssertionError("a deny-only policy must deny (tri-state rules)")
    ok, depth, brk = chain.verify()
    if ok is not True or brk != -1 or depth < 2:
        raise AssertionError(f"receipt chain must verify: {(ok, depth, brk)}")

    euaiact = _companion(kernel)
    import json

    doc = euaiact.derive_annex_iv({"system": {"name": "szl-blocked smoke"},
                                   "chain": json.loads(chain.to_json())})
    if not isinstance(doc, dict) or not euaiact.to_markdown(doc).strip():
        raise AssertionError("szl_euaiact must derive a draft from the chain export")
    return {"blocked": True, "allowed_output": allowed.output, "chain_depth": depth,
            "euaiact_schema": euaiact.SCHEMA_VERSION}
