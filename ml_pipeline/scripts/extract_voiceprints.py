from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from src.audio import chunk_audio, load_audio
from src.dataset import build_index
from src.model import load_checkpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--hop-seconds", type=float, default=None)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _, config = load_checkpoint(args.checkpoint, device)
    model.eval()

    items, _ = build_index(args.data_dir)
    by_speaker = {}
    for item in items:
        by_speaker.setdefault(item.speaker, []).append(item.path)

    segment_samples = int(config["sample_rate"] * config["segment_seconds"])
    hop_samples = None if args.hop_seconds is None else int(config["sample_rate"] * args.hop_seconds)

    voiceprints = {}
    for speaker, paths in tqdm(by_speaker.items(), desc="Extracting"):
        embeddings = []
        for path in paths:
            wav = load_audio(str(path), config["sample_rate"])
            segments = chunk_audio(wav, segment_samples, hop_samples)
            for seg in segments:
                seg = seg.unsqueeze(0).to(device)
                with torch.no_grad():
                    _, emb = model(seg)
                embeddings.append(emb.squeeze(0).cpu().numpy())
        if embeddings:
            voiceprints[speaker] = np.mean(np.stack(embeddings, axis=0), axis=0)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out_path, **voiceprints)
    print(f"Saved voiceprints to {out_path}")


if __name__ == "__main__":
    main()
