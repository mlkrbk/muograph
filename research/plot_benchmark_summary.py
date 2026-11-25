"""Plot verified Geant4 benchmark summary statistics."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

thresholds = ["≥5 points", "≥10 points"]

poca_mean = np.array([0.5313, 0.5908])
poca_std = np.array([0.0677, 0.0792])

bca_mean = np.array([0.4526, 0.5280])
bca_std = np.array([0.0909, 0.1033])

x = np.arange(len(thresholds))
width = 0.33

fig, ax = plt.subplots(figsize=(8, 5))

ax.bar(
    x - width / 2,
    poca_mean,
    width,
    yerr=poca_std,
    capsize=5,
    label="PoCA mean θ²",
    color="#3274A1",
)

ax.bar(
    x + width / 2,
    bca_mean,
    width,
    yerr=bca_std,
    capsize=5,
    label="Native BCA",
    color="#E1812C",
)

ax.set_xticks(x)
ax.set_xticklabels(thresholds)
ax.set_ylabel("Spearman correlation with iron volume fraction")
ax.set_xlabel("Minimum PoCA points per voxel")
ax.set_ylim(0, 0.8)
ax.set_title("Geant4 muon-scattering reconstruction benchmark")
ax.legend()
ax.grid(axis="y", alpha=0.2)
ax.set_axisbelow(True)

fig.text(
    0.5,
    0.01,
    "30 detector-noise seeds; error bars = standard deviation across seeds",
    ha="center",
    fontsize=9,
)

fig.tight_layout(rect=[0, 0.06, 1, 1])

output = Path("research/figures/benchmark_correlations.png")
fig.savefig(output, dpi=200, bbox_inches="tight")
plt.close(fig)

print("Created:", output)
