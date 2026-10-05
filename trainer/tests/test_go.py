import numpy as np

from alphago_lite.go import PASS, Position, apply_symmetry, move_to_str, KOMI, BLACK, WHITE
from alphago_lite.mcts import run_searches


def pt(s):
    c = "ABCDEFGHJ".index(s[0]); r = 9 - int(s[1:])
    return r * 9 + c


def setup(black=(), white=(), to_play=BLACK):
    b = [0] * 81
    for s in black: b[pt(s)] = 1
    for s in white: b[pt(s)] = -1
    return Position(board=b, to_play=to_play)


def test_capture_corner():
    p = setup(black=["B9"], white=["A9"])
    p = p.play(pt("A8"))
    assert p.board[pt("A9")] == 0


def test_suicide_illegal():
    p = setup(black=["B9", "A8"], to_play=WHITE)
    assert not p.legal_mask()[pt("A9")]


def test_suicide_that_captures_is_legal():
    # White A9 has no liberties of its own but captures black B9 + A8.
    p = setup(black=["B9", "A8"], white=["C9", "B8", "A7"], to_play=WHITE)
    assert p.legal_mask()[pt("A9")]
    q = p.play(pt("A9"))
    assert q.board[pt("B9")] == 0 and q.board[pt("A8")] == 0


def test_ko():
    # White B9 captures black C9; black may not retake at C9 immediately.
    p = setup(black=["A9", "B8", "C9"], white=["C8", "D9"], to_play=WHITE)
    q = p.play(pt("B9"))
    assert q.board[pt("C9")] == 0 and q.ko == pt("C9")
    assert not q.legal_mask()[pt("C9")]
    r = q.play(pt("J1")).play(pt("J2"))  # after a move elsewhere the ko is lifted
    assert r.ko == -1 and r.legal_mask()[pt("C9")]


def test_score_empty_and_area():
    assert Position().area_score() == -KOMI
    p = setup(black=["E" + str(i) for i in range(1, 10)])  # a wall: both sides are black area
    assert p.area_score() == 81 - KOMI


def test_two_passes_end():
    p = Position().play(PASS).play(PASS)
    assert p.is_over() and p.winner() == WHITE


def test_symmetry_roundtrip():
    x = np.random.rand(6, 9, 9).astype(np.float32); pi = np.random.rand(82)
    for k in range(8):
        y, q = apply_symmetry(x, pi, k)
        assert np.isclose(y.sum(), x.sum()) and q[81] == pi[81]


class Uniform:
    """No knowledge: uniform policy, zero value. Only terminal results guide the search."""

    def __call__(self, planes):
        return np.zeros((len(planes), 82), np.float32), np.zeros(len(planes), np.float32)


def test_mcts_finds_winning_pass():
    # White just passed and black owns the board: passing ends the game with a win.
    p = setup(black=["E" + str(i) for i in range(1, 10)])
    p.passes = 1
    root = run_searches([p], Uniform(), 300)[0]
    assert int(root.N.argmax()) == PASS
