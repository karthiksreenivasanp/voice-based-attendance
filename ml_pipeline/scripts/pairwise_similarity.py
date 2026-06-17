from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def cosine_matrix(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-12
    normalized = embeddings / norms
    return normalized @ normalized.T


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voiceprints", required=True)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--prefix", default="pairwise_similarity")
    args = parser.parse_args()

    vp = np.load(args.voiceprints)
    speakers = sorted(vp.files)
    if not speakers:
        raise ValueError("No voiceprints found in the provided file.")

    embeddings = np.stack([vp[s] for s in speakers], axis=0)
    sim = cosine_matrix(embeddings)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{args.prefix}.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["speaker"] + speakers)
        for i, spk in enumerate(speakers):
            writer.writerow([spk] + [f"{v:.6f}" for v in sim[i].tolist()])

    plot_path = out_dir / f"{args.prefix}.png"
    plt.figure(figsize=(8, 7))
    im = plt.imshow(sim, vmin=-1, vmax=1, cmap="coolwarm")
    plt.colorbar(im, fraction=0.046, pad=0.04, label="Cosine similarity")
    plt.xticks(range(len(speakers)), speakers, rotation=90, fontsize=7)
    plt.yticks(range(len(speakers)), speakers, fontsize=7)
    plt.title("All-vs-all speaker similarity")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=160)
    plt.close()

    print(f"Saved pairwise similarity CSV to: {csv_path}")
    print(f"Saved pairwise similarity plot to: {plot_path}")


if __name__ == "__main__":
    main()
