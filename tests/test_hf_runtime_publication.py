"""Publication must retain Hub assets, refuse races, and verify real readback."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("blocked_publication", ROOT / "scripts/publish_hf_runtime.py")
assert SPEC is not None and SPEC.loader is not None
publication = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = publication
SPEC.loader.exec_module(publication)


def git(cwd, *args, data=None):
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args], cwd=cwd, input=data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    ).stdout


@pytest.fixture
def hub(tmp_path):
    bare, seed = tmp_path / "hub.git", tmp_path / "seed"
    git(tmp_path, "init", "--bare", str(bare))
    git(tmp_path, "init", "--initial-branch=main", str(seed))
    git(seed, "config", "user.name", "Publication test")
    git(seed, "config", "user.email", "test@example.invalid")
    (seed / "README.md").write_bytes(b"curated Hub card\n")
    (seed / "model.joblib").write_bytes(b"opaque quarantined bytes; never execute")
    (seed / "build/torch-universal/szl_blocked").mkdir(parents=True)
    (seed / "build/torch-universal/szl_blocked/_gate.py").write_bytes(b"old kernel\n")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "test baseline\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    git(seed, "push", str(bare), "HEAD:refs/heads/main")
    parent = git(seed, "rev-parse", "HEAD").decode().strip()
    return bare, seed, parent


def test_payload_uses_immutable_git_blobs_and_closes_both_load_variants():
    revision = git(ROOT, "rev-parse", "HEAD").decode().strip()
    payload = publication.build_payload(ROOT, revision)
    binding = json.loads(payload[publication.BINDING_PATH])
    assert binding["source_revision"] == revision
    assert binding["source_repository"] == "szl-holdings/szl-blocked"
    assert binding["trained_weights_present"] is False
    for leaf in publication.PACKAGE_FILES:
        source = git(ROOT, "show", f"{revision}:torch-ext/szl_blocked/{leaf}")
        for variant in publication.VARIANTS:
            assert payload[f"build/{variant}/szl_blocked/{leaf}"] == source
    assert "README.md" not in payload and "model.joblib" not in payload
    for variant in publication.VARIANTS:
        metadata = json.loads(payload[f"build/{variant}/metadata.json"])
        assert metadata["kernel-sha"] == revision and metadata["kernel-dirty"] is False
    with pytest.raises(publication.PublicationError):
        publication.build_payload(ROOT, "main")


def test_preparation_is_read_only_and_apply_retains_all_unmanaged_blobs(hub, tmp_path):
    bare, _, parent = hub
    target = publication.GitTarget("kernel", str(bare), tmp_path / "candidate")
    payload = {"build/torch-universal/szl_blocked/_gate.py": b"new kernel\n"}
    row = target.prepare(parent, payload, "a" * 40)
    assert target.remote_head() == parent
    target.publish(row, payload)
    assert target.remote_head() == row["candidate_revision"]
    assert row["readback_verified"] is True
    assert row["unmanaged_blobs_preserved"] is True
    assert git(bare, "show", "main:README.md") == b"curated Hub card\n"
    assert git(bare, "show", "main:model.joblib") == b"opaque quarantined bytes; never execute"


def test_changed_parent_refuses_before_any_publication(hub, tmp_path):
    bare, _, parent = hub
    target = publication.GitTarget("model", str(bare), tmp_path / "candidate")
    with pytest.raises(publication.PublicationError, match="parent"):
        target.prepare("b" * 40, {"new.py": b"x"}, "a" * 40)
    assert target.remote_head() == parent


def test_race_after_preparation_keeps_other_writers_commit(hub, tmp_path):
    bare, seed, parent = hub
    target = publication.GitTarget("model", str(bare), tmp_path / "candidate")
    payload = {"new.py": b"x"}
    row = target.prepare(parent, payload, "a" * 40)
    (seed / "README.md").write_bytes(b"owner's newer card\n")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "test owner change\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    git(seed, "push", str(bare), "HEAD:refs/heads/main")
    newer = git(seed, "rev-parse", "HEAD").decode().strip()
    with pytest.raises(publication.PublicationError, match="parent"):
        target.publish(row, payload)
    assert target.remote_head() == newer


def test_corrupt_expected_readback_is_never_a_success(hub, tmp_path):
    bare, _, parent = hub
    target = publication.GitTarget("model", str(bare), tmp_path / "candidate")
    row = target.prepare(parent, {"new.py": b"actual"}, "a" * 40)
    with pytest.raises(publication.PublicationError, match="readback"):
        target.publish(row, {"new.py": b"corrupt"})
    assert not row.get("readback_verified", False)


def test_all_targets_preflight_before_first_push_and_partial_results_persist(tmp_path):
    first, second = mock.Mock(), mock.Mock()
    first.prepare.return_value = {"target": "model"}
    second.prepare.side_effect = publication.PublicationError("kernel parent moved")
    with pytest.raises(publication.PublicationError):
        publication.publish_targets([first, second], ["a" * 40, "b" * 40], {}, "c" * 40, lambda: None, [])
    first.publish.assert_not_called()
    second.prepare.side_effect = None
    second.prepare.return_value = {"target": "kernel"}
    second.publish.side_effect = publication.PublicationError("readback failed")
    rows = []
    with pytest.raises(publication.PublicationError):
        publication.publish_targets([first, second], ["a" * 40, "b" * 40], {}, "c" * 40, lambda: None, rows)
    assert len(rows) == 2
    first.publish.assert_called_once()
    assert rows[1]["target"] == "kernel"


def test_source_movement_after_preflight_refuses_any_write():
    target = mock.Mock()
    target.prepare.return_value = {"target": "model"}
    guard = mock.Mock(side_effect=publication.PublicationError("source moved"))
    with pytest.raises(publication.PublicationError):
        publication.publish_targets([target], ["a" * 40], {}, "b" * 40, guard, [])
    target.publish.assert_not_called()


def test_payload_runs_the_full_source_package_without_torch():
    revision = git(ROOT, "rev-parse", "HEAD").decode().strip()
    payload = publication.build_payload(ROOT, revision)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name, value in payload.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        for variant in publication.VARIANTS:
            result = subprocess.run([
                sys.executable, "-I", "-c",
                "import sys; sys.path.insert(0, sys.argv[1]); import szl_blocked as f; "
                "assert f.governed_call(lambda: 42).blocked; "
                "assert f.governed_call(lambda: 42).output is None; "
                "calls=[]; "
                "assert f.governed_call(lambda: calls.append(1), gov_axes=[1.,1.]).blocked; assert not calls",
                str(root / "build" / variant),
            ], capture_output=True, text=True)
            assert result.returncode == 0, result.stderr


def test_runtime_lane_stays_inside_the_existing_canonical_writer():
    text = (ROOT / '.github/workflows/hf-mirror.yml').read_text(encoding='utf-8')
    assert '  runtime-publication:' in text
    assert "inputs.publish_runtime" in text
    assert "&& !inputs.publish_runtime" in text
    assert 'test "$AUTH_MODE" = pat' in text
    assert 'test -z "$RELEASE_TAG"' in text
    assert 'test "$GITHUB_REF" = refs/heads/main' in text
    assert 'python scripts/publish_hf_runtime.py --apply' in text
    assert text.count('id-token: write') == 1
