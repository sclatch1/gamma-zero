"""Correctness tests for network.py: output shapes, trainability
(gradients actually flow), and that raw policy logits compose correctly
with policy.legal_move_mask."""

import torch
import torch.nn.functional as F

from src.board_encoder import encode, initial_board
from src.move import legal_moves
from src.network import GammaZeroNet
from src.policy import ACTION_SPACE_SIZE, legal_move_mask


def _board_tensor(batch_size=1):
    board = initial_board()
    return encode(board, turn='w', ply=0).unsqueeze(0).repeat(batch_size, 1, 1, 1)


def test_output_shapes():
    net = GammaZeroNet()
    net.eval()
    with torch.no_grad():
        policy_logits, value = net(_board_tensor(batch_size=3))
    assert tuple(policy_logits.shape) == (3, ACTION_SPACE_SIZE)
    assert tuple(value.shape) == (3,)


def test_value_in_tanh_range():
    net = GammaZeroNet()
    net.eval()
    with torch.no_grad():
        _, value = net(_board_tensor())
    assert (-1.0 <= value).all() and (value <= 1.0).all()


def test_gradients_flow():
    net = GammaZeroNet()
    policy_logits, value = net(_board_tensor(batch_size=2))
    target_policy = torch.zeros_like(policy_logits)
    target_policy[:, 0] = 1.0
    loss = F.cross_entropy(policy_logits, target_policy) + F.mse_loss(value, torch.tensor([1.0, -1.0]))
    loss.backward()

    grads = [p.grad for p in net.parameters()]
    assert all(g is not None for g in grads)
    assert all(torch.isfinite(g).all() for g in grads)


def test_masked_policy_is_a_valid_distribution_over_legal_moves():
    board = initial_board()
    moves = legal_moves(board, 'w')
    mask = torch.from_numpy(legal_move_mask(moves))

    net = GammaZeroNet()
    net.eval()
    with torch.no_grad():
        policy_logits, _ = net(_board_tensor())

    masked_logits = policy_logits[0].masked_fill(~mask, float('-inf'))
    probs = F.softmax(masked_logits, dim=0)

    assert torch.isclose(probs.sum(), torch.tensor(1.0), atol=1e-5)
    assert (probs > 0).sum().item() == len(moves)
