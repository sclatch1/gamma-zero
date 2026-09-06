"""FastAPI game server for Gardner Minichess: human vs raw (no-MCTS)
network, played from a browser. Owns: HTTP API for game state and move
submission, plus one shared in-memory game (single player, no sessions).
Does not own: move generation, encoding, or network architecture --
delegates entirely to board_encoder.py / move.py / policy.py / network.py,
same as play.py's CLI loop.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.board_encoder import BOARD_SIZE, MAX_PLY, PIECE_TYPES, encode, initial_board
from src.move import apply_move, checkmate, legal_moves, stalemate
from src.network import GammaZeroNet
from src.policy import move_to_index

WEB_DIR = Path(__file__).resolve().parent.parent / 'web'
FILES = 'abcde'

app = FastAPI()

net = GammaZeroNet()
net.eval()


@dataclass
class Game:
    board: np.ndarray = field(default_factory=initial_board)
    turn: str = 'w'
    ply: int = 0


game = Game()


def piece_symbol(code):
    if code == 0:
        return ''
    pt = PIECE_TYPES[abs(code) - 1]
    return pt if code > 0 else pt.lower()


def square_name(sq):
    row, col = sq
    return f'{FILES[col]}{row + 1}'


def move_name(move):
    name = f'{square_name(move.from_sq)}{square_name(move.to_sq)}'
    return f'{name}={move.promo}' if move.promo else name


def move_status(board, color):
    if checkmate(board, color):
        return 'checkmate'
    if stalemate(board, color):
        return 'stalemate'
    return 'ongoing'


def game_status():
    status = move_status(game.board, game.turn)
    if status == 'ongoing' and game.ply >= MAX_PLY:
        return 'draw'
    return status


def state_dict(**extra):
    status = game_status()
    moves = legal_moves(game.board, game.turn) if status == 'ongoing' else []
    return {
        'board': [[piece_symbol(game.board[r, c]) for c in range(BOARD_SIZE)] for r in range(BOARD_SIZE)],
        'turn': game.turn,
        'ply': game.ply,
        'status': status,
        'legal_moves': [
            {'from': list(m.from_sq), 'to': list(m.to_sq), 'promo': m.promo, 'name': move_name(m)}
            for m in moves
        ],
        **extra,
    }


def play_network_reply():
    """If it's now the network's turn and the game isn't over, play its
    move (raw policy argmax over legal moves, no search) and return its
    name -- None if the game ended or it wasn't the network's turn."""
    if game_status() != 'ongoing':
        return None
    moves = legal_moves(game.board, game.turn)
    board_tensor = encode(game.board, turn=game.turn, ply=game.ply).unsqueeze(0)
    with torch.no_grad():
        policy_logits, _ = net(board_tensor)
    reply = max(moves, key=lambda m: policy_logits[0, move_to_index(m)].item())
    game.board = apply_move(game.board, reply)
    game.turn = 'b' if game.turn == 'w' else 'w'
    game.ply += 1
    return move_name(reply)


class MoveRequest(BaseModel):
    from_sq: list[int]
    to_sq: list[int]
    promo: Literal['Q', 'R', 'B', 'N'] | None = None


@app.get('/api/state')
def get_state():
    return state_dict()


@app.post('/api/new_game')
def new_game():
    game.board = initial_board()
    game.turn = 'w'
    game.ply = 0
    return state_dict()


@app.post('/api/move')
def make_move(req: MoveRequest):
    if game_status() != 'ongoing':
        raise HTTPException(400, 'game is over')

    moves = legal_moves(game.board, game.turn)
    match = next(
        (m for m in moves
         if list(m.from_sq) == req.from_sq and list(m.to_sq) == req.to_sq and m.promo == req.promo),
        None,
    )
    if match is None:
        raise HTTPException(400, 'illegal move')

    game.board = apply_move(game.board, match)
    game.turn = 'b' if game.turn == 'w' else 'w'
    game.ply += 1
    human_move = move_name(match)

    network_move = play_network_reply()
    return state_dict(human_move=human_move, network_move=network_move)


app.mount('/', StaticFiles(directory=WEB_DIR, html=True), name='web')
