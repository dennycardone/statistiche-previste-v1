"""Funzioni comuni del test player props (estratte da test_props.py)."""
import numpy as np
from scipy.special import gammaln
STATS = ["sh", "sot", "fc", "yc"]                       # tiri (API: senza i respinti), tiri in porta, falli commessi, cartellini (gialli + rossi)
MARKETS = [("sot", 0.5), ("sot", 1.5), ("sh", 1.5), ("sh", 2.5), ("fc", 0.5), ("fc", 1.5), ("yc", 0.5)]
LAB = {("sot", 0.5): "Tiri in porta Over 0,5", ("sot", 1.5): "Tiri in porta Over 1,5", ("sh", 1.5): "Tiri Over 1,5", ("sh", 2.5): "Tiri Over 2,5",
       ("fc", 0.5): "Falli Over 0,5", ("fc", 1.5): "Falli Over 1,5", ("yc", 0.5): "Ammonito Sì"}
DPS = [0.95, 0.97, 0.99]; KS = [2.0, 5.0, 10.0, 20.0]
def p_over(mu, L, alpha):
    """P(X > L) con X Binomiale Negativa (media mu, varianza mu + alpha·mu²); alpha 0 = Poisson."""
    k = np.arange(int(L) + 1)[None, :]; mu = np.maximum(np.asarray(mu, float), 1e-9)[:, None]
    if alpha <= 1e-6: lp = -mu + k * np.log(mu) - gammaln(k + 1)
    else:
        r = 1 / alpha; q = r / (r + mu); lp = gammaln(k + r) - gammaln(r) - gammaln(k + 1) + r * np.log(q) + k * np.log1p(-q)
    return np.clip(1 - np.exp(lp).sum(1), 1e-6, 1 - 1e-6)
def ll(p, y): return -(y * np.log(p) + (1 - y) * np.log(1 - p))
