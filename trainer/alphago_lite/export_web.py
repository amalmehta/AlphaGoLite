"""Export a training run for the website.

    python -m alphago_lite.export_web --run runs/main --out ../web

Writes:
  model/alphagolite.onnx  the network, for ONNX Runtime Web
  data/metrics.json       per-generation metrics + head-to-head checks
  data/games.json         sample self-play games for the replay viewer
"""
import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from .export_app import pick_games
from .go import NUM_PLANES, N
from .net import load_net


def export_onnx(weights, out_path):
    net = load_net(weights)
    example = torch.zeros(1, NUM_PLANES, N, N)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(net, example, str(out_path), input_names=["planes"],
                      output_names=["policy", "value"], opset_version=13,
                      dynamic_axes={"planes": {0: "batch"}, "policy": {0: "batch"}, "value": {0: "batch"}})
    return net


def check_parity(net, path, n=20):
    sess = ort.InferenceSession(str(path))
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(n):
        x = (rng.random((1, NUM_PLANES, N, N)) < 0.3).astype(np.float32)
        with torch.no_grad():
            p, v = net(torch.from_numpy(x))
        op, ov = sess.run(None, {"planes": x})
        worst = max(worst, float(np.abs(op - p.numpy()).max()), float(np.abs(ov - v.numpy()).max()))
    return worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/main")
    ap.add_argument("--out", default="../web")
    ap.add_argument("--gen", type=int, default=None)
    args = ap.parse_args()
    run, out = Path(args.run), Path(args.out)

    metrics = json.loads((run / "metrics.json").read_text())
    gen = args.gen if args.gen is not None else metrics["generations"][-1]["gen"]
    model = out / "model" / "alphagolite.onnx"
    net = export_onnx(run / "weights" / f"gen_{gen:04d}.pt", model)
    print(f"exported generation {gen}; ONNX vs PyTorch max abs diff {check_parity(net, model):.2e}")

    metrics["exported_gen"] = gen
    strength = run / "strength.json"
    checks = json.loads(strength.read_text()) if strength.exists() else []
    metrics["strength_checks"] = [c for c in checks if c["gen"] == gen]
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "metrics.json").write_text(json.dumps(metrics))
    games = pick_games(run)
    (out / "data" / "games.json").write_text(json.dumps({"games": games}))
    print(f"wrote metrics and {len(games)} replay games to {out / 'data'}")


if __name__ == "__main__":
    main()
