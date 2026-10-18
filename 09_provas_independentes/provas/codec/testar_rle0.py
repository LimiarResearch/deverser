"""testar_rle0.py: a corrida de zeros vetorizada (codec.py) dá os mesmos bytes que a de laço (codec_v2_laco.py) e volta exata."""
import numpy as np, codec as N, codec_v2_laco as V
rng = np.random.default_rng(0); falhas = 0
for k in range(3000):
    n = int(rng.integers(0, 3000)); p0 = rng.random()
    u = np.where(rng.random(n) < p0, 0, rng.integers(0, 6, n)).astype(np.uint64)
    a, b = N._rle0(u), V._rle0(u)
    if not np.array_equal(a, b) or not np.array_equal(N._desrle0(a, n), u): falhas += 1
print("3000 casos sorteados: falhas", falhas)
