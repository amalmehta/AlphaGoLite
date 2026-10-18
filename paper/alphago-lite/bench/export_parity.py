"""Record export and rule parity for the paper (writes export_parity.json).

    ../../../trainer/.venv/bin/python export_parity.py

- Network: max |output - PyTorch| for the Core ML package and the ONNX file the apps ship,
  on 20 random binary input boards (same check as trainer/alphago_lite/export_*.py).
- Rules: number of parity cases in the shared test vectors (checked by the Swift and Node tests).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "trainer"))

import coremltools as ct  # noqa: E402

from alphago_lite.export_app import check_parity as coreml_parity  # noqa: E402
from alphago_lite.export_web import check_parity as onnx_parity  # noqa: E402
from alphago_lite.net import load_net  # noqa: E402

gen = json.loads((ROOT / "web/data/metrics.json").read_text())["exported_gen"]
net = load_net(ROOT / f"trainer/runs/main/weights/gen_{gen:04d}.pt")
vectors = json.loads((ROOT / "MacApp/Tests/GoEngineTests/test_vectors.json").read_text())["cases"]
out = {
    "gen": gen,
    "inputs": 20,
    "coreml_max_abs_diff": coreml_parity(net, ct.models.MLModel(str(ROOT / "MacApp/Resources/AlphaGoLite.mlpackage"))),
    "onnx_max_abs_diff": onnx_parity(net, ROOT / "web/model/alphagolite.onnx"),
    "rule_parity_cases": len(vectors),
    "rule_parity_games": 40,
}
(HERE / "export_parity.json").write_text(json.dumps(out, indent=1))
print(out)
