from __future__ import annotations

from typing import Dict, Tuple

import os
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

        # Load Pretrained ECAPA-TDNN from SpeechBrain
        from speechbrain.inference.speaker import EncoderClassifier
        device_str = "cuda" if torch.cuda.is_available() else "cpu"
        self.encoder = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "pretrained_models/spkrec-ecapa-voxceleb"),
            run_opts={"device": device_str}
        )
        # Freeze backbone to prevent collapse and rely on its high-quality zero-shot embeddings
        for param in self.encoder.parameters():
            param.requires_grad = False
            
        self.classifier = nn.Linear(embedding_dim, num_speakers)

    def forward(self, wav: torch.Tensor):
        # Ensure wav has batch dimension
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)
            
        # speechbrain's encoder expects (batch, samples)
        # It handles Mel extraction internally!
        emb = self.encoder.encode_batch(wav)
        
        # emb shape is usually (batch, 1, emb_dim)
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
    model.load_state_dict(ckpt["model_state"], strict=False)
    return model, ckpt["speaker_to_label"], config
