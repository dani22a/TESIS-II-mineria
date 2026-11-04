"""Five binary TB-screening classifiers (single logit output, 1-channel input in [-1, 1]).

densenet121, efficientnet_b3 : torchvision backbones (weights=None unless pretrained=True).
vit                          : compact ViT written here (exposes attention for rollout).
cnn_transformer              : conv stem + transformer encoder (hybrid).
effnet_bilstm_attn           : EfficientNet-B3 features -> BiLSTM -> additive attention.
"""
from __future__ import annotations

import torch
from torch import nn
from torchvision import models as tv

MODEL_NAMES = ("densenet121", "efficientnet_b3", "vit", "cnn_transformer", "effnet_bilstm_attn")


def _rgb(x: torch.Tensor) -> torch.Tensor:
    return x.repeat(1, 3, 1, 1) if x.shape[1] == 1 else x


class DenseNet121(nn.Module):
    def __init__(self, pretrained=False, dropout=0.0, **_):
        super().__init__()
        self.net = tv.densenet121(weights="DEFAULT" if pretrained else None, drop_rate=dropout)
        self.net.classifier = nn.Linear(self.net.classifier.in_features, 1)
        self.cam_layer = self.net.features.denseblock4

    def forward(self, x):
        return self.net(_rgb(x)).squeeze(1)


class EfficientNetB3(nn.Module):
    def __init__(self, pretrained=False, dropout=0.3, **_):
        super().__init__()
        self.net = tv.efficientnet_b3(weights="DEFAULT" if pretrained else None, dropout=dropout)
        self.net.classifier[1] = nn.Linear(self.net.classifier[1].in_features, 1)
        self.cam_layer = self.net.features[-1]

    def forward(self, x):
        return self.net(_rgb(x)).squeeze(1)


class Attention(nn.Module):
    def __init__(self, dim, heads):
        super().__init__()
        self.h, self.qkv, self.proj = heads, nn.Linear(dim, dim * 3), nn.Linear(dim, dim)
        self.last_attn = None

    def forward(self, x):
        b, t, d = x.shape
        q, k, v = self.qkv(x).reshape(b, t, 3, self.h, d // self.h).permute(2, 0, 3, 1, 4)
        a = (q @ k.transpose(-2, -1) * (d // self.h) ** -0.5).softmax(-1)
        self.last_attn = a.detach()
        return self.proj((a @ v).transpose(1, 2).reshape(b, t, d))


class Block(nn.Module):
    def __init__(self, dim, heads, dropout):
        super().__init__()
        self.n1, self.attn, self.n2 = nn.LayerNorm(dim), Attention(dim, heads), nn.LayerNorm(dim)
        self.mlp = nn.Sequential(nn.Linear(dim, dim * 4), nn.GELU(), nn.Dropout(dropout), nn.Linear(dim * 4, dim))

    def forward(self, x):
        x = x + self.attn(self.n1(x))
        return x + self.mlp(self.n2(x))


class ViT(nn.Module):
    def __init__(self, img_size=224, patch=16, dim=192, depth=6, heads=3, dropout=0.1, **_):
        super().__init__()
        assert img_size % patch == 0, "img_size must be divisible by patch"
        self.grid = img_size // patch
        self.embed = nn.Conv2d(1, dim, patch, patch)
        self.cls = nn.Parameter(torch.zeros(1, 1, dim))
        self.pos = nn.Parameter(torch.randn(1, self.grid ** 2 + 1, dim) * 0.02)
        self.blocks = nn.ModuleList(Block(dim, heads, dropout) for _ in range(depth))
        self.norm, self.head = nn.LayerNorm(dim), nn.Linear(dim, 1)

    def forward(self, x):
        t = self.embed(x).flatten(2).transpose(1, 2)
        t = torch.cat([self.cls.expand(len(t), -1, -1), t], 1) + self.pos
        for blk in self.blocks:
            t = blk(t)
        return self.head(self.norm(t)[:, 0]).squeeze(1)


class CNNTransformer(nn.Module):
    def __init__(self, img_size=224, dim=128, depth=2, heads=4, dropout=0.1, **_):
        super().__init__()

        def cb(i, o):
            return nn.Sequential(nn.Conv2d(i, o, 3, 2, 1), nn.BatchNorm2d(o), nn.ReLU())

        self.stem = nn.Sequential(cb(1, 32), cb(32, 64), cb(64, dim))
        self.cam_layer = self.stem[-1]
        n = (img_size // 8) ** 2
        self.pos = nn.Parameter(torch.randn(1, n, dim) * 0.02)
        layer = nn.TransformerEncoderLayer(dim, heads, dim * 4, dropout, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, depth, enable_nested_tensor=False)
        self.head = nn.Linear(dim, 1)

    def forward(self, x):
        t = self.stem(x).flatten(2).transpose(1, 2) + self.pos
        return self.head(self.enc(t).mean(1)).squeeze(1)


class EffNetBiLSTMAttn(nn.Module):
    def __init__(self, pretrained=False, dropout=0.3, hidden=64, **_):
        super().__init__()
        eff = tv.efficientnet_b3(weights="DEFAULT" if pretrained else None)
        self.features = eff.features
        self.cam_layer = self.features[-1]
        self.proj = nn.Linear(1536, 2 * hidden)
        self.lstm = nn.LSTM(2 * hidden, hidden, batch_first=True, bidirectional=True)
        self.att = nn.Linear(2 * hidden, 1)
        self.drop, self.head = nn.Dropout(dropout), nn.Linear(2 * hidden, 1)

    def forward(self, x):
        f = self.features(_rgb(x)).flatten(2).transpose(1, 2)  # (B, h*w, C): spatial positions as a sequence
        h, _ = self.lstm(self.proj(f))
        w = self.att(h).softmax(1)
        return self.head(self.drop((w * h).sum(1))).squeeze(1)


def get_model(name: str, img_size: int = 224, **kw) -> nn.Module:
    if name == "densenet121":
        return DenseNet121(**kw)
    if name == "efficientnet_b3":
        return EfficientNetB3(**kw)
    if name == "vit":
        patch = kw.pop("patch", 16 if img_size >= 224 else 8)
        return ViT(img_size=img_size, patch=patch, **kw)
    if name == "cnn_transformer":
        return CNNTransformer(img_size=img_size, **kw)
    if name == "effnet_bilstm_attn":
        return EffNetBiLSTMAttn(**kw)
    raise ValueError(f"unknown model {name}; choose from {MODEL_NAMES}")
