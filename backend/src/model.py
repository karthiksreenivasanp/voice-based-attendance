from __future__ import annotations

from typing import Dict, Tuple

import torch
import torch.nn as nn
import torchaudio
from speechbrain.lobes.models.ECAPA_TDNN import ECAPA_TDNN


class SpeakerModel(nn.Module):
    def __init__(
        self,
        num_speakers: int,
        sample_rate: int = 16000,
        n_mels: int = 80,
        embedding_dim: int = 192,
    ):
        super().__init__()
        self.melspec = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_mels=n_mels,
            n_fft=400,
            hop_length=160,
            win_length=400,
        )
        self.db = torchaudio.transforms.AmplitudeToDB(stype="power", top_db=80.0)

        self.ecapa = ECAPA_TDNN(
            input_size=n_mels,
            lin_neurons=embedding_dim,
            channels=[512, 512, 512, 512, 1536],
            kernel_sizes=[5, 3, 3, 3, 1],
            dilations=[1, 2, 3, 4, 1],
            attention_channels=128,
            res2net_scale=8,
            se_channels=128,
        )
        self.classifier = nn.Linear(embedding_dim, num_speakers)

    def forward(self, wav: torch.Tensor):
        feats = self.melspec(wav)
        feats = self.db(feats).transpose(1, 2)
        lengths = torch.ones(feats.size(0), device=feats.device)
        emb = self.ecapa(feats, lengths)
        if emb.dim() == 3 and emb.size(1) == 1:
            emb = emb.squeeze(1)
        logits = self.classifier(emb)
        return logits, emb


def load_checkpoint(path: str, device: torch.device) -> Tuple[SpeakerModel, Dict, Dict]:
    ckpt = torch.load(path, map_location=device)
    config = ckpt["config"]
    model = SpeakerModel(
        num_speakers=ckpt["num_speakers"],
        sample_rate=config["sample_rate"],
        n_mels=config["n_mels"],
        embedding_dim=config["embedding_dim"],
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    return model, ckpt["speaker_to_label"], config
