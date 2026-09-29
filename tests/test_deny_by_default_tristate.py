# SPDX-License-Identifier: Apache-2.0
"""Tri-state hard rules: a deny-only policy must deny (E4d regression).

A hard rule now answers ALLOW, DENY or ABSTAIN. Only an explicit ALLOW grants
permission, any DENY dominates, and a rule that does not fire ABSTAINS: it
speaks for nothing. Before this change a deny rule that did not fire returned
``allow=True``, which ``deny_by_default`` counted as an explicit ALLOW, so a
policy made only of deny rules allowed every request that tripped none of them.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ["torch-ext", "build/torch-universal"]


@pytest.fixture(params=COPIES)
def kernel(request):
    name = "_tristate_" + request.param.replace("/", "_").replace("-", "_")
    package = ROOT / request.param / "szl_blocked"
    spec = importlib.util.spec_from_file_location(
        name, package / "__init__.py", submodule_search_locations=[str(package)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _deny_only(kernel):
    return kernel.deny_by_default([
        kernel.deny_if_flag("exfiltration"),
        kernel.deny_if_action_in({"exfiltrate", "delete_all"}),
    ])


# -- PolicyResult carries a verdict; allow is derived from it ----------------

@pytest.mark.parametrize(
    "given, verdict, allow, code",
    [
        (True, "ALLOW", True, "OK"),
        (False, "DENY", False, "DENY"),
        ("ALLOW", "ALLOW", True, "OK"),
        ("DENY", "DENY", False, "DENY"),
        ("ABSTAIN", "ABSTAIN", False, "ABSTAIN"),
    ],
)
def test_policy_result_verdict_and_derived_allow(kernel, given, verdict, allow, code):
    r = kernel.PolicyResult(given, "why")
    assert r.verdict == verdict
    assert r.allow is allow
    assert r.code == code
    assert r.as_dict()["verdict"] == verdict
    assert r.as_dict()["allow"] is allow


def test_verdict_vocabulary_is_exported_from_gate(kernel):
    gate = importlib.import_module(kernel.__name__ + "._gate")
    assert (gate.ALLOW, gate.DENY, gate.ABSTAIN) == ("ALLOW", "DENY", "ABSTAIN")


@pytest.mark.parametrize("bad", ["allow", "PERMIT", "", "OK", "BLOCK"])
def test_unknown_verdict_string_fails_closed(kernel, bad):
    # Today any non-empty string is truthy and would read as ALLOW.
    with pytest.raises(ValueError, match="verdict"):
        kernel.PolicyResult(bad, "why")


def test_allow_cannot_drift_from_verdict(kernel):
    r = kernel.PolicyResult("ABSTAIN", "why")
    with pytest.raises(AttributeError):
        r.allow = True
    assert r.allow is False and r.verdict == "ABSTAIN"


# -- the three rules whose meaning changes ------------------------------------

def test_deny_if_flag_abstains_when_it_does_not_fire(kernel):
    rule = kernel.deny_if_flag("exfiltration")
    quiet = rule({})
    assert quiet.verdict == "ABSTAIN" and quiet.allow is False
    fired = rule({"exfiltration": True})
    assert fired.verdict == "DENY" and fired.code == "DENY_RULE:exfiltration"


def test_deny_if_action_in_abstains_when_it_does_not_fire(kernel):
    rule = kernel.deny_if_action_in({"exfiltrate"})
    quiet = rule({"action": "summarize"})
    assert quiet.verdict == "ABSTAIN" and quiet.allow is False
    fired = rule({"action": "exfiltrate"})
    assert fired.verdict == "DENY" and fired.code == "DENY_RULE:blocklist"


def test_allow_if_capability_abstains_rather_than_denies(kernel):
    rule = kernel.allow_if_capability("run_norm")
    granted = rule({"capabilities": ["run_norm"]})
    assert granted.verdict == "ALLOW" and granted.allow is True
    missing = rule({"capabilities": ["read_public"]})
    assert missing.verdict == "ABSTAIN"
    assert missing.code == "ABSTAIN_NO_CAPABILITY"
    assert missing.detail == {"required": "run_norm", "have": ["read_public"]}


# -- deny_by_default over tri-state rules -------------------------------------

def test_deny_only_policy_gives_deny_default(kernel):
    # E4d: this returned allow=True, code "OK" before the fix.
    r = _deny_only(kernel)({"action": "summarize"})
    assert r.allow is False
    assert r.verdict == "DENY"
    assert r.code == "DENY_DEFAULT"


def test_deny_only_policy_still_denies_by_rule_when_a_rule_fires(kernel):
    r = _deny_only(kernel)({"action": "delete_all"})
    assert r.verdict == "DENY" and r.code == "DENY_RULE:blocklist"


@pytest.mark.parametrize("allow_first", [True, False])
def test_allow_plus_firing_deny_gives_deny(kernel, allow_first):
    rules = [kernel.allow_if_capability("run_norm"), kernel.deny_if_flag("exfiltration")]
    if not allow_first:
        rules.reverse()
    r = kernel.deny_by_default(rules)({"capabilities": ["run_norm"], "exfiltration": True})
    assert r.verdict == "DENY" and r.code == "DENY_RULE:exfiltration"


def test_allow_plus_quiet_deny_gives_allow(kernel):
    policy = kernel.deny_by_default([
        kernel.allow_if_capability("run_norm"), kernel.deny_if_flag("exfiltration"),
    ])
    r = policy({"capabilities": ["run_norm"]})
    assert r.verdict == "ALLOW" and r.allow is True and r.code == "OK"


def test_allow_only_policy_gives_allow(kernel):
    r = kernel.deny_by_default([kernel.allow_if_capability("run_norm")])(
        {"capabilities": ["run_norm"]}
    )
    assert r.verdict == "ALLOW" and r.allow is True


def test_allow_only_policy_without_capability_gives_deny_default(kernel):
    # Before: the abstaining rule short-circuited as a hard deny with code
    # ABSTAIN_NO_CAPABILITY. Now it abstains and the default speaks.
    r = kernel.deny_by_default([kernel.allow_if_capability("run_norm")])({})
    assert r.verdict == "DENY" and r.code == "DENY_DEFAULT"


def test_empty_policy_gives_deny_default(kernel):
    r = kernel.deny_by_default([])({"capabilities": ["run_norm"]})
    assert r.verdict == "DENY" and r.code == "DENY_DEFAULT"
    r = kernel.deny_by_default()({})
    assert r.verdict == "DENY" and r.code == "DENY_DEFAULT"


def test_an_abstaining_allow_rule_does_not_stop_a_later_allow(kernel):
    # Meaning change: several allow_if_capability rules are now "any of",
    # not "all of". A missing capability abstains instead of denying.
    policy = kernel.deny_by_default([
        kernel.allow_if_capability("a"), kernel.allow_if_capability("b"),
    ])
    assert policy({"capabilities": ["b"]}).verdict == "ALLOW"
    assert policy({"capabilities": []}).code == "DENY_DEFAULT"


def test_all_abstaining_custom_rules_give_deny_default(kernel):
    abstain = lambda ctx: kernel.PolicyResult("ABSTAIN", "no opinion")
    r = kernel.deny_by_default([abstain, abstain])({})
    assert r.verdict == "DENY" and r.code == "DENY_DEFAULT"
    assert r.detail["n_rules"] == 2


# -- through the gate: refusal is first-class, the op never runs --------------

def test_governed_call_with_deny_only_policy_blocks_and_never_runs(kernel):
    calls = []
    chain = kernel.UnifiedReceiptChain()
    res = kernel.governed_call(
        lambda: calls.append("operation"), policy=_deny_only(kernel), chain=chain,
        request={"action": "summarize"}, gov_axes=[1.0, 1.0],
    )
    assert res.blocked is True and res.output is None
    assert calls == []
    assert res.decision.dominant == kernel.DOMINANT_HARD
    assert res.decision.policy["code"] == "DENY_DEFAULT"
    assert res.receipt["attrs"]["hard_code"] == "DENY_DEFAULT"
    assert chain.count() == 1


def test_a_bare_deny_rule_used_as_the_whole_policy_blocks(kernel):
    # A single deny rule passed straight to the gate is a deny-only policy too.
    calls = []
    res = kernel.governed_call(
        lambda: calls.append("operation"),
        policy=kernel.deny_if_action_in({"exfiltrate"}),
        request={"action": "summarize"},
    )
    assert res.blocked is True and calls == []
    assert res.decision.dominant == kernel.DOMINANT_HARD
    assert res.decision.policy["verdict"] == "ABSTAIN"
    assert "abstain" in res.decision.reason.lower()


def test_governed_call_with_allow_plus_quiet_deny_runs(kernel):
    policy = kernel.deny_by_default([
        kernel.allow_if_capability("run_norm"), kernel.deny_if_flag("exfiltration"),
    ])
    res = kernel.governed_call(
        lambda: 42, policy=policy, request={"capabilities": ["run_norm"]},
    )
    assert res.allowed is True and res.output == 42


# -- both shipped copies stay byte-identical ----------------------------------

@pytest.mark.parametrize("name", ["_gate.py", "_rules.py"])
def test_mirrored_sources_are_exact_bytes(name):
    assert (ROOT / "torch-ext/szl_blocked" / name).read_bytes() == (
        ROOT / "build/torch-universal/szl_blocked" / name
    ).read_bytes()
