# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""szl-blocked's advisory Λ against the szl.lambda/v1 vectors: pinned divergences.

The vectors are vendored from szl-lambda-gate (see
``tests/fixtures/lambda_v1_vectors.SOURCE``). Two layers are checked, each
against both shipped copies of the kernel:

* **Λ layer.** ``_gate._lambda_advisory_score(axes, weights)`` must give each
  vector's Λ within its ``value_tol``, or refuse with a ``ValueError`` whose
  ``code`` is the v1 error code. It predates v1: it clamps x > 1 to 1, routes
  NaN, ±Inf and negative axes to 0, renormalises weights, allows zero weights,
  coerces with ``float()``, and refuses without a code. Every such row is
  pinned exactly in ``LAMBDA_DIVERGENCE`` (FUSION_BRIEF E5).
* **Gate layer.** ``GovernedGate(lambda_threshold=tau).decide(...)`` under an
  explicit hard ALLOW must give the fail-closed image of the v1 verdict: GO ->
  ALLOW, NO_GO -> BLOCK, ABSTAIN -> BLOCK (an abstention is never a pass),
  BLOCK -> refuse (raise before any policy callback or receipt). Every other
  outcome is pinned exactly in ``GATE_DIVERGENCE``.

Nothing here is skipped or xfailed: a divergence is asserted as today's exact
behaviour, so any silent change, in the kernel or in the vectors, fails. The
slice that aligns the kernel with v1 edits these tables in the same change.

The file also pins the implicit-threshold warning: ``GovernedGate`` and
``governed_call`` warn when ``lambda_threshold`` is not given, because the
implicit advisory θ = 0.5 differs from the admit contract's policy_tau 0.8
(szl-math-core I-4). The value is unchanged.

Λ is advisory. Λ uniqueness is Conjecture 1 (open); nothing here uses it.
Stdlib and pytest only; no torch.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import struct
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ["torch-ext", "build/torch-universal"]
FIXTURES = ROOT / "tests" / "fixtures"
VECTORS_PATH = FIXTURES / "lambda_v1_vectors.json"
SOURCE_PATH = FIXTURES / "lambda_v1_vectors.SOURCE"

VECTORS_DOC = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
VECTORS = VECTORS_DOC["vectors"]
VECTOR_IDS = [v["id"] for v in VECTORS]
BY_ID = {v["id"]: v for v in VECTORS}
ERROR_IDS = {v["id"] for v in VECTORS if "error" in v["expect"]}


@pytest.fixture(params=COPIES)
def kernel(request):
    name = "_conformance_" + request.param.replace("/", "_").replace("-", "_")
    package = ROOT / request.param / "szl_blocked"
    spec = importlib.util.spec_from_file_location(
        name, package / "__init__.py", submodule_search_locations=[str(package)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _decode_scalar(value):
    # "f64:<16 hex>" is an IEEE-754 binary64; any other JSON value (true, null,
    # a plain string, an integer) is passed to the kernel unchanged.
    if isinstance(value, str) and value.startswith("f64:"):
        return struct.unpack(">d", bytes.fromhex(value[4:]))[0]
    return value


def _decode(value):
    if isinstance(value, list):
        return [_decode_scalar(v) for v in value]
    return _decode_scalar(value)


def _canonical_sha256(obj) -> str:
    raw = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_source():
    fields = {}
    for line in SOURCE_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        key, sep, value = line.partition(": ")
        assert sep, "malformed .SOURCE line: {!r}".format(line)
        assert key not in fields, "duplicate .SOURCE key: {!r}".format(key)
        fields[key] = value
    return fields


# -- the vendored vectors are the upstream bytes -----------------------------

def test_vendored_vectors_match_their_source_record():
    source = _read_source()
    assert source["repo"] == "szl-holdings/szl-lambda-gate"
    assert re.fullmatch(r"[0-9a-f]{40}", source["commit"])
    assert source["path"] == "spec/lambda_v1_vectors.json"
    assert _canonical_sha256(VECTORS_DOC) == source["canonical_sha256"]
    lf_bytes = VECTORS_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(lf_bytes).hexdigest() == source["lf_bytes_sha256"]
    assert int(source["vectors"]) == len(VECTORS) == 50


def test_vectors_are_the_v1_schema_with_unique_ids():
    assert VECTORS_DOC["schema"] == "szl.lambda/v1.vectors"
    assert len(set(VECTOR_IDS)) == len(VECTOR_IDS)
    for vector in VECTORS:
        expect = vector["expect"]
        assert ("error" in expect) != ("value_f64" in expect), vector["id"]
        assert expect["verdict"] in ("GO", "NO_GO", "ABSTAIN", "BLOCK"), vector["id"]
        assert vector["value_tol"] > 0, vector["id"]


# -- Λ layer: _lambda_advisory_score ----------------------------------------

# vector id -> what _lambda_advisory_score(axes, weights) does today, on a row
# where v1 refuses with a code:
#   ("value", x):              returns (x, len(axes)) with |got - x| <= 1e-12;
#   ("raises", Error, regex):  raises Error with no v1 code; str(error) fullmatches regex.
_SQRT_0_9 = 0.9486832980505138  # [1, 0.9] at equal weights: what [1.5, 0.9] reads as
_UNCODED = {
    "positive": re.escape("gov_weights must include a positive weight"),
    "match": re.escape("gov_weights must match the number of gov_axes"),
    "finite": re.escape("gov_weights must be finite and non-negative"),
    "require": re.escape("gov_weights require gov_axes"),
    # CPython's own text; "real " was added in 3.10.
    "float_none": r"float\(\) argument must be a string or a (real )?number, not 'NoneType'",
}
LAMBDA_DIVERGENCE = {
    # E5 clamp: an axis above 1 is read as 1, so [1.5, 0.9] scores sqrt(0.9).
    # tau is not an input at this layer, so tau_precedes_axis_error is the same row.
    "x_gt_1": ("value", _SQRT_0_9),
    "precedence_axis_before_weight": ("value", _SQRT_0_9),
    "tau_precedes_axis_error": ("value", _SQRT_0_9),
    # E5 zero-route: a NaN, ±Inf or negative axis scores 0.0 instead of being refused.
    "nan_axis": ("value", 0.0),
    "pos_inf_axis": ("value", 0.0),
    "neg_inf_axis": ("value", 0.0),
    "negative_axis": ("value", 0.0),
    "precedence_nonfinite_before_range_a": ("value", 0.0),
    "precedence_nonfinite_before_range_b": ("value", 0.0),
    # E5 renormalisation: weights off the unit sum are rescaled, not refused.
    "w_unnormalised_2_2": ("value", 0.7200000000000001),
    "weight_sum_outside_tol": ("value", 0.6708203932505283),
    # Zero weights are allowed (w >= 0), so a zero-weighted axis drops out.
    "w_zero_weight": ("value", 0.5),
    # float() coercion: a bool or a numeric string is read as a number.
    "type_bool_axis": ("value", _SQRT_0_9),
    "type_string_axis": ("value", 0.9),
    "type_bool_weight": ("value", 0.5),
    # Refused, but without a v1 code.
    "empty": ("raises", ValueError, _UNCODED["positive"]),
    "empty_axes_nonempty_weights": ("raises", ValueError, _UNCODED["match"]),
    "e5_dropped_axis_renormalised": ("raises", ValueError, _UNCODED["match"]),
    "length_mismatch_extra_weight": ("raises", ValueError, _UNCODED["match"]),
    "e5_negative_weight": ("raises", ValueError, _UNCODED["finite"]),
    "weight_nan": ("raises", ValueError, _UNCODED["finite"]),
    "weight_pos_inf": ("raises", ValueError, _UNCODED["finite"]),
    "weight_neg_inf": ("raises", ValueError, _UNCODED["finite"]),
    "type_axes_not_array": ("raises", ValueError, _UNCODED["require"]),
    "type_null_axis": ("raises", TypeError, _UNCODED["float_none"]),
}


def test_lambda_table_names_only_rows_v1_refuses():
    assert set(LAMBDA_DIVERGENCE) <= ERROR_IDS
    for vid, pinned in LAMBDA_DIVERGENCE.items():
        assert pinned[0] in ("value", "raises"), vid


def test_lambda_acceptance_rows_are_pinned_exactly():
    # szl-math-core §3, szl-blocked column.
    assert LAMBDA_DIVERGENCE["x_gt_1"] == ("value", 0.9486832980505138)
    assert LAMBDA_DIVERGENCE["nan_axis"] == ("value", 0.0)
    assert LAMBDA_DIVERGENCE["pos_inf_axis"] == ("value", 0.0)
    assert LAMBDA_DIVERGENCE["negative_axis"] == ("value", 0.0)
    assert LAMBDA_DIVERGENCE["w_unnormalised_2_2"] == ("value", 0.7200000000000001)
    assert LAMBDA_DIVERGENCE["w_zero_weight"] == ("value", 0.5)
    assert LAMBDA_DIVERGENCE["empty"][:2] == ("raises", ValueError)


@pytest.mark.parametrize("vid", VECTOR_IDS)
def test_lambda_advisory_score_against_vector(kernel, vid):
    vector = BY_ID[vid]
    expect = vector["expect"]
    axes, weights = _decode(vector["axes"]), _decode(vector["weights"])
    # The package is re-executed per test; its submodule is cached in sys.modules.
    score = importlib.import_module(kernel.__name__ + "._gate")._lambda_advisory_score

    if vid in LAMBDA_DIVERGENCE:
        pinned = LAMBDA_DIVERGENCE[vid]
        if pinned[0] == "value":
            got, k = score(axes, weights)
            assert k == len(axes)
            assert abs(got - pinned[1]) <= 1e-12, (got, pinned[1])
        else:
            _, error, pattern = pinned
            with pytest.raises(error) as info:
                score(axes, weights)
            assert type(info.value) is error
            assert re.fullmatch(pattern, str(info.value)), str(info.value)
            assert getattr(info.value, "code", None) is None
        return

    if "error" in expect:
        # Conformant refusal: a ValueError carrying the v1 code.
        with pytest.raises(ValueError) as info:
            score(axes, weights)
        assert getattr(info.value, "code", None) == expect["error"]
        return

    got, k = score(axes, weights)
    assert k == len(axes)
    expected = _decode_scalar(expect["value_f64"])
    assert math.isfinite(got)
    assert abs(got - expected) <= vector["value_tol"], (got, expected)


# -- gate layer: GovernedGate.decide under an explicit hard ALLOW ------------

ALLOW_OUTCOME, BLOCK_OUTCOME, REFUSE_OUTCOME = "ALLOW", "BLOCK", "REFUSE"
# The fail-closed image of each v1 verdict in szl-blocked terms.
FAIL_CLOSED_IMAGE = {
    "GO": ALLOW_OUTCOME,
    "NO_GO": BLOCK_OUTCOME,
    "ABSTAIN": BLOCK_OUTCOME,
    "BLOCK": REFUSE_OUTCOME,
}

# vector id -> what the gate does today where it differs from that image.
GATE_DIVERGENCE = {
    # The advisory layer does not veto invalid input: with a hard ALLOW, fn runs.
    "x_gt_1": ALLOW_OUTCOME,  # E5 clamp, Λ 0.9487 >= 0.8
    "precedence_axis_before_weight": ALLOW_OUTCOME,  # E5 clamp
    "type_bool_axis": ALLOW_OUTCOME,  # True read as 1.0
    "type_string_axis": ALLOW_OUTCOME,  # "0.9" read as 0.9
    # No tie band: score >= θ passes at, and just above, θ.
    "tie_exact": ALLOW_OUTCOME,
    "tie_inside_above": ALLOW_OUTCOME,
    "tie_multi_axis_at_own_value": ALLOW_OUTCOME,
    # θ = 0 is accepted, so a zero-vetoed Λ = 0.0 passes 0.0 >= 0.0.
    "tau_zero_would_admit_veto": ALLOW_OUTCOME,
    # Vetoed as a low score instead of refused as invalid input. Closed, but
    # the receipt reads as an advisory veto, not a refusal of the input.
    "nan_axis": BLOCK_OUTCOME,
    "pos_inf_axis": BLOCK_OUTCOME,
    "neg_inf_axis": BLOCK_OUTCOME,
    "negative_axis": BLOCK_OUTCOME,
    "precedence_nonfinite_before_range_a": BLOCK_OUTCOME,
    "precedence_nonfinite_before_range_b": BLOCK_OUTCOME,
    "w_unnormalised_2_2": BLOCK_OUTCOME,  # renormalised to 0.72 < 0.8
    "weight_sum_outside_tol": BLOCK_OUTCOME,  # renormalised to 0.6708 < 0.8
    "w_zero_weight": BLOCK_OUTCOME,  # 0.5 < 0.8
    "type_bool_weight": BLOCK_OUTCOME,  # weights [1, 0]: 0.5 < 0.8
    "tau_bool": BLOCK_OUTCOME,  # θ = float(True) = 1.0; 0.9121 < 1.0
}

# With a hard ALLOW, these inputs run the wrapped op although v1 never gives GO.
ADVISORY_PASSES_WITHOUT_GO = frozenset({
    "x_gt_1",
    "precedence_axis_before_weight",
    "type_bool_axis",
    "type_string_axis",
    "tie_exact",
    "tie_inside_above",
    "tie_multi_axis_at_own_value",
    "tau_zero_would_admit_veto",
})


def _gate_outcome(kernel, vector):
    """Run one vector through GovernedGate; return (outcome, calls, receipts)."""
    calls = []

    def policy(request):
        calls.append("policy")
        return kernel.PolicyResult(True, "explicit test permission")

    chain = kernel.UnifiedReceiptChain()
    tau = _decode_scalar(vector["tau"])
    axes, weights = _decode(vector["axes"]), _decode(vector["weights"])
    with warnings.catch_warnings():
        # Every threshold here is explicit, so the implicit-θ warning must not fire.
        warnings.simplefilter("error")
        try:
            gate = kernel.GovernedGate(policy=policy, lambda_threshold=tau, chain=chain)
            decision = gate.decide(gov_axes=axes, gov_weights=weights)
        except (ValueError, TypeError):
            return REFUSE_OUTCOME, calls, chain.count()
    if decision.verdict == kernel.ALLOW:
        assert decision.dominant == kernel.DOMINANT_NONE
        return ALLOW_OUTCOME, calls, chain.count()
    assert decision.verdict == kernel.BLOCK
    assert decision.dominant == kernel.DOMINANT_ADVISORY
    return BLOCK_OUTCOME, calls, chain.count()


def test_gate_table_names_only_real_divergences():
    for vid, outcome in GATE_DIVERGENCE.items():
        assert vid in BY_ID, vid
        assert outcome in (ALLOW_OUTCOME, BLOCK_OUTCOME, REFUSE_OUTCOME), vid
        assert outcome != FAIL_CLOSED_IMAGE[BY_ID[vid]["expect"]["verdict"]], vid


def test_gate_rows_that_run_without_go_are_exactly_these():
    passes = {vid for vid, outcome in GATE_DIVERGENCE.items() if outcome == ALLOW_OUTCOME}
    assert passes == ADVISORY_PASSES_WITHOUT_GO
    assert all(BY_ID[vid]["expect"]["verdict"] != "GO" for vid in passes)


@pytest.mark.parametrize("vid", VECTOR_IDS)
def test_governed_gate_against_vector(kernel, vid):
    vector = BY_ID[vid]
    outcome, calls, receipts = _gate_outcome(kernel, vector)
    expected = GATE_DIVERGENCE.get(vid, FAIL_CLOSED_IMAGE[vector["expect"]["verdict"]])
    assert outcome == expected
    if outcome == REFUSE_OUTCOME:
        # A refusal happens before any policy callback or receipt.
        assert calls == [] and receipts == 0
    else:
        assert calls == ["policy"] and receipts == 1


# -- the implicit advisory θ 0.5 warns; the value is unchanged ---------------

_IMPLICIT_MESSAGE = re.compile(
    r"lambda_threshold not given.*implicit advisory threshold 0\.5.*policy_tau 0\.8",
    re.DOTALL,
)


def _explicit_allow(kernel):
    return lambda request: kernel.PolicyResult(True, "explicit test permission")


def test_governed_gate_warns_when_threshold_is_implicit(kernel):
    with pytest.warns(DeprecationWarning, match=_IMPLICIT_MESSAGE) as record:
        gate = kernel.GovernedGate(policy=_explicit_allow(kernel))
    assert len(record) == 1
    assert "GovernedGate" in str(record[0].message)
    # Attributed to the caller, not to the kernel.
    assert Path(record[0].filename).resolve() == Path(__file__).resolve()
    assert gate.lambda_threshold == 0.5
    assert type(gate.lambda_threshold) is float


@pytest.mark.parametrize("threshold", [0.5, 0.8, 0.0, 1.0])
def test_governed_gate_is_silent_when_threshold_is_explicit(kernel, threshold):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        gate = kernel.GovernedGate(policy=_explicit_allow(kernel), lambda_threshold=threshold)
    assert gate.lambda_threshold == threshold


def test_implicit_threshold_decides_exactly_as_explicit_half(kernel):
    axes = [0.95, 0.95, 0.95, 0.40]  # hidden_weak: Λ 0.7653 passes θ 0.5
    with pytest.warns(DeprecationWarning):
        implicit = kernel.GovernedGate(policy=_explicit_allow(kernel))
    explicit = kernel.GovernedGate(policy=_explicit_allow(kernel), lambda_threshold=0.5)
    a = implicit.decide(gov_axes=axes)
    b = explicit.decide(gov_axes=axes)
    assert a.verdict == b.verdict == kernel.ALLOW
    assert a.as_attrs() == b.as_attrs()
    assert a.receipt["digest"] == b.receipt["digest"]


def test_explicit_none_threshold_is_still_refused(kernel):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(TypeError):
            kernel.GovernedGate(lambda_threshold=None)


def test_governed_call_warns_once_when_threshold_is_implicit(kernel):
    with pytest.warns(DeprecationWarning, match=_IMPLICIT_MESSAGE) as record:
        result = kernel.governed_call(
            lambda: 42, policy=_explicit_allow(kernel), gov_axes=[0.95, 0.95, 0.95, 0.40]
        )
    assert len(record) == 1
    assert "governed_call" in str(record[0].message)
    assert Path(record[0].filename).resolve() == Path(__file__).resolve()
    assert result.allowed is True and result.output == 42
    assert result.decision.advisory["threshold"] == 0.5


def test_governed_call_is_silent_when_threshold_is_explicit(kernel):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = kernel.governed_call(
            lambda: 42, policy=_explicit_allow(kernel),
            gov_axes=[0.95, 0.95, 0.95, 0.40], lambda_threshold=0.8,
        )
    assert result.blocked is True
    assert result.decision.dominant == kernel.DOMINANT_ADVISORY
