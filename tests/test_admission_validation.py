"""Invalid advisory inputs must never bypass a failed axis or run callbacks."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=["torch-ext", "build/torch-universal"])
def kernel(request):
    name = "_admission_" + request.param.replace("/", "_").replace("-", "_")
    package = ROOT / request.param / "szl_blocked"
    spec = importlib.util.spec_from_file_location(
        name, package / "__init__.py", submodule_search_locations=[str(package)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("threshold", [math.nan, math.inf, -math.inf, -0.01, 1.01])
def test_invalid_threshold_rejected(kernel, threshold):
    with pytest.raises(ValueError, match="threshold"):
        kernel.GovernedGate(lambda_threshold=threshold)


@pytest.mark.parametrize(
    "weights", [[1.0], [1.0, 1.0, 1.0], [], [-1.0, 2.0], [0.0, 0.0],
                [math.nan, 1.0], [math.inf, 1.0], [-math.inf, 1.0]],
)
def test_malformed_weights_rejected_before_callbacks_or_receipts(kernel, weights):
    calls = []
    chain = kernel.UnifiedReceiptChain()

    def policy(request):
        calls.append("policy")
        return kernel.PolicyResult(True, "explicit test permission")

    def operation():
        calls.append("operation")
        return 42

    with pytest.raises(ValueError, match="weight"):
        kernel.governed_call(
            operation, policy=policy, chain=chain,
            gov_axes=[0.9, 0.0], gov_weights=weights,
        )
    assert calls == []
    assert chain.count() == 0


def test_weights_without_axes_are_not_silently_ignored(kernel):
    with pytest.raises(ValueError, match="weight"):
        kernel.GovernedGate().decide(gov_axes=None, gov_weights=[1.0])


@pytest.mark.parametrize("bad_axis", [math.nan, math.inf, -math.inf, -1.0, 0.0])
def test_nonfinite_or_failed_axis_keeps_documented_zero_route(kernel, bad_axis):
    calls = []
    policy = lambda request: kernel.PolicyResult(True, "explicit permission")
    result = kernel.governed_call(
        lambda: calls.append("operation"), policy=policy,
        gov_axes=[0.9, bad_axis], gov_weights=[1.0, 0.0],
    )
    assert result.blocked is True
    assert result.output is None
    assert result.decision.advisory["score"] == 0.0
    assert calls == []


@pytest.mark.parametrize("threshold", [0.0, 0.5, 1.0])
def test_valid_boundary_thresholds_and_equal_axes(kernel, threshold):
    policy = lambda request: kernel.PolicyResult(True, "explicit permission")
    result = kernel.governed_call(
        lambda: 42, policy=policy, gov_axes=[1.0, 1.0],
        gov_weights=[2.0, 3.0], lambda_threshold=threshold,
    )
    assert result.allowed is True
    assert result.output == 42
    assert result.decision.advisory["score"] == pytest.approx(1.0)


@pytest.mark.parametrize("weights", [None, [1.0, 1.0], [1e308, 1e308], [0.0, 1.0]])
def test_valid_weights_preserve_expected_scores(kernel, weights):
    policy = lambda request: kernel.PolicyResult(True, "explicit permission")
    decision = kernel.GovernedGate(policy=policy).decide(
        gov_axes=[0.81, 1.0], gov_weights=weights,
    )
    expected = 1.0 if weights == [0.0, 1.0] else 0.9
    assert decision.advisory["score"] == pytest.approx(expected)


def test_hard_deny_still_dominates_valid_advisory(kernel):
    calls = []
    result = kernel.governed_call(
        lambda: calls.append("operation"), gov_axes=[1.0, 1.0],
        gov_weights=[1.0, 1.0],
    )
    assert result.blocked is True
    assert result.decision.dominant == kernel.DOMINANT_HARD
    assert calls == []


def test_mirrored_gate_sources_are_exact_bytes():
    assert (ROOT / "torch-ext/szl_blocked/_gate.py").read_bytes() == (
        ROOT / "build/torch-universal/szl_blocked/_gate.py"
    ).read_bytes()
