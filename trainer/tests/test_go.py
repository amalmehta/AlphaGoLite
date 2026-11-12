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


# --- pass rule (search_mask) and ownership targets ---------------------------

def test_search_mask_forbids_pass_on_open_board():
    p = Position()
    assert not p.search_mask()[PASS]
    assert p.search_mask()[:PASS] == p.legal_mask()[:PASS]


def test_search_mask_allows_pass_when_only_own_eyes_remain():
    # black owns the whole board except two separate one-point eyes (A9, J1)
    b = [1] * 81
    b[pt("A9")] = 0
    b[pt("J1")] = 0
    p = Position(board=b, to_play=BLACK)
    assert p.search_mask()[PASS]
    # white may only play suicide-free captures: none here, both points are suicide
    pw = Position(board=b, to_play=WHITE)
    assert pw.search_mask()[PASS]


def test_search_mask_allows_pass_when_only_self_atari_remains():
    # black group on the top edge with a single two-point eye space A9-B9:
    # filling either point is self-atari for the whole group, so pass is allowed
    black = [s + "8" for s in "ABCDEFGHJ"] + [s + "9" for s in "CDEFGHJ"]
    white = [s + "7" for s in "ABCDEFGHJ"] + [s + r for s in "ABCDEFGHJ" for r in "123456"]
    p = setup(black=black, white=white, to_play=BLACK)
    m = p.search_mask()
    assert m[pt("A9")] and m[pt("B9")]   # still legal
    assert m[PASS]


def test_search_mask_requires_capturing_dead_stones():
    # one white stone sits alone inside black's area: black must keep playing
    b = [1] * 81
    for s in ("A9", "J1", "E5"):
        b[pt(s)] = 0
    for s in ("D5", "F5", "E4", "E6"):
        b[pt(s)] = 0
    b[pt("E5")] = -1
    p = Position(board=b, to_play=BLACK)
    assert not p.search_mask()[PASS]


def test_ownership_and_max_moves():
    p = setup(black=["A8", "B9"], white=["J1"])
    own = p.ownership()
    assert own[pt("A9")] == 1 and own[pt("A8")] == 1 and own[pt("J1")] == -1
    assert own[pt("E5")] == 0  # empty region touching both colors is neutral
    q = Position(max_moves=3)
    for _ in range(3):
        assert not q.is_over()
        q = q.play(q.legal_mask().index(True))
    assert q.is_over() and q.max_moves == 3


def test_search_mask_allows_passing_back_when_ahead():
    p = setup(black=["E5"], white=[], to_play=WHITE).play(PASS)  # black to play after white passed
    assert p.passes == 1 and p.area_score() > 0
    assert p.search_mask()[PASS]
    q = setup(black=[], white=["E5"], to_play=WHITE).play(PASS)  # black behind
    assert not q.search_mask()[PASS]
