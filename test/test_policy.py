"""Correctness tests for policy.py: every legal move must round-trip
through move_to_index/index_to_move, and no two legal moves in the same
position may collide on the same index (a collision would silently
corrupt policy training targets)."""

import numpy as np

from src.board_encoder import initial_board, piece_code
from src.move import apply_move, legal_moves
from src.policy import (ACTION_SPACE_SIZE, N_PLANES, describe_index, index_to_move,
                         legal_move_mask, move_to_index, plane_name)


def _check_position(board, color):
    moves = legal_moves(board, color)
    indices = [move_to_index(m) for m in moves]

    assert len(set(indices)) == len(moves), 'index collision among legal moves'
    assert all(0 <= i < ACTION_SPACE_SIZE for i in indices)
    for move, index in zip(moves, indices):
        assert index_to_move(index, board) == move

    mask = legal_move_mask(moves)
    assert mask.shape == (ACTION_SPACE_SIZE,)
    assert mask.sum() == len(moves)


def test_round_trip_initial_position_both_colors():
    board = initial_board()
    _check_position(board, 'w')
    _check_position(board, 'b')


def test_round_trip_several_plies_deep():
    # walks a short forced line so sliding/knight/capture moves all get
    # exercised, not just the opening's pawn pushes.
    board = initial_board()
    color = 'w'
    for i in range(6):
        moves = legal_moves(board, color)
        _check_position(board, color)
        board = apply_move(board, moves[i % len(moves)])
        color = 'b' if color == 'w' else 'w'


def test_round_trip_white_promotion():
    board = np.zeros((5, 5), dtype=np.int8)
    board[3, 2] = piece_code('P', 'w')
    board[0, 0] = piece_code('K', 'w')
    board[4, 0] = piece_code('K', 'b')
    _check_position(board, 'w')


def test_round_trip_black_promotion():
    board = np.zeros((5, 5), dtype=np.int8)
    board[1, 2] = piece_code('P', 'b')
    board[4, 0] = piece_code('K', 'b')
    board[0, 0] = piece_code('K', 'w')
    _check_position(board, 'b')


def test_plane_name_is_unique_and_total():
    # every plane gets its own label -- a collision here would mean two
    # geometrically different move-types are indistinguishable in the
    # debug output (though not in the actual index, which stays correct
    # regardless: this only guards the human-readable labels).
    names = [plane_name(p) for p in range(N_PLANES)]
    assert len(set(names)) == N_PLANES


def test_describe_index_matches_move_to_index():
    move = list(legal_moves(initial_board(), 'w'))[0]
    index = move_to_index(move)
    description = describe_index(index)
    assert description.startswith(f'index {index}:')
    assert str(move.from_sq).replace(' ', '') in description.replace(' ', '')
