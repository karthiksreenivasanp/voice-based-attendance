from dataclasses import dataclass


@dataclass
class Config:
    sample_rate: int = 16000
    segment_seconds: float = 3.0
    n_mels: int = 80
    embedding_dim: int = 192
    batch_size: int = 8
    epochs: int = 40
    lr: float = 1e-2
    weight_decay: float = 1e-4
    seed: int = 1337
    augment: bool = False
