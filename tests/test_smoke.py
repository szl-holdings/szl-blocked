# SPDX-License-Identifier: Apache-2.0
"""CPU smoke: import the kernel and prove honest BLOCK never runs fn."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "torch-ext"))

from szl_blocked import UnifiedReceiptChain, deny_if_action_in, governed_call


def test_import_and_honest_block():
    ran = {"n": 0}

    def fn(v):
        ran["n"] += 1
        return v * 2

    policy = deny_if_action_in({"exfiltrate", "delete_all"})
    chain = UnifiedReceiptChain()

    blocked = governed_call(
        fn, policy=policy, chain=chain, request={"action": "exfiltrate"}, args=(21,)
    )
    assert blocked.blocked is True
    assert blocked.output is None
    assert ran["n"] == 0

    allowed = governed_call(
        fn, policy=policy, chain=chain, request={"action": "summarize"}, args=(21,)
    )
    assert allowed.blocked is False
    assert allowed.output == 42
    assert ran["n"] == 1

    ok, depth, brk = chain.verify()
    assert ok is True and brk == -1 and depth >= 2


if __name__ == "__main__":
    test_import_and_honest_block()
    print("OK — szl_blocked CPU smoke")
