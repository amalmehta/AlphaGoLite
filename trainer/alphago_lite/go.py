"""9x9 Go rules: simple ko, no suicide, Tromp-Taylor area scoring.

Points are indexed p = row * 9 + col. Move 81 is pass.
Colors: 1 = black, -1 = white, 0 = empty.

The Swift engine in MacApp/Sources/GoEngine/Go.swift mirrors this file exactly;
tests/test_vectors.json (written by make_test_vectors.py) keeps them in sync.
"""
import numpy as np

N = 9
NN = N * N
PASS = NN
NUM_MOVES = NN + 1
KOMI = 7.5
MAX_MOVES = 2 * NN  # game is scored after this many moves
NUM_PLANES = 6

BLACK, WHITE, EMPTY = 1, -1, 0


def _neighbors(p):
    r, c = divmod(p, N)
    out = []
    if r > 0:
        out.append(p - N)
    if r < N - 1:
        out.append(p + N)
    if c > 0:
        out.append(p - 1)
    if c < N - 1:
        out.append(p + 1)
    return tuple(out)


NEIGHBORS = tuple(_neighbors(p) for p in range(NN))


def _diagonals(p):
    r, c = divmod(p, N)
    return tuple((r + dr) * N + c + dc for dr in (-1, 1) for dc in (-1, 1)
                 if 0 <= r + dr < N and 0 <= c + dc < N)


DIAGONALS = tuple(_diagonals(p) for p in range(NN))


def _group(board, p):
    """Return (stones, liberties) of the group containing p."""
    color = board[p]
    stones = {p}
    libs = set()
    stack = [p]
    while stack:
        q = stack.pop()
        for n in NEIGHBORS[q]:
            v = board[n]
            if v == EMPTY:
                libs.add(n)
            elif v == color and n not in stones:
                stones.add(n)
                stack.append(n)
    return stones, libs


class Position:
    __slots__ = ("board", "prev_board", "to_play", "ko", "passes", "move_count", "max_moves")

    def __init__(self, board=None, prev_board=None, to_play=BLACK, ko=-1, passes=0, move_count=0,
                 max_moves=MAX_MOVES):
        self.board = board if board is not None else [EMPTY] * NN
        self.prev_board = prev_board if prev_board is not None else [EMPTY] * NN
        self.to_play = to_play
        self.ko = ko
        self.passes = passes
        self.move_count = move_count
        self.max_moves = max_moves

    def is_over(self):
        return self.passes >= 2 or self.move_count >= self.max_moves

    def legal_mask(self):
        """Boolean list of length 82. Pass is always legal."""
        board = self.board
        me = self.to_play
        gid = [-1] * NN
        libcount = []
        for p in range(NN):
            if board[p] != EMPTY and gid[p] < 0:
                color = board[p]
                g = len(libcount)
                gid[p] = g
                stack = [p]
                libs = set()
                while stack:
                    q = stack.pop()
                    for n in NEIGHBORS[q]:
                        v = board[n]
                        if v == EMPTY:
                            libs.add(n)
                        elif v == color and gid[n] < 0:
                            gid[n] = g
                            stack.append(n)
                libcount.append(len(libs))
        mask = [False] * NUM_MOVES
        mask[PASS] = True
        for p in range(NN):
            if board[p] != EMPTY or p == self.ko:
                continue
            for n in NEIGHBORS[p]:
                v = board[n]
                if v == EMPTY:
                    mask[p] = True
                    break
                lc = libcount[gid[n]]
                if (v == me and lc > 1) or (v == -me and lc == 1):
                    mask[p] = True
                    break
        return mask

    def search_mask(self):
        """legal_mask, except that passing is only allowed when every legal move
        would fill one of our own eyes or put our own stones in atari. Under area
        scoring such moves cost nothing, so games are played out until the board
        is settled (or the opponent has passed and we already win on the board) and Tromp-Taylor scoring counts it correctly (no dead stones
        left on the board). Used by the trainer's search and the web player
        (web/js/go.js searchMask); the Mac app still uses legal_mask."""
        board = self.board
        me = self.to_play
        gid = [-1] * NN
        libsets = []
        for p in range(NN):
            if board[p] != EMPTY and gid[p] < 0:
                color = board[p]
                g = len(libsets)
                gid[p] = g
                stack = [p]
                libs = set()
                while stack:
                    q = stack.pop()
                    for n in NEIGHBORS[q]:
                        v = board[n]
                        if v == EMPTY:
                            libs.add(n)
                        elif v == color and gid[n] < 0:
                            gid[n] = g
                            stack.append(n)
                libsets.append(libs)
        mask = [False] * NUM_MOVES
        mask[PASS] = True
        worthwhile = False
        for p in range(NN):
            if board[p] != EMPTY or p == self.ko:
                continue
            legal = captures = False
            own_eye = True
            libs = set()
            for n in NEIGHBORS[p]:
                v = board[n]
                if v == EMPTY:
                    legal = True
                    own_eye = False
                    libs.add(n)
                elif v == me:
                    ls = libsets[gid[n]]
                    if len(ls) > 1:
                        legal = True
                    libs |= ls
                else:
                    own_eye = False
                    if len(libsets[gid[n]]) == 1:
                        legal = captures = True
            if not legal:
                continue
            mask[p] = True
            if worthwhile:
                continue
            if own_eye:
                diag = DIAGONALS[p]
                bad = sum(1 for d in diag if board[d] == -me)
                if bad == 0 or (len(diag) == 4 and bad == 1):
                    continue  # filling a real eye
            libs.discard(p)
            if captures or len(libs) >= 2:
                worthwhile = True
        # After an opponent's pass (which under this rule means they had nothing
        # worthwhile left), passing back is allowed if we already win on the board.
        if worthwhile and not (self.passes == 1 and self.area_score() * me > 0):
            mask[PASS] = False
        return mask

    def play(self, m):
        """Return the position after move m. Assumes m is legal."""
        me = self.to_play
        if m == PASS:
            return Position(self.board, self.board, -me, -1, self.passes + 1, self.move_count + 1, self.max_moves)
        b = self.board[:]
        b[m] = me
        captured = []
        for n in NEIGHBORS[m]:
            if b[n] == -me:
                stones, libs = _group(b, n)
                if not libs:
                    for s in stones:
                        b[s] = EMPTY
                    captured.extend(stones)
        stones, libs = _group(b, m)
        if not libs:
            raise ValueError(f"suicide at {m}")
        ko = -1
        if len(captured) == 1 and len(stones) == 1 and len(libs) == 1:
            ko = captured[0]
        return Position(b, self.board, -me, ko, 0, self.move_count + 1, self.max_moves)

    def area_score(self):
        """Black area minus white area minus komi (Tromp-Taylor)."""
        board = self.board
        score = 0
        seen = [False] * NN
        for p in range(NN):
            v = board[p]
            if v != EMPTY:
                score += v
            elif not seen[p]:
                region = [p]
                seen[p] = True
                stack = [p]
                borders = set()
                while stack:
                    q = stack.pop()
                    for n in NEIGHBORS[q]:
                        w = board[n]
                        if w == EMPTY:
                            if not seen[n]:
                                seen[n] = True
                                region.append(n)
                                stack.append(n)
                        else:
                            borders.add(w)
                if len(borders) == 1:
                    score += len(region) * borders.pop()
        return score - KOMI

    def ownership(self):
        """Tromp-Taylor owner of each point (1 black, -1 white, 0 neutral)."""
        board = self.board
        own = list(board)
        seen = [False] * NN
        for p in range(NN):
            if board[p] == EMPTY and not seen[p]:
                region = [p]
                seen[p] = True
                stack = [p]
                borders = set()
                while stack:
                    q = stack.pop()
                    for n in NEIGHBORS[q]:
                        w = board[n]
                        if w == EMPTY:
                            if not seen[n]:
                                seen[n] = True
                                region.append(n)
                                stack.append(n)
                        else:
                            borders.add(w)
                if len(borders) == 1:
                    c = borders.pop()
                    for q in region:
                        own[q] = c
        return own

    def winner(self):
        """1 if black wins, -1 if white wins (komi .5 means no draws)."""
        return 1 if self.area_score() > 0 else -1

    def features(self):
        """(6, 9, 9) float32 planes, from the point of view of the player to move:
        own stones, opponent stones, own stones one move ago, opponent stones one
        move ago, all-ones if black to play, all-ones."""
        me = self.to_play
        b = np.asarray(self.board, dtype=np.int8)
        pb = np.asarray(self.prev_board, dtype=np.int8)
        f = np.zeros((NUM_PLANES, NN), dtype=np.float32)
        f[0] = b == me
        f[1] = b == -me
        f[2] = pb == me
        f[3] = pb == -me
        f[4] = 1.0 if me == BLACK else 0.0
        f[5] = 1.0
        return f.reshape(NUM_PLANES, N, N)


def move_to_str(m):
    if m == PASS:
        return "pass"
    r, c = divmod(m, N)
    return "ABCDEFGHJ"[c] + str(N - r)


# --- dihedral symmetries, used for training-data augmentation -------------

def _sym_perm(k):
    """Permutation of 81 points for symmetry k in 0..7: new[i] = old[perm[i]]."""
    idx = np.arange(NN).reshape(N, N)
    if k & 4:
        idx = idx.T
    idx = np.rot90(idx, k & 3)
    return idx.reshape(-1)


SYM_PERMS = [np.concatenate([_sym_perm(k), [PASS]]) for k in range(8)]


def apply_symmetry(planes, pi, k):
    """planes: (C, 9, 9); pi: (82,). Returns transformed copies."""
    perm = SYM_PERMS[k]
    C = planes.shape[0]
    p2 = planes.reshape(C, NN)[:, perm[:NN]].reshape(C, N, N)
    return p2, pi[perm]
