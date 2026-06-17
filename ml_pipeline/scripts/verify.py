from __future__ import annotations

import argparse

import numpy as np
import torch

from src.audio import chunk_audio, load_audio
from src.model import load_checkpoint


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-10
    return float(np.dot(a, b) / denom)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--voiceprints", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--threshold", type=float, default=0.60)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _, config = load_checkpoint(args.checkpoint, device)
    model.eval()

    vp = np.load(args.voiceprints)
    voiceprints = {k: vp[k] for k in vp.files}

    wav = load_audio(args.audio, config["sample_rate"])
    segment_samples = int(config["sample_rate"] * config["segment_seconds"])
    segments = chunk_audio(wav, segment_samples, None)

    embeddings = []
    with torch.no_grad():
        for seg in segments:
            seg = seg.unsqueeze(0).to(device)
            _, emb = model(seg)
            embeddings.append(emb.squeeze(0).cpu().numpy())
    query = np.mean(np.stack(embeddings, axis=0), axis=0)

    scores = {spk: cosine(query, emb) for spk, emb in voiceprints.items()}
    best_speaker, best_score = max(scores.items(), key=lambda x: x[1])

    print(f"Best match: {best_speaker} | score={best_score:.4f}")
    print("Match" if best_score >= args.threshold else "No match")


if __name__ == "__main__":
    main()
