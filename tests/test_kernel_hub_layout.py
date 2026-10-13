# SPDX-License-Identifier: Apache-2.0
"""The real szl-blocked config builds the Hub tree get_kernel loads (stdlib + git).

Runs scripts/szl_kernel_publish.py's build against this repository's own HEAD: both
noarch variants carry szl_blocked and its companion szl_euaiact, byte for byte from
torch-ext (LF), with no root shim and with the kernel card passing the lint.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_szl_kernel_publish_layout",
                                               ROOT / "scripts" / "szl_kernel_publish.py")
kp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = kp
_spec.loader.exec_module(kp)

CFG = kp.find_kernel(ROOT, "SZLHOLDINGS/szl-blocked")
HEAD = kp.resolve_commit(ROOT, "HEAD")


def test_config_maps_kernel_and_companion():
    assert [(p.src, p.name) for p in CFG.packages] == [
        ("torch-ext/szl_blocked", "szl_blocked"),
        ("torch-ext/szl_euaiact", "szl_euaiact"),
    ]
    assert CFG.version == 1 and CFG.version_branch == "v1"
    assert CFG.twin is not None and {"build/", "torch-ext/"} <= set(CFG.twin.prune_paths)


def test_head_build_is_the_torch_ext_source():
    payload = kp.build_payload(CFG, ROOT, HEAD)
    for variant in kp.VARIANTS:
        prefix = f"build/{variant}/"
        served = {p[len(prefix):]: d for p, d in payload.items() if p.startswith(prefix)}
        expected = {}
        for pkg in CFG.packages:
            for rel, data in kp.read_tree_files(ROOT, HEAD, pkg.src).items():
                expected[f"{pkg.name}/{rel}"] = data.replace(b"\r\n", b"\n")
        assert set(served) == set(expected) | {"metadata.json"}, variant
        for rel, data in expected.items():
            assert served[rel] == data, f"{variant}:{rel}"
        assert "__init__.py" not in served  # no shim: the loaded module is szl_blocked
        meta = json.loads(served["metadata.json"])
        assert meta["name"] == "szl-blocked" and meta["version"] == 1
        assert set(meta["digest"]["files"]) == set(expected)


def test_card_and_binding_name_the_version_channel():
    payload = kp.build_payload(CFG, ROOT, HEAD)
    card = payload["README.md"].decode("utf-8")
    assert 'get_kernel("SZLHOLDINGS/szl-blocked", version=1, trust_remote_code=True)' in card
    binding = json.loads(payload[kp.BINDING_PATH])
    assert binding["source_commit"] == HEAD
    assert binding["source_repository"] == "szl-holdings/szl-blocked"
