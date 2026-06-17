from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from torch.utils.data import Dataset

from src.audio import augment_wav, load_audio, pad_or_crop, apply_butterworth_filter

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".webm"}


@dataclass(frozen=True)
class Item:
    path: Path
    speaker: str
    label: int


def build_index(data_dir: str) -> Tuple[List[Item], Dict[str, int]]:
    data_path = Path(data_dir)
    files = [p for p in data_path.rglob("*") if p.suffix.lower() in AUDIO_EXTS]
    speakers = sorted({p.parent.name for p in files})
    speaker_to_label = {spk: idx for idx, spk in enumerate(speakers)}
    items = []
    for p in files:
        speaker = p.parent.name
        items.append(Item(path=p, speaker=speaker, label=speaker_to_label[speaker]))
    return items, speaker_to_label


def split_by_speaker(items: List[Item], val_per_speaker: int = 1, seed: int = 1337):
    random.seed(seed)
    by_speaker: Dict[str, List[Item]] = {}
    for item in items:
        by_speaker.setdefault(item.speaker, []).append(item)

    train_items: List[Item] = []
    val_items: List[Item] = []

    for speaker, speaker_items in by_speaker.items():
        random.shuffle(speaker_items)
        if len(speaker_items) <= val_per_speaker:
            val_items.extend(speaker_items)
        else:
            val_items.extend(speaker_items[:val_per_speaker])
            train_items.extend(speaker_items[val_per_speaker:])

    return train_items, val_items


class SpeakerDataset(Dataset):
    def __init__(
        self,
        items: List[Item],
        sample_rate: int,
        segment_seconds: float,
        training: bool,
        augment: bool = False,
    ):
        self.items = items
        self.sample_rate = sample_rate
        self.segment_samples = int(sample_rate * segment_seconds)
        self.training = training
        self.augment = augment

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        item = self.items[idx]
        wav = load_audio(str(item.path), self.sample_rate)
        
        # 1. Apply Butterworth filter first!
        wav = apply_butterworth_filter(wav, self.sample_rate)
        
        # 2. Pad or crop
        wav = pad_or_crop(wav, self.segment_samples, random_crop=self.training)
        if self.training and self.augment:
            wav = augment_wav(wav, self.sample_rate)
        return {
            "wav": wav,
            "label": item.label,
            "speaker": item.speaker,
            "path": str(item.path),
        }
