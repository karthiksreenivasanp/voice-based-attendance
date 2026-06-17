# Voice-Based Attendance System 🎙️📡

A production-ready, biometric attendance tracking system powered by Deep Learning (ECAPA-TDNN) and Geolocation tracking. This repository provides a complete end-to-end solution, including a FastAPI backend, a real-time web dashboard, and a PyTorch-based machine learning pipeline for voice signature extraction and verification.

![Dashboard Preview](https://img.shields.io/badge/UI-Responsive-emerald.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![Firebase](https://img.shields.io/badge/Firebase-Database-FFCA28.svg)

---

## 🚀 Features

- **Biometric Voice Verification:** Achieves **>96% accuracy** utilizing a fine-tuned `ECAPA-TDNN` architecture (via SpeechBrain), trained on 16kHz resampled audio processed through a Butterworth Bandpass filter (300Hz-3400Hz) to preserve critical speech structures.
- **Dynamic Geofencing:** Employs the Haversine distance formula to establish a 20m virtual boundary originating from the teacher's locked coordinates. Students cannot mark attendance outside of this zone.
- **3-Step Voice Enrollment:** A streamlined browser-based enrollment phase requires 3 distinct voice phrases, storing an aggregated 192-dimensional embedding vector per student in the database for robust zero-shot verification.
- **Teacher Dashboard:** Real-time metrics, interactive geofence locks, 12-Hour AM/PM timestamps, and live updating presence grids, along with CSV export capabilities.
- **Hugging Face Deployment:** Complete configuration for deploying the deep learning inference API directly to Hugging Face Spaces.

## 📂 Repository Structure

The architecture is split into three main logical components:

```text
.
├── backend/                   # FastAPI Backend Server & API Routes
│   ├── api.py                 # Core endpoints (Auth, Sessions, Attendance, ML Inference)
│   ├── firestore_audio_storage.py # Firebase interactions
│   ├── Dockerfile             # Container configuration for Hugging Face
│   └── requirements.txt       # Production dependencies
│
├── frontend/                  # Vanilla JS, Tailwind CSS Web Application
│   ├── index.html             # Main Dashboard UI & Modals
│   └── check.js               # Application State, Geolocation logic, and API calls
│
└── ml_pipeline/               # PyTorch Model Training & Evaluation Pipeline
    ├── scripts/
    │   └── train.py           # ECAPA-TDNN fine-tuning and evaluation script
    ├── src/
    │   ├── audio.py           # Signal processing, Butterworth filter, 16kHz resampling
    │   ├── dataset.py         # PyTorch Dataset for .webm/.ogg chunks
    │   └── model.py           # SpeechBrain architecture wrapper
    └── pretrained_models/     # Cached SpkRec weights
```

## 🧠 Machine Learning Details

The voice processing engine bypasses typical vulnerabilities by:
1. Standardizing user microphone inputs to `16000Hz` using `torchaudio.transforms.Resample`.
2. Applying a `4th-order Butterworth Bandpass filter` to limit the signal between 300Hz and 3400Hz, removing device-specific static and ambient room noise.
3. Passing the chunked tensors through the **ECAPA-TDNN** encoder.
4. Using **Cosine Similarity** during inference to compare the new audio embedding against the 3-phrase aggregated enrollment embedding stored in Firebase.

*Evaluation Note:* The model demonstrates a 96% verification accuracy rate on the provided validation set, preventing false-positives while maintaining a seamless user experience.

## ⚙️ Local Development Setup

### 1. Prerequisites
- Python 3.9+
- A Firebase Project (Firestore Database)

### 2. Backend Installation

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Place your Firebase Admin SDK JSON file in the root directory and update the path in `backend/api.py` if necessary.

Start the backend:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Execution
The frontend is a vanilla web application. Simply serve it using any HTTP server:
```bash
cd frontend
python3 -m http.server 3000
```
Open `http://localhost:3000/index.html` in your browser. Ensure the browser allows Microphone and Location access (requires `localhost` or HTTPS).

## ☁️ Deployment

The backend is fully containerized and configured for deployment on **Hugging Face Spaces**. 
1. Create a Docker Space.
2. Push the `backend/` directory and the `ml_pipeline/work_dir/best.pt` file.
3. The Space will automatically install the requirements and launch `uvicorn` on port `7860`.

---
*Developed for robust, spoof-resistant biometric classroom tracking.*
