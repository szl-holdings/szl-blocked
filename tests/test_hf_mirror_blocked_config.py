"""szl-blocked specific checks for the release mirror ported from szl-lambda-gate.

Standard library and pytest only, so the CPU contract job can run it without
huggingface_hub or PyYAML.
"""
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "hf-mirror.yml"
MAP = ROOT / ".github" / "hf-mirror.json"
PUBLISHER = ROOT / "scripts" / "hf_mirror_release.py"
RENDERER = ROOT / "scripts" / "render_model_card.py"
spec = importlib.util.spec_from_file_location("hf_mirror_release_blocked", PUBLISHER)
assert spec and spec.loader
mirror = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirror)

# Paths whose bytes on Hub main e0789bc0 differ from the GitHub tree. The
# additive release lane must keep the Hub copy instead of overwriting it.
DIFFERING_OVERLAPS = {"LICENSE", "SECURITY.md", "build.toml", "scripts/eval.py", "scripts/forge.py"}


def only_target() -> dict:
    targets = json.loads(MAP.read_text(encoding="utf-8"))["targets"]
    assert len(targets) == 1
    return targets[0]


def run_blocks(text: str) -> list[str]:
    """Return the shell text of every `run:` key in the workflow."""
    lines = text.splitlines()
    blocks = []
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)(?:- )?run:\s*(.*)$", line)
        if not match:
            continue
        indent, value = len(match.group(1)), match.group(2)
        if value not in ("|", ">", "|-", ">-"):
            blocks.append(value)
            continue
        body = []
        for following in lines[index + 1:]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            body.append(following)
        blocks.append("\n".join(body))
    return blocks


def test_target_map_uses_lambda_gate_schema() -> None:
    item = only_target()
    assert item["slug"] == "blocked"
    assert item["hf_repo_id"] == "SZLHOLDINGS/szl-blocked"
    assert item["oidc_resource"] == item["hf_repo_id"]
    assert item["repo_type"] == "model"
    assert item["subdirectory"] == "."
    assert item["card_template"] == ""
    assert item["mirror_on_push"] is False
    assert item["preserve_hub_card"] is True
    assert item["required_card_metadata"] == {"library_name": "kernels", "license": "apache-2.0"}
    assert item["required_card_tags"] == ["doi:10.5281/zenodo.19944926"]


def test_preserved_hub_paths_are_exact_safe_files() -> None:
    paths = only_target()["preserve_hub_paths"]
    assert paths == sorted(set(paths))
    assert "README.md" not in paths
    assert DIFFERING_OVERLAPS <= set(paths)
    for name in paths:
        assert not name.endswith("/")
        mirror.safe_relative(name)


def test_stage_drops_preserved_paths_and_keeps_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".github").mkdir()
    shutil.copy(MAP, tmp_path / ".github" / "hf-mirror.json")
    stage = tmp_path / ".hfstage"
    for name in ("README.md", "torch-ext/szl_blocked/_gate.py", "scripts/hub_quarantine_joblib.py", *DIFFERING_OVERLAPS):
        (stage / name).parent.mkdir(parents=True, exist_ok=True)
        (stage / name).write_text(name, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HF_REPO_ID", "SZLHOLDINGS/szl-blocked")
    monkeypatch.setenv("HF_REPO_TYPE", "model")

    mirror.stage()

    staged = set(mirror.stage_files())
    assert staged == {"README.md", "torch-ext/szl_blocked/_gate.py", "scripts/hub_quarantine_joblib.py"}


def test_run_scripts_take_expressions_only_through_env() -> None:
    blocks = run_blocks(WORKFLOW.read_text(encoding="utf-8"))
    assert blocks, "no run: scripts found"
    for block in blocks:
        assert "${{" not in block


def test_actions_are_pinned_to_full_commit_shas() -> None:
    uses = re.findall(r"uses:\s*(\S+)", WORKFLOW.read_text(encoding="utf-8"))
    assert uses
    for ref in uses:
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref), ref


def test_old_workflow_defects_are_gone() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    publisher = PUBLISHER.read_text(encoding="utf-8")
    renderer = RENDERER.read_text(encoding="utf-8")

    assert "HF_OIDC_RESOURCE:" in workflow
    assert "only='${{ inputs.only }}'" not in workflow
    assert "hf auth whoami" not in workflow
    assert 'echo "HF_TOKEN=${{ secrets.HF_TOKEN }}"' not in workflow
    assert workflow.count("id-token: write") == 1
    for text in (workflow, publisher):
        assert "delete_tag" not in text
    assert "exist_ok" not in workflow
    create_tag = re.search(r"api\.create_tag\((.*?)\)\n", publisher, re.S)
    assert create_tag and "exist_ok=False" in create_tag.group(1)
    assert "from_template" not in renderer
