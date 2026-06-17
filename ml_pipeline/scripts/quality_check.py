from __future__ import annotations

import argparse
import csv
import hashlib
import statistics
from pathlib import Path
from typing import Dict, List

import numpy as np
import torchaudio

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a", ".ogg"}


def silence_ratio(wav: np.ndarray, sr: int, frame_ms: int = 20, thresh_db: float = -40.0) -> float:
    frame_len = int(sr * frame_ms / 1000)
    if frame_len <= 0:
        return 0.0
    total = (len(wav) // frame_len) * frame_len
    if total == 0:
        return 1.0
    frames = wav[:total].reshape(-1, frame_len)
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    return float(np.mean(db < thresh_db))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    files = [p for p in data_dir.rglob("*") if p.suffix.lower() in AUDIO_EXTS]
    rows: List[Dict] = []
    sample_rates = []
    durations = []
    clip_counts = 0
    dup_hashes = set()
    dup_files = 0

    for path in files:
        wav, sr = torchaudio.load(path)
        wav = wav.mean(dim=0).numpy() if wav.shape[0] > 1 else wav.squeeze(0).numpy()
        duration = len(wav) / sr
        rms = float(np.sqrt(np.mean(wav**2) + 1e-12))
        clipping = float(np.mean(np.abs(wav) >= 0.999))
        silence = silence_ratio(wav, sr)
        sample_rates.append(sr)
        durations.append(duration)
        if clipping > 0.0:
            clip_counts += 1

        file_hash = hashlib.md5(path.read_bytes()).hexdigest()
        if file_hash in dup_hashes:
            dup_files += 1
        else:
            dup_hashes.add(file_hash)

        rows.append(
            {
                "path": str(path),
                "speaker": path.parent.name,
                "sample_rate": sr,
                "duration_sec": round(duration, 3),
                "rms": round(rms, 6),
                "clipping_ratio": round(clipping, 6),
                "silence_ratio": round(silence, 6),
            }
        )

    with report_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Files: {len(files)}")
    print(f"Speakers: {len(set(r['speaker'] for r in rows))}")
    if durations:
        print(
            "Duration (sec) min/median/max: "
            f"{min(durations):.2f} / {statistics.median(durations):.2f} / {max(durations):.2f}"
        )
    if sample_rates:
        print(f"Sample rates: {sorted(set(sample_rates))}")
    print(f"Files with clipping: {clip_counts}")
    print(f"Duplicate files (by hash): {dup_files}")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
