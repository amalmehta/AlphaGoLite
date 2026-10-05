"""Policy/value residual network (AlphaGo Zero architecture, scaled down)."""
import torch
import torch.nn as nn
import torch.nn.functional as F

from .go import N, NN, NUM_MOVES, NUM_PLANES

BLOCKS = 4
CHANNELS = 48


class ResBlock(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.c1 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        self.b1 = nn.BatchNorm2d(c)
        self.c2 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        self.b2 = nn.BatchNorm2d(c)

    def forward(self, x):
        y = F.relu(self.b1(self.c1(x)))
        y = self.b2(self.c2(y))
        return F.relu(x + y)


class PolicyValueNet(nn.Module):
    def __init__(self, blocks=BLOCKS, channels=CHANNELS):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(NUM_PLANES, channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(),
        )
        self.tower = nn.Sequential(*[ResBlock(channels) for _ in range(blocks)])
        self.p_conv = nn.Sequential(nn.Conv2d(channels, 2, 1, bias=False), nn.BatchNorm2d(2), nn.ReLU())
        self.p_fc = nn.Linear(2 * NN, NUM_MOVES)
        self.v_conv = nn.Sequential(nn.Conv2d(channels, 1, 1, bias=False), nn.BatchNorm2d(1), nn.ReLU())
        self.v_fc1 = nn.Linear(NN, 64)
        self.v_fc2 = nn.Linear(64, 1)

    def forward(self, x):
        """x: (B, 6, 9, 9). Returns policy logits (B, 82) and value (B, 1) in [-1, 1]
        from the point of view of the player to move."""
        h = self.tower(self.stem(x))
        p = self.p_fc(self.p_conv(h).flatten(1))
        v = torch.tanh(self.v_fc2(F.relu(self.v_fc1(self.v_conv(h).flatten(1)))))
        return p, v


class Evaluator:
    """Wraps a net for batched numpy inference."""

    def __init__(self, net):
        self.net = net.eval()

    @torch.inference_mode()
    def __call__(self, planes):
        x = torch.from_numpy(planes)
        logits, v = self.net(x)
        return logits.numpy(), v[:, 0].numpy()


def load_net(path):
    net = PolicyValueNet()
    net.load_state_dict(torch.load(path, map_location="cpu"))
    return net.eval()
