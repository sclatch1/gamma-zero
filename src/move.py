"""Legal move generation for Gardner Minichess. Owns: pseudo-legal move
generation per piece type, check detection, legality filtering. 

No castling, no en passant, Gardner rules: pawns only ever move one
square, so en passant can't arise; castling is conventionally excluded.
"""

from collections import namedtuple

from src.board_encoder import BOARD_SIZE, PIECE_TYPES, piece_code

Move = namedtuple('Move', ['from_sq', 'to_sq', 'promo'])
Move.__new__.__defaults__ = (None,)  # promo defaults to None

PROMOTION_PIECES = ['Q', 'R', 'B', 'N']  # no K

KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
KING_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
ROOK_DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_DIRECTIONS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
QUEEN_DIRS = ROOK_DIRECTIONS + BISHOP_DIRECTIONS


def on_board(row, col):
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def pseudo_legal_moves(board, color):
    """All moves for `color`, ignoring whether the mover's own king ends
    up in check."""
    moves = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            piece = board[row, col]
            if piece == 0 or (piece > 0) != (color == 'w'):
                continue
            pt = PIECE_TYPES[abs(piece) - 1]
            if pt == 'P':
                moves += _pawn_moves(board, row, col, color)
            elif pt == 'N':
                moves += _leaper_moves(board, row, col, color, KNIGHT_OFFSETS)
            elif pt == 'K':
                moves += _leaper_moves(board, row, col, color, KING_OFFSETS)
            elif pt == 'R':
                moves += _sliding_moves(board, row, col, color, ROOK_DIRECTIONS)
            elif pt == 'B':
                moves += _sliding_moves(board, row, col, color, BISHOP_DIRECTIONS)
            elif pt == 'Q':
                moves += _sliding_moves(board, row, col, color, QUEEN_DIRS)
    return moves


def legal_moves(board, color):
    """pseudo_legal_moves(board, color) filtered to moves that don't leave
    `color`'s own king in check."""
    return [move for move in pseudo_legal_moves(board, color)
            if not is_in_check(apply_move(board, move), color)]


def checkmate(board, color):
    return is_in_check(board, color) and not legal_moves(board, color)


def stalemate(board, color):
    return not is_in_check(board, color) and not legal_moves(board, color)


def _pawn_moves(board, row, col, color):
    # forward step (no double-step), diagonal captures, promotion on
    # reaching the far rank -- one Move per PROMOTION_PIECES choice.
    moves = []
    direction = 1 if color == 'w' else -1
    promotion_rank = BOARD_SIZE - 1 if color == 'w' else 0
    r = row + direction
    if not on_board(r, col):
        return moves

    def add(to_sq):
        if r == promotion_rank:
            moves.extend(Move((row, col), to_sq, promo) for promo in PROMOTION_PIECES)
        else:
            moves.append(Move((row, col), to_sq))

    if board[r, col] == 0:
        add((r, col))

    for dc in (-1, 1):
        c = col + dc
        if not on_board(r, c):
            continue
        target = board[r, c]
        if target != 0 and (target > 0) != (color == 'w'):
            add((r, c))

    return moves


def _leaper_moves(board, row, col, color, offsets):
    # shared by knight and king: fixed offsets, no ray-walking.
    moves = []
    for dr, dc in offsets:
        r, c = row + dr, col + dc
        if not on_board(r, c):
            continue
        target = board[r, c]
        if target == 0 or (target > 0) != (color == 'w'): # you captured an enemy piece
            moves.append(Move((row, col), (r, c)))
    return moves


def _sliding_moves(board, row, col, color, directions):
    # shared by rook/bishop/queen: walk each direction until blocked.
    moves = []
    for dr, dc in directions:
        r, c = row + dr, col + dc
        while on_board(r, c):
            target = board[r, c]
            if target == 0:
                moves.append(Move((row, col), (r, c)))
            else:
                if (target > 0) != (color == 'w'): # you captured an enemy piece
                    moves.append(Move((row, col), (r, c)))
                break
            r += dr
            c += dc
    return moves


def is_square_attacked(board, row, col, by_color):
    """True if any `by_color` piece pseudo-legally attacks (row, col)."""
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            piece = board[r, c]
            if piece == 0 or (piece > 0) != (by_color == 'w'):
                continue
            pt = PIECE_TYPES[abs(piece) - 1]
            if pt == 'P':
                direction = 1 if by_color == 'w' else -1
                if (row, col) in {(r + direction, c - 1), (r + direction, c + 1)}:
                    return True
            elif pt == 'N':
                if (row, col) in {(r + dr, c + dc) for dr, dc in KNIGHT_OFFSETS}:
                    return True
            elif pt == 'K':
                if (row, col) in {(r + dr, c + dc) for dr, dc in KING_OFFSETS}:
                    return True
            else:
                directions = {'R': ROOK_DIRECTIONS, 'B': BISHOP_DIRECTIONS, 'Q': QUEEN_DIRS}[pt]
                for dr, dc in directions:
                    rr, cc = r + dr, c + dc
                    while on_board(rr, cc):
                        if (rr, cc) == (row, col):
                            return True
                        if board[rr, cc] != 0:
                            break
                        rr += dr
                        cc += dc
    return False


def is_in_check(board, color):
    king_code = piece_code('K', color)
    enemy = 'b' if color == 'w' else 'w'
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r, c] == king_code:
                return is_square_attacked(board, r, c, enemy)
    raise ValueError(f'no {color} king on board')


def apply_move(board, move):
    """Returns a new board with `move` applied. Does not mutate `board`."""
    new_board = board.copy()
    piece = board[move.from_sq]
    if move.promo is not None:
        color = 'w' if piece > 0 else 'b'
        piece = piece_code(move.promo, color)
    new_board[move.from_sq] = 0
    new_board[move.to_sq] = piece
    return new_board
