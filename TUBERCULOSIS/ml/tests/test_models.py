import numpy as np
import pytest
import torch

from tbml.explain import attention_rollout, gradcam
from tbml.models import MODEL_NAMES, get_model


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_forward_shape_and_explanation(name):
    m = get_model(name, img_size=64).eval()
    x = torch.randn(2, 1, 64, 64)
    assert m(x).shape == (2,)
    heat = attention_rollout(m, x[:1]) if name == "vit" else gradcam(m, x[:1])
    assert heat.shape == (64, 64) and 0 <= heat.min() and heat.max() <= 1 and np.isfinite(heat).all()
