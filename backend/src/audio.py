from __future__ import annotations

from typing import List

import torch
import torchaudio


def load_audio(path: str, sample_rate: int) -> torch.Tensor:
    wav, sr = torchaudio.load(path)
    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    wav = wav.squeeze(0)
    if sr != sample_rate:
        wav = torchaudio.functional.resample(wav, sr, sample_rate)
    return wav

def apply_butterworth_filter(wav: torch.Tensor, sample_rate: int, lowcut: float = 300.0, highcut: float = 3400.0, order: int = 5) -> torch.Tensor:
    """
    Apply a Butterworth bandpass filter using scipy.signal.filtfilt (zero-phase).
    """
    from scipy.signal import butter, filtfilt
    import numpy as np

    # Convert to numpy
    wav_np = wav.numpy()
    
    # Nyquist frequency is half the sample rate
    nyq = 0.5 * sample_rate
    low = lowcut / nyq
    high = highcut / nyq
    
    # Generate Butterworth filter coefficients
    b, a = butter(order, [low, high], btype='band')
    
    # Apply filter
    filtered_wav_np = filtfilt(b, a, wav_np).copy()
    
    # Convert back to torch tensor
    return torch.from_numpy(filtered_wav_np).float()


def augment_wav(wav: torch.Tensor, sample_rate: int) -> torch.Tensor:
    # Random gain
    gain = torch.empty(1).uniform_(0.8, 1.2).item()
    wav = wav * gain

    # Random additive noise at 15-25 dB SNR
    if torch.rand(1).item() < 0.5:
        rms = torch.sqrt(torch.mean(wav**2) + 1e-12)
        noise = torch.randn_like(wav)
        noise_rms = torch.sqrt(torch.mean(noise**2) + 1e-12)
        snr_db = float(torch.empty(1).uniform_(15.0, 25.0).item())
        noise_scale = rms / (10 ** (snr_db / 20)) / noise_rms
        wav = wav + noise * noise_scale

    # Random time shift up to +/-100ms
    if torch.rand(1).item() < 0.5:
        max_shift = int(0.1 * sample_rate)
        shift = int(torch.randint(-max_shift, max_shift + 1, (1,)).item())
        if shift > 0:
            wav = torch.nn.functional.pad(wav, (shift, 0))[:-shift]
        elif shift < 0:
            wav = torch.nn.functional.pad(wav, (0, -shift))[(-shift):]

    return wav.clamp(-1.0, 1.0)


def pad_or_crop(wav: torch.Tensor, num_samples: int, random_crop: bool) -> torch.Tensor:
    if wav.numel() == num_samples:
        return wav
    if wav.numel() < num_samples:
        pad = num_samples - wav.numel()
        return torch.nn.functional.pad(wav, (0, pad))
    if random_crop:
        max_start = wav.numel() - num_samples
        start = torch.randint(0, max_start + 1, (1,)).item()
    else:
        start = (wav.numel() - num_samples) // 2
    return wav[start : start + num_samples]


def chunk_audio(wav: torch.Tensor, num_samples: int, hop_samples: int | None = None) -> List[torch.Tensor]:
    if hop_samples is None:
        hop_samples = num_samples
    if wav.numel() <= num_samples:
        return [pad_or_crop(wav, num_samples, random_crop=False)]
    chunks = []
    for start in range(0, wav.numel() - num_samples + 1, hop_samples):
        chunks.append(wav[start : start + num_samples])
    if (wav.numel() - num_samples) % hop_samples != 0:
        chunks.append(wav[-num_samples:])
    return chunks
