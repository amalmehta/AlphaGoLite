"""Batched PUCT Monte Carlo tree search.

Many independent trees (one per game) are searched in lock-step: each
simulation picks one leaf per tree and all leaves are evaluated by the network
in a single batch. Values are always from the point of view of the player to
move at the node where they are stored.
"""
import math

import numpy as np

from .go import NUM_MOVES, NUM_PLANES, N

C_PUCT = 1.5
FPU_REDUCTION = 0.25


class Node:
    __slots__ = ("pos", "legal", "penalty", "P", "N", "W", "V", "total", "children", "expanded")

    def __init__(self, pos):
        self.pos = pos
        self.children = {}
        self.expanded = False
        self.legal = self.penalty = None
        self.P = self.N = self.W = None
        self.V = 0.0
        self.total = 0

    def expand(self, logits, value):
        legal = np.asarray(self.pos.legal_mask(), dtype=bool)
        x = np.where(legal, logits, -np.inf)
        x = np.exp(x - x.max())
        self.P = x / x.sum()
        self.legal = legal
        self.penalty = np.where(legal, 0.0, -1e9)
        self.N = np.zeros(NUM_MOVES)
        self.W = np.zeros(NUM_MOVES)
        self.V = float(value)
        self.expanded = True

    def select(self):
        """PUCT. Unvisited moves get a first-play-urgency value: the node's
        own value minus a reduction that grows with the policy mass already
        explored (as in Leela Zero)."""
        visited = self.N > 0
        fpu = self.V - FPU_REDUCTION * math.sqrt(self.P[visited].sum())
        q = self.W / np.maximum(self.N, 1) + (~visited) * fpu
        u = self.P * (C_PUCT * math.sqrt(self.total + 1)) / (1 + self.N)
        return int((q + u + self.penalty).argmax())

    def add_noise(self, rng, alpha=0.12, eps=0.25):
        idx = np.flatnonzero(self.legal)
        noise = rng.dirichlet([alpha] * len(idx))
        self.P[idx] = (1 - eps) * self.P[idx] + eps * noise


def terminal_value(pos):
    """Game result from the point of view of pos.to_play."""
    return float(pos.winner() * pos.to_play)


def _descend(root):
    """Walk to a leaf. Returns (path, leaf, value-or-None)."""
    node = root
    path = []
    while True:
        a = node.select()
        path.append((node, a))
        child = node.children.get(a)
        if child is None:
            child = Node(node.pos.play(a))
            node.children[a] = child
        if child.pos.is_over():
            return path, child, terminal_value(child.pos)
        if not child.expanded:
            return path, child, None
        node = child


def _backup(path, v):
    """v is from the point of view of the leaf's player to move."""
    for node, a in reversed(path):
        v = -v
        node.N[a] += 1
        node.W[a] += v
        node.total += 1


def run_searches(positions, evaluator, sims, rng=None, noise=False, roots=None):
    """Search every position for `sims` simulations. Returns the root nodes."""
    if roots is None:
        roots = [Node(p) for p in positions]
    fresh = [r for r in roots if not r.expanded]
    if fresh:
        logits, values = evaluator(np.stack([r.pos.features() for r in fresh]))
        for r, l, v in zip(fresh, logits, values):
            r.expand(l, v)
    if noise:
        for r in roots:
            r.add_noise(rng)
    buf = np.empty((len(roots), NUM_PLANES, N, N), dtype=np.float32)
    for _ in range(sims):
        pending = []
        for r in roots:
            path, leaf, v = _descend(r)
            if v is None:
                buf[len(pending)] = leaf.pos.features()
                pending.append((path, leaf))
            else:
                _backup(path, v)
        if pending:
            logits, values = evaluator(buf[: len(pending)])
            for (path, leaf), l, v in zip(pending, logits, values):
                leaf.expand(l, v)
                _backup(path, float(v))
    return roots


def root_value(root):
    """Mean value of the searched root, point of view of root's player to move."""
    n = root.N.sum()
    return float(root.W.sum() / n) if n else root.V
