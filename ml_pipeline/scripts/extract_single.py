import argparse
import sys
import json
import numpy as np
import torch
from src.audio import chunk_audio, load_audio
from src.model import load_checkpoint

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--audio", required=True)
    args = parser.parse_args()

    device = torch.device("cpu")
    try:
        model, _, config = load_checkpoint(args.checkpoint, device)
        model.eval()
    except Exception as e:
        print(json.dumps({"error": f"Failed to load model: {str(e)}"}))
        sys.exit(1)

    try:
        wav = load_audio(args.audio, config["sample_rate"])
    except Exception as e:
        print(json.dumps({"error": f"Failed to load audio: {str(e)}"}))
        sys.exit(1)
        
    segment_samples = int(config["sample_rate"] * config["segment_seconds"])
    segments = chunk_audio(wav, segment_samples, None)

    embeddings = []
    with torch.no_grad():
        for seg in segments:
            seg = seg.unsqueeze(0).to(device)
            _, emb = model(seg)
            embeddings.append(emb.squeeze(0).cpu().numpy())
            
    if not embeddings:
        print(json.dumps({"error": "No voice segments found in audio"}))
        sys.exit(1)
        
    query = np.mean(np.stack(embeddings, axis=0), axis=0)
    print(json.dumps({"embedding": query.tolist()}))

if __name__ == "__main__":
    main()
