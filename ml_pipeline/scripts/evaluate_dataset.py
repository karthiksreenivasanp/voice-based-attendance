from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from tqdm import tqdm

from src.audio import chunk_audio, load_audio
from src.dataset import build_index
from src.model import load_checkpoint


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-10
    return float(np.dot(a, b) / denom)


def embed_audio(path: str, model: torch.nn.Module, config: dict, device: torch.device) -> np.ndarray:
    wav = load_audio(path, config["sample_rate"])
    segment_samples = int(config["sample_rate"] * config["segment_seconds"])
    segments = chunk_audio(wav, segment_samples, None)
    embeddings = []
    with torch.no_grad():
        for seg in segments:
            seg = seg.unsqueeze(0).to(device)
            _, emb = model(seg)
            embeddings.append(emb.squeeze(0).cpu().numpy())
    return np.mean(np.stack(embeddings, axis=0), axis=0)


def compute_metrics(pos_scores: list[float], neg_scores: list[float], threshold: float) -> dict:
    tp = sum(score >= threshold for score in pos_scores)
    fn = len(pos_scores) - tp
    tn = sum(score < threshold for score in neg_scores)
    fp = len(neg_scores) - tn
    denom = len(pos_scores) + len(neg_scores)
    accuracy = (tp + tn) / max(1, denom)
    precision = tp / max(1, (tp + fp))
    recall = tp / max(1, len(pos_scores))
    f1 = (2 * precision * recall / max(1e-12, (precision + recall))) if (precision + recall) > 0 else 0.0
    tpr = recall
    fpr = fp / max(1, len(neg_scores))
    return {
        "threshold": threshold,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tpr": tpr,
        "fpr": fpr,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--voiceprints", required=True)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument("--bins", type=int, default=30)
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--target-accuracy", type=float, default=None)
    parser.add_argument("--target-precision", type=float, default=None)
    parser.add_argument("--target-recall", type=float, default=None)
    parser.add_argument("--target-f1", type=float, default=None)
    args = parser.parse_args()

    items, _ = build_index(args.data_dir)
    if not items:
        print("No audio files found.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _, config = load_checkpoint(args.checkpoint, device)
    model.eval()

    vp = np.load(args.voiceprints)
    voiceprints = {k: vp[k] for k in vp.files}
    if not voiceprints:
        raise ValueError("No voiceprints found in the provided file.")

    total = 0
    correct = 0
    per_speaker: dict[str, dict[str, int]] = {}
    pos_scores: list[float] = []
    neg_scores: list[float] = []

    for item in tqdm(items, desc="Evaluating"):
        emb = embed_audio(str(item.path), model, config, device)
        scores = {spk: cosine(emb, vp) for spk, vp in voiceprints.items()}
        if item.speaker not in scores:
            continue
        best_speaker, _ = max(scores.items(), key=lambda x: x[1])

        total += 1
        stats = per_speaker.setdefault(item.speaker, {"total": 0, "correct": 0})
        stats["total"] += 1
        if best_speaker == item.speaker:
            correct += 1
            stats["correct"] += 1

        pos_scores.append(scores[item.speaker])
        for spk, score in scores.items():
            if spk != item.speaker:
                neg_scores.append(score)

    top1 = correct / max(1, total)
    base_metrics = compute_metrics(pos_scores, neg_scores, args.threshold)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_path = out_dir / "verification_scores.png"
    plt.figure(figsize=(8, 4.5))
    plt.hist(pos_scores, bins=args.bins, alpha=0.6, label="same speaker", color="#2b6cb0")
    plt.hist(neg_scores, bins=args.bins, alpha=0.6, label="different speaker", color="#c05621")
    plt.axvline(
        args.threshold, color="black", linestyle="--", linewidth=1.2, label=f"threshold={args.threshold:.2f}"
    )
    plt.xlabel("Cosine similarity")
    plt.ylabel("Count")
    plt.title("Verification score distribution")
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    plt.close()

    csv_path = out_dir / "classification_accuracy.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["speaker", "correct", "total", "accuracy"])
        for speaker in sorted(per_speaker):
            stats = per_speaker[speaker]
            acc = stats["correct"] / max(1, stats["total"])
            writer.writerow([speaker, stats["correct"], stats["total"], f"{acc:.4f}"])

    print(f"Top-1 classification accuracy: {top1:.4f} ({correct}/{total})")
    for speaker in sorted(per_speaker):
        stats = per_speaker[speaker]
        acc = stats["correct"] / max(1, stats["total"])
        print(f"{speaker}: {acc:.4f} ({stats['correct']}/{stats['total']})")
    print(f"Verification accuracy @ threshold {args.threshold:.4f}: {base_metrics['accuracy']:.4f}")
    print(
        f"Precision: {base_metrics['precision']:.4f} | Recall: {base_metrics['recall']:.4f} | "
        f"F1: {base_metrics['f1']:.4f}"
    )
    print(f"TPR: {base_metrics['tpr']:.4f} | FPR: {base_metrics['fpr']:.4f}")
    print(f"Score plot saved to: {plot_path}")
    print(f"Per-speaker accuracy saved to: {csv_path}")

    if args.sweep:
        scores = np.array(pos_scores + neg_scores, dtype=np.float64)
        if scores.size == 0:
            print("No scores available for sweep.")
            return
        thresholds = np.unique(scores)
        thresholds = np.concatenate(
            ([thresholds[0] - 1e-6], thresholds, [thresholds[-1] + 1e-6])
        )

        best_f1 = None
        best_acc = None
        best_target = None

        def meets_target(m: dict) -> bool:
            if args.target_accuracy is not None and m["accuracy"] < args.target_accuracy:
                return False
            if args.target_precision is not None and m["precision"] < args.target_precision:
                return False
            if args.target_recall is not None and m["recall"] < args.target_recall:
                return False
            if args.target_f1 is not None and m["f1"] < args.target_f1:
                return False
            return True

        for thr in thresholds:
            metrics = compute_metrics(pos_scores, neg_scores, float(thr))
            if best_f1 is None or metrics["f1"] > best_f1["f1"]:
                best_f1 = metrics
            if best_acc is None or metrics["accuracy"] > best_acc["accuracy"]:
                best_acc = metrics
            if meets_target(metrics):
                if best_target is None or metrics["f1"] > best_target["f1"]:
                    best_target = metrics

        if best_f1 is not None:
            print(
                "Best F1 threshold "
                f"{best_f1['threshold']:.4f}: acc={best_f1['accuracy']:.4f}, "
                f"precision={best_f1['precision']:.4f}, recall={best_f1['recall']:.4f}, f1={best_f1['f1']:.4f}"
            )
        if best_acc is not None:
            print(
                "Best accuracy threshold "
                f"{best_acc['threshold']:.4f}: acc={best_acc['accuracy']:.4f}, "
                f"precision={best_acc['precision']:.4f}, recall={best_acc['recall']:.4f}, f1={best_acc['f1']:.4f}"
            )
        if (
            args.target_accuracy is not None
            or args.target_precision is not None
            or args.target_recall is not None
            or args.target_f1 is not None
        ):
            if best_target is None:
                print("No threshold meets the requested targets.")
            else:
                print(
                    "Target met at threshold "
                    f"{best_target['threshold']:.4f}: acc={best_target['accuracy']:.4f}, "
                    f"precision={best_target['precision']:.4f}, recall={best_target['recall']:.4f}, "
                    f"f1={best_target['f1']:.4f}"
                )


if __name__ == "__main__":
    main()
