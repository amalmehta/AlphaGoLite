"""Export a training run for the Mac app.

    python -m alphago_lite.export_app --run runs/main --out ../MacApp/Resources

Writes:
  AlphaGoLite.mlpackage   the latest network, as Core ML
  metrics.json            the run's per-generation metrics (Training dashboard)
  games.json              sample self-play games from early, middle and late
                          generations (AI vs AI replay)
"""
import argparse
import json
import shutil
from pathlib import Path

import coremltools as ct
import numpy as np
import torch

from .go import NUM_PLANES, N
from .net import load_net


class _Wrapped(torch.nn.Module):
    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, x):
        return self.net(x)


def export_coreml(weights, out_path):
    net = load_net(weights)
    example = torch.zeros(1, NUM_PLANES, N, N)
    traced = torch.jit.trace(_Wrapped(net).eval(), example)
    mlmodel = ct.convert(
        traced,
        inputs=[ct.TensorType(name="planes", shape=example.shape, dtype=np.float32)],
        outputs=[ct.TensorType(name="policy"), ct.TensorType(name="value")],
        convert_to="mlprogram",
        compute_precision=ct.precision.FLOAT32,
        minimum_deployment_target=ct.target.macOS13,
    )
    mlmodel.short_description = "AlphaGo Lite 9x9 policy/value network"
    if Path(out_path).exists():
        shutil.rmtree(out_path)
    mlmodel.save(str(out_path))
    return net, mlmodel


def check_parity(net, mlmodel, n=20):
    """Max abs difference between PyTorch and Core ML outputs on random boards."""
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(n):
        x = (rng.random((1, NUM_PLANES, N, N)) < 0.3).astype(np.float32)
        with torch.no_grad():
            p, v = net(torch.from_numpy(x))
        out = mlmodel.predict({"planes": x})
        worst = max(worst, float(np.abs(out["policy"] - p.numpy()).max()),
                    float(np.abs(out["value"] - v.numpy()).max()))
    return worst


def pick_games(run):
    files = sorted((run / "games").glob("gen_*.json"))
    if not files:
        return []
    picks = sorted({0, len(files) // 4, len(files) // 2, len(files) - 1})
    out = []
    for i in picks:
        d = json.loads(files[i].read_text())
        for j, g in enumerate(d["games"][:3]):
            g = dict(g, generation=d["generation"], title=f"Generation {d['generation']} — game {j + 1}")
            out.append(g)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/main")
    ap.add_argument("--out", default="../MacApp/Resources")
    ap.add_argument("--gen", type=int, default=None, help="generation to export (default: latest)")
    args = ap.parse_args()
    run, out = Path(args.run), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    metrics = json.loads((run / "metrics.json").read_text())
    gen = args.gen if args.gen is not None else metrics["generations"][-1]["gen"]
    net, mlmodel = export_coreml(run / "weights" / f"gen_{gen:04d}.pt", out / "AlphaGoLite.mlpackage")
    print(f"exported generation {gen}; Core ML vs PyTorch max abs diff {check_parity(net, mlmodel):.2e}")
    metrics["exported_gen"] = gen
    strength = run / "strength.json"
    metrics["strength_checks"] = json.loads(strength.read_text()) if strength.exists() else []
    (out / "metrics.json").write_text(json.dumps(metrics))
    games = pick_games(run)
    (out / "games.json").write_text(json.dumps({"games": games}))
    print(f"wrote metrics ({len(metrics['generations'])} generations) and {len(games)} replay games to {out}")


if __name__ == "__main__":
    main()
