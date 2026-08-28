#!/usr/bin/env python3
"""Forge a REAL trained surrogate for szl-blocked.
Kernel = ground truth. Surrogate = fast BLOCK/ALLOW triage: given a governed
request's structural observables (capabilities, action, flags) plus the advisory
Λ axes, predict what GovernedGate.decide(...) would return — ALLOW, BLOCK by
HARD security, or BLOCK by advisory Λ. The kernel's deny-by-default policy and
non-compensatory Λ gate are the sole labeler; a sample of labels is re-audited
by full kernel replay and MUST agree or the run fails loudly.
Seeded, receipted, reproducible."""
import json, os, random, sys, time, hashlib, platform
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(os.path.join(_here, "build", "torch-universal")):
    sys.path.insert(0, os.path.join(_here, "build", "torch-universal"))  # in-repo run
else:
    sys.path.insert(0, "/tmp/kernel-probe/szl-blocked/build/torch-universal")  # forge-dev run
import szl_blocked as sb
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score
import joblib

SEED = 20260721
random.seed(SEED); np.random.seed(SEED)
T0 = time.time()

# The universe the surrogate learns over. These mirror the kernel's own rules:
#   allow_if_capability("run_norm")   -> needs capability present
#   deny_if_action_in({"exfiltrate","delete_all","drop_table"}) -> hard blocklist
#   deny_if_flag("exfiltration")      -> hard flag deny
CAPS_UNIVERSE = ["run_norm", "read_public", "write_logs", "call_model"]
REQUIRED_CAP = "run_norm"
BLOCKLIST = {"exfiltrate", "delete_all", "drop_table"}
ACTIONS = ["summarize", "rms_norm", "classify", "embed",
           "exfiltrate", "delete_all", "drop_table"]
HARD_FLAG = "exfiltration"
LAMBDA_THRESHOLD = 0.5

CLASSES = ["ALLOW", "BLOCK_HARD", "BLOCK_ADVISORY"]


def build_policy():
    """The fixed hard policy the surrogate is trained against (deny-by-default)."""
    return sb.deny_by_default([
        sb.allow_if_capability(REQUIRED_CAP),
        sb.deny_if_flag(HARD_FLAG),
        sb.deny_if_action_in(BLOCKLIST),
    ])


def synth_request():
    """Synthesize a governed request + advisory axes across the decision space."""
    caps = [c for c in CAPS_UNIVERSE if random.random() < 0.5]
    action = random.choice(ACTIONS)
    flag = 1 if random.random() < 0.18 else 0
    req = {"capabilities": caps, "action": action}
    if flag:
        req[HARD_FLAG] = True
    # advisory Λ axes: sometimes absent (abstain), sometimes present with a
    # spread that straddles the threshold; occasionally a zero-route axis.
    if random.random() < 0.25:
        axes = None
    else:
        k = random.randint(2, 4)
        axes = [round(random.uniform(0.0, 1.0), 4) for _ in range(k)]
        if random.random() < 0.12:
            axes[random.randrange(k)] = 0.0  # non-compensatory zero-route
    return req, axes


def kernel_label(req, axes):
    """Ground truth: exactly what GovernedGate.decide returns, plus which
    authority dominated (fresh chain per call — decision is chain-independent)."""
    gate = sb.GovernedGate(policy=build_policy(), lambda_threshold=LAMBDA_THRESHOLD,
                           chain=sb.UnifiedReceiptChain())
    d = gate.decide(request=req, gov_axes=axes)
    if d.allowed:
        return "ALLOW"
    if d.dominant == sb.DOMINANT_HARD:
        return "BLOCK_HARD"
    return "BLOCK_ADVISORY"


def features(req, axes):
    """Structural observables of the request + advisory axes. These are what a
    fast pre-gate can see WITHOUT running the policy chain."""
    caps = set(req.get("capabilities") or [])
    action = req.get("action")
    has_req_cap = int(REQUIRED_CAP in caps)
    n_caps = len(caps)
    action_blocklisted = int(action in BLOCKLIST)
    flag_set = int(bool(req.get(HARD_FLAG)))
    # advisory axes summary (non-compensatory: min matters most)
    if axes is None:
        axes_present = 0
        k = 0
        amin = -1.0
        amean = -1.0
        any_zero = 0
    else:
        axes_present = 1
        k = len(axes)
        amin = min(axes) if axes else -1.0
        amean = sum(axes) / len(axes) if axes else -1.0
        any_zero = int(any(a <= 0.0 for a in axes))
    return [has_req_cap, n_caps, action_blocklisted, flag_set,
            axes_present, k, amin, amean, any_zero]


FEATURE_NAMES = ["has_required_capability", "n_capabilities", "action_blocklisted",
                 "hard_flag_set", "advisory_axes_present", "n_axes",
                 "axes_min", "axes_mean", "axes_any_zero"]

# ---- generate ----
N = 24000
X, y = [], []
audit_idx = set(random.sample(range(N), 600))
audit_checked = 0
policy = build_policy()
for i in range(N):
    req, axes = synth_request()
    lbl = kernel_label(req, axes)
    X.append(features(req, axes)); y.append(lbl)
    # ground-truth audit: independent fresh kernel replay must agree
    if i in audit_idx:
        gate2 = sb.GovernedGate(policy=build_policy(), lambda_threshold=LAMBDA_THRESHOLD,
                                chain=sb.UnifiedReceiptChain())
        d2 = gate2.decide(request=req, gov_axes=axes)
        replay = ("ALLOW" if d2.allowed else
                  ("BLOCK_HARD" if d2.dominant == sb.DOMINANT_HARD else "BLOCK_ADVISORY"))
        assert replay == lbl, f"kernel disagrees on sample {i}: {replay} != {lbl} req={req} axes={axes}"
        audit_checked += 1

X = np.array(X, dtype=np.float64); y = np.array(y)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
clf = HistGradientBoostingClassifier(random_state=SEED, max_iter=300, early_stopping=True)
clf.fit(Xtr, ytr)
pred = clf.predict(Xte)
acc = accuracy_score(yte, pred)  # this IS the fidelity: agreement% vs kernel on held-out
per_class_recall = {c: float(recall_score(yte == c, pred == c, zero_division=0)) for c in CLASSES}

out = os.path.dirname(os.path.abspath(__file__))
joblib.dump(clf, f"{out}/model.joblib")
model_sha = hashlib.sha256(open(f"{out}/model.joblib", "rb").read()).hexdigest()
receipt = {
  "artifact": "SZLHOLDINGS/szl-blocked surrogate v1",
  "role": "BLOCK/ALLOW decision triage surrogate — kernel remains ground truth",
  "generator": {"script": "scripts/forge.py", "seed": SEED, "kernel_version": sb.__version__,
                 "kernel_labelled": True, "kernel_audited_samples": audit_checked,
                 "policy": "deny_by_default([allow_if_capability('run_norm'), deny_if_flag('exfiltration'), deny_if_action_in({'exfiltrate','delete_all','drop_table'})])",
                 "lambda_threshold": LAMBDA_THRESHOLD},
  "data": {"rows": int(len(y)), "classes": CLASSES,
            "class_counts": {c: int((y == c).sum()) for c in CLASSES},
            "split": "80/20 stratified", "features": FEATURE_NAMES,
            "feature_policy": "structural observables of the request + advisory Λ axes only; the surrogate never signs receipts or replaces the policy chain"},
  "model": {"type": "sklearn.HistGradientBoostingClassifier",
             "params": {"max_iter": 300, "early_stopping": True, "random_state": SEED},
             "file": "model.joblib", "sha256": model_sha},
  "metrics_MEASURED": {"fidelity_vs_kernel_heldout": round(float(acc), 4),
                        "test_accuracy": round(float(acc), 4),
                        "per_class_recall": {k: round(v, 4) for k, v in per_class_recall.items()}},
  "environment": {"python": platform.python_version(), "sklearn": __import__("sklearn").__version__,
                   "numpy": np.__version__, "host": "replit 2-vCPU container",
                   "wall_seconds": round(time.time() - T0, 1)},
  "honesty": "Every number above is MEASURED by this run. Fidelity = agreement%% with GovernedGate.decide on a held-out split. The surrogate is a fast pre-gate; the kernel's honest-BLOCKED policy chain stays authoritative. Λ untouched = Conjecture 1.",
  "trained_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
with open(f"{out}/TRAINING_RECEIPT.json", "w") as f:
    json.dump(receipt, f, indent=2)
print(json.dumps(receipt["metrics_MEASURED"], indent=2))
print(f"rows={len(y)} kernel_audited_samples={audit_checked} wall={receipt['environment']['wall_seconds']}s")
