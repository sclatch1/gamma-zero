"""Minimal Gardner Minichess board + encoder."""

import numpy as np
import torch
import matplotlib.pyplot as plt
import math
from pathlib import Path

BOARD_SIZE = 5
MAX_PLY = 120
PIECE_TYPES = ['K', 'Q', 'R', 'B', 'N', 'P']  # fixed order -> also determines piece codes
BACK_RANK = ['R', 'N', 'B', 'Q', 'K']


def piece_code(piece_type, color):
    idx = PIECE_TYPES.index(piece_type) + 1
    return idx if color == 'w' else -idx


def initial_board():
    board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
    for file, pt in enumerate(BACK_RANK):
        board[0, file] = piece_code(pt, 'w')
        board[4, file] = piece_code(pt, 'b')
    board[1, :] = piece_code('P', 'w')
    board[3, :] = piece_code('P', 'b')
    return board


def get_piece_code(r,w, board):
    return board[r,w]

def idx_to_piec_code(idx):
    return PIECE_TYPES[idx-1]



def encode(board, turn, ply):
    n = len(PIECE_TYPES)
    planes = np.zeros((n * 2 + 2, BOARD_SIZE, BOARD_SIZE), dtype=np.float32)
    for i in range(n):
        planes[i] = (board == i + 1)
        planes[n + i] = (board == -(i + 1))
    if turn == 'w':
        planes[n * 2] = 1.0
    planes[n * 2 + 1] = min(ply, MAX_PLY) / MAX_PLY
    return torch.from_numpy(planes)


if __name__ == '__main__':
    board = initial_board()
    t = encode(board, turn='w', ply=0)
    assert tuple(t.shape) == (14, 5, 5)
    assert (board != 0).sum() == 20
    assert board[0, 4] == piece_code('K', 'w')  # White king on e1
    assert board[4, 4] == piece_code('K', 'b')  # Black king on e5
    print('Shape:', tuple(t.shape), '-- OK')

    matrices = [t[i, :, :].numpy() for i in range(t.shape[0])]

    n_types = len(PIECE_TYPES)
    titles = (
        [f"{pt} white" for pt in PIECE_TYPES]
        + [f"{pt} black" for pt in PIECE_TYPES]
        + ["turn (1=white)", "ply / MAX_PLY"]
    )

    n_planes = t.shape[0]
    n_cols = n_types
    n_rows = math.ceil(n_planes / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 3 * n_rows))
    axes = axes.flatten()

    for i, ax in enumerate(axes):
        if i < n_planes:
            ax.imshow(matrices[i], cmap="Greys", interpolation="nearest", vmin=0, vmax=1)
            ax.set_title(titles[i], fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            ax.axis("off")

    plt.tight_layout()
    plots_dir = Path(__file__).resolve().parent.parent / "plots"
    plots_dir.mkdir(exist_ok=True)
    plt.savefig(plots_dir / "encoded_board.png")
