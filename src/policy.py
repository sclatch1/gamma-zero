"""Move <-> policy-index mapping for the neural net's policy head. Owns:
encoding a Move as a flat index into a fixed (58, 5, 5) action space
(AlphaZero-style plane encoding, sized for the 5x5 board).
indices/moves produced here aren't filtered against
legal_moves, callers mask with that themselves.

"""

import numpy as np

from src.board_encoder import BOARD_SIZE, PIECE_TYPES
from src.move import KNIGHT_OFFSETS, QUEEN_DIRS, Move, on_board

MAX_DISTANCE = BOARD_SIZE - 1  # 4: longest possible slide on a 5x5 board
UNDERPROMOTION_PIECES = ['N', 'B', 'R']  # queen promotion is implicit in the queen-direction planes
UNDERPROMOTION_DIRS = [(1, 0), (1, -1), (1, 1), (-1, 0), (-1, -1), (-1, 1)]  # white push/cap-left/cap-right, then black

N_SLIDE_PLANES = len(QUEEN_DIRS) * MAX_DISTANCE                        # 32
N_KNIGHT_PLANES = len(KNIGHT_OFFSETS)                                  # 8
N_UNDERPROMO_PLANES = len(UNDERPROMOTION_DIRS) * len(UNDERPROMOTION_PIECES)  # 18
N_PLANES = N_SLIDE_PLANES + N_KNIGHT_PLANES + N_UNDERPROMO_PLANES      # 58
ACTION_SPACE_SIZE = N_PLANES * BOARD_SIZE * BOARD_SIZE                 # 1450


def _build_slide_tables():
    """Builds the sliding-move plane tables: one plane per
    (direction, distance) pair, indexed as
    `direction_index * MAX_DISTANCE + (distance - 1)`.

    "Sliding move" covers any piece walking a straight or diagonal line
    from QUEEN_DIRS's 8 directions -- rook and bishop moves are just the
    4-direction subsets of this same table, queen moves use all 8, a
    king step or non-promoting pawn push is the distance-1 case. The
    plane only encodes direction + distance, never which piece moved --
    the board state tells the network that, not the action index. That's
    why there's one table here instead of one per piece.

    Returns:
        (step_to_plane, plane_to_step): dict[(dr, dc), int] and its
        inverse dict[int, (dr, dc)], covering all N_SLIDE_PLANES planes.
    """
    step_to_plane = {}
    plane_to_step = {}
    for direction_index, (dr, dc) in enumerate(QUEEN_DIRS):
        for distance in range(1, MAX_DISTANCE + 1):
            plane = direction_index * MAX_DISTANCE + (distance - 1)
            step = (dr * distance, dc * distance)
            step_to_plane[step] = plane
            plane_to_step[plane] = step
    return step_to_plane, plane_to_step


def _build_knight_tables():
    """Builds the knight-jump plane tables: one plane per knight offset,
    in KNIGHT_OFFSETS order.

    Returns:
        (step_to_plane, plane_to_step): dict[(dr, dc), int] and its
        inverse dict[int, (dr, dc)], covering all N_KNIGHT_PLANES planes.
        These plane indices are local to the knight block -- callers
        offset by N_SLIDE_PLANES to place them in the full plane space.
    """
    step_to_plane = {step: i for i, step in enumerate(KNIGHT_OFFSETS)}
    plane_to_step = {i: step for i, step in enumerate(KNIGHT_OFFSETS)}
    return step_to_plane, plane_to_step


def _build_underpromo_tables():
    """Builds the underpromotion plane tables: one plane per
    (direction, promo piece) pair.

    Returns:
        (step_promo_to_plane, plane_to_step_promo): dict[((dr, dc),
        promo), int] and its inverse dict[int, (dr, dc, promo)],
        covering all N_UNDERPROMO_PLANES planes. Plane indices already
        include the N_SLIDE_PLANES + N_KNIGHT_PLANES offset, matching
        their place in the full plane space.
    """
    step_promo_to_plane = {}
    plane_to_step_promo = {}
    for direction_index, step in enumerate(UNDERPROMOTION_DIRS):
        for piece_index, promo in enumerate(UNDERPROMOTION_PIECES):
            plane = N_SLIDE_PLANES + N_KNIGHT_PLANES + direction_index * len(UNDERPROMOTION_PIECES) + piece_index
            step_promo_to_plane[(step, promo)] = plane
            plane_to_step_promo[plane] = (step[0], step[1], promo)
    return step_promo_to_plane, plane_to_step_promo


_SLIDE_STEP_TO_PLANE, _SLIDE_PLANE_TO_STEP = _build_slide_tables()
_KNIGHT_STEP_TO_PLANE, _KNIGHT_PLANE_TO_STEP = _build_knight_tables()
_UNDERPROMO_STEP_PROMO_TO_PLANE, _UNDERPROMO_PLANE_TO_STEP_PROMO = _build_underpromo_tables()



def _plane_step(plane):
    """(dr, dc, promo) for a plane index -- promo is None unless it's an
    underpromotion plane. Shared by index_to_move and the debug helpers
    below so the plane layout is only decoded in one place.

    Args:
        plane: int in range(N_PLANES).

    Returns:
        (dr, dc, promo) tuple. dr, dc are the row/col step for that plane
        (already scaled by distance for slide planes). promo is the
        underpromotion piece letter ('N', 'B', or 'R') for underpromotion
        planes, else None.
    """
    if plane < N_SLIDE_PLANES:
        dr, dc = _SLIDE_PLANE_TO_STEP[plane]
        return dr, dc, None
    elif plane < N_SLIDE_PLANES + N_KNIGHT_PLANES:
        dr, dc = _KNIGHT_PLANE_TO_STEP[plane - N_SLIDE_PLANES]
        return dr, dc, None
    else:
        return _UNDERPROMO_PLANE_TO_STEP_PROMO[plane]



def _implicit_promo(board, from_sq, to_sq):
    """Infers queen promotion for a slide-direction plane, since those
    planes never store a promo piece explicitly -- it's inferred from
    board context at decode time instead.

    Args:
        board: (BOARD_SIZE, BOARD_SIZE) array in board_encoder's piece-code
            layout.
        from_sq: (row, col) tuple the move starts from.
        to_sq: (row, col) tuple the move ends on.

    Returns:
        'Q' if `from_sq` holds a pawn and `to_sq` is on the far rank for
        that pawn's color, else None.
    """
    piece = board[from_sq]
    if piece == 0 or PIECE_TYPES[abs(piece) - 1] != 'P':
        return None
    color = 'w' if piece > 0 else 'b'
    promotion_rank = BOARD_SIZE - 1 if color == 'w' else 0
    return 'Q' if to_sq[0] == promotion_rank else None


def move_to_index(move):
    """Encodes `move` as a flat index into the fixed action space.

    Args:
        move: a move.Move. Must be one of the three encodable shapes
            (sliding move, knight jump, or a non-queen promotion) --
            callers pass moves from move.legal_moves, which only ever
            produces those shapes.

    Returns:
        int: a value in range(ACTION_SPACE_SIZE) identifying `move`'s
        (from-square, direction/distance-or-jump, promotion) combination.
    """
    from_row, from_col = move.from_sq
    to_row, to_col = move.to_sq
    step = (to_row - from_row, to_col - from_col)

    if move.promo is not None and move.promo != 'Q':
        plane = _UNDERPROMO_STEP_PROMO_TO_PLANE[(step, move.promo)]
    elif step in _KNIGHT_STEP_TO_PLANE:
        plane = N_SLIDE_PLANES + _KNIGHT_STEP_TO_PLANE[step]
    else:
        plane = _SLIDE_STEP_TO_PLANE[step]

    return (plane * BOARD_SIZE + from_row) * BOARD_SIZE + from_col


def index_to_move(index, board):
    """Decodes a flat policy index back into a Move.

    Args:
        index: int in range(ACTION_SPACE_SIZE).
        board: (BOARD_SIZE, BOARD_SIZE) array in board_encoder's piece-code
            layout -- needed to tell whether a slide-direction move onto
            the far rank is a pawn promoting to queen.

    Returns:
        Move, or None if the index decodes to an off-board square --
        callers intersect with legal_moves anyway, so an invalid index
        just never matches a legal move.
    """
    plane, rem = divmod(index, BOARD_SIZE * BOARD_SIZE)
    from_row, from_col = divmod(rem, BOARD_SIZE)
    from_sq = (from_row, from_col)

    dr, dc, promo = _plane_step(plane)
    to_row, to_col = from_row + dr, from_col + dc
    if not on_board(to_row, to_col):
        return None
    to_sq = (to_row, to_col)

    if promo is None:
        promo = _implicit_promo(board, from_sq, to_sq)
    return Move(from_sq, to_sq, promo)


def legal_move_mask(legal):
    """Boolean mask over the action space for a list of legal moves.

    Args:
        legal: list[Move], typically move.legal_moves(board, color).

    Returns:
        np.ndarray: bool array of shape (ACTION_SPACE_SIZE,), True at the
        index of each move in `legal`.
    """
    mask = np.zeros(ACTION_SPACE_SIZE, dtype=bool)
    for move in legal:
        mask[move_to_index(move)] = True
    return mask


if __name__ == "__main__":
    from src.board_encoder import initial_board, get_piece_code, idx_to_piec_code

    first_square_to_second_square = Move((0,0),(0,1))
    board = initial_board()



    a = move_to_index(first_square_to_second_square)

    mov = index_to_move(a,board=board)

    piece = idx_to_piec_code(get_piece_code(0,0, board))

    print(a, mov, piece)