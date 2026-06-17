from __future__ import annotations

import argparse
import itertools

import numpy as np
import torch
from tqdm import tqdm

from src.audio import chunk_audio, load_audio
from src.dataset import build_index, split_by_speaker
from src.model import load_checkpoint


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-10
    return float(np.dot(a, b) / denom)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _, config = load_checkpoint(args.checkpoint, device)
    model.eval()

    items, _ = build_index(args.data_dir)
    _, val_items = split_by_speaker(items, val_per_speaker=1, seed=1337)

    embeddings = []
    labels = []

    segment_samples = int(config["sample_rate"] * config["segment_seconds"])

    for item in tqdm(val_items, desc="Embedding"):
        wav = load_audio(str(item.path), config["sample_rate"])
        segments = chunk_audio(wav, segment_samples, None)
        seg_embs = []
        with torch.no_grad():
            for seg in segments:
                seg = seg.unsqueeze(0).to(device)
                _, emb = model(seg)
                seg_embs.append(emb.squeeze(0).cpu().numpy())
        embeddings.append(np.mean(np.stack(seg_embs, axis=0), axis=0))
        labels.append(item.speaker)

    scores = []
    labels_pair = []

    for i, j in itertools.combinations(range(len(embeddings)), 2):
        score = cosine(embeddings[i], embeddings[j])
        same = labels[i] == labels[j]
        scores.append(score)
        labels_pair.append(same)

    scores = np.array(scores)
    labels_pair = np.array(labels_pair)

    thresholds = np.unique(scores)
    best_thr = 0.0
    best_diff = 1.0
    best_eer = 1.0

    for thr in thresholds:
        false_accept = np.sum((scores >= thr) & (~labels_pair))
        false_reject = np.sum((scores < thr) & (labels_pair))
        far = false_accept / max(1, np.sum(~labels_pair))
        frr = false_reject / max(1, np.sum(labels_pair))
        diff = abs(far - frr)
        if diff < best_diff:
            best_diff = diff
            best_thr = thr
            best_eer = (far + frr) / 2

    print(f"Suggested threshold: {best_thr:.4f}")
    print(f"EER estimate: {best_eer:.4f}")


if __name__ == "__main__":
    main()
