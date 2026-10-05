"""Write random-game positions with their legal moves, features and scores, so
the Swift engine can check it implements exactly the same rules.

    python -m alphago_lite.make_test_vectors --out ../MacApp/Tests/GoEngineTests/test_vectors.json
"""
import argparse
import json
import random

import numpy as np

from .go import PASS, Position


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--games", type=int, default=40)
    args = ap.parse_args()
    rng = random.Random(0)
    cases = []
    for g in range(args.games):
        pos = Position()
        moves = []
        while not pos.is_over():
            legal = [m for m, ok in enumerate(pos.legal_mask()) if ok and m != PASS]
            # pass rarely so games get long and full of captures and ko
            m = rng.choice(legal) if legal and rng.random() > 0.02 else PASS
            moves.append(m)
            pos = pos.play(m)
            if len(moves) % 15 == 0 or pos.is_over():
                cases.append({
                    "moves": list(moves),
                    "board": pos.board,
                    "ko": pos.ko,
                    "to_play": pos.to_play,
                    "legal": [int(x) for x in pos.legal_mask()],
                    "score": pos.area_score(),
                    "features_sum": [float(s) for s in pos.features().reshape(6, -1).sum(1)],
                    "features_hash": int((pos.features().reshape(-1) * np.arange(486)).sum()),
                })
    with open(args.out, "w") as f:
        json.dump({"cases": cases}, f)
    print(f"wrote {len(cases)} cases")


if __name__ == "__main__":
    main()
