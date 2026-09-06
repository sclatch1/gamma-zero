"""AlphaZero-style policy+value network for Gardner Minichess. Owns: the
model architecture and its forward pass (encoded board -> policy logits +
value). 

Sized down from the original AlphaZero architecture (19-40 residual
blocks, 256 channels) to match a 5x5 board with a much smaller action
space.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


from src.board_encoder import BOARD_SIZE, PIECE_TYPES
from src.policy import N_PLANES

IN_PLANES = len(PIECE_TYPES) * 2 + 2  # matches board_encoder.encode()'s output channel count


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return F.relu(out + x)


class GammaZeroNet(nn.Module):
    def __init__(self, channels=64, n_blocks=4, value_hidden=64):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(IN_PLANES, channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True),
        )
        self.tower = nn.Sequential(*[ResidualBlock(channels) for _ in range(n_blocks)])

        # One raw-logit output channel per move-type plane: flattening this
        # (N_PLANES, 5, 5) tensor gives exactly the index order
        # policy.move_to_index expects (plane-major, then row, then col).
        self.policy_head = nn.Conv2d(channels, N_PLANES, kernel_size=1)

        value_channels = 2
        self.value_conv = nn.Sequential(
            nn.Conv2d(channels, value_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(value_channels),
            nn.ReLU(inplace=True),
        )
        self.value_fc = nn.Sequential(
            nn.Linear(value_channels * BOARD_SIZE * BOARD_SIZE, value_hidden),
            nn.ReLU(inplace=True),
            nn.Linear(value_hidden, 1),
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.tower(x)

        policy_logits = self.policy_head(x).flatten(1)

        value = self.value_conv(x).flatten(1)
        value = torch.tanh(self.value_fc(value)).squeeze(-1)

        return policy_logits, value


if __name__ == '__main__':

    from src.board_encoder import encode, initial_board

    net = GammaZeroNet()
    net.eval()
    board_tensor = encode(initial_board(), turn='w', ply=0).unsqueeze(0)
    with torch.no_grad():
        policy_logits, value = net(board_tensor)

    assert tuple(policy_logits.shape) == (1, N_PLANES * BOARD_SIZE * BOARD_SIZE)
    assert tuple(value.shape) == (1,)
    assert -1.0 <= value.item() <= 1.0
    n_params = sum(p.numel() for p in net.parameters())
    print('policy_logits:', tuple(policy_logits.shape), '-- value:', tuple(value.shape),
          f'-- {n_params:,} params -- OK')
