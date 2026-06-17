"""
Voice Attendance API - Firebase + Google Drive Backend
======================================================
FastAPI backend with:
  - Password authentication (bcrypt)
  - 3-step voice enrollment with Drive storage
  - Voice verification via cosine similarity
  - GPS geofencing via Haversine formula
  - Latecomer detection (configurable threshold)
  - Google Drive audio persistence

CONFIGURABLE VALUES (search for '# CONFIGURABLE'):
  - VOICE_MATCH_THRESHOLD: Minimum cosine similarity for voice match (default: 0.60)
  - GEOFENCE_DEFAULT_RADIUS: Default geofence radius in meters (default: 500.0)
  - LATECOMER_MINUTES: Minutes after session start to flag as late (default: 10)
  - SUBJECTS: List of available subjects
"""
from __future__ import annotations

import io, math, os, tempfile, subprocess, csv, bcrypt
import numpy as np
import torch
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

import sys
import os

def find_project_root():
    current = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(current, "ml_pipeline", "work_dir")):
        return current
    elif os.path.exists(os.path.join(current, "..", "ml_pipeline", "work_dir")):
        return os.path.abspath(os.path.join(current, ".."))
    return current

PROJECT_ROOT = find_project_root()
ml_pipeline_dir = os.path.join(PROJECT_ROOT, "ml_pipeline")
if ml_pipeline_dir not in sys.path:
    sys.path.insert(0, ml_pipeline_dir)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.audio import chunk_audio, apply_butterworth_filter
from src.model import load_checkpoint

# ============================================================
# CONFIGURABLE: Voice match threshold (0.0 to 1.0)
# Higher = stricter, Lower = more lenient
# ============================================================
VOICE_MATCH_THRESHOLD = 0.40

# ============================================================
# CONFIGURABLE: Default geofence radius in meters
# Set to 20m for high-accuracy GPS mobile phone usage.
# ============================================================
GEOFENCE_DEFAULT_RADIUS = 20.0

# ============================================================
# CONFIGURABLE: Minutes after session start to mark as late
# ============================================================
LATECOMER_MINUTES = 10

# ============================================================
# CONFIGURABLE: Available subjects for sessions
# ============================================================
SUBJECTS = ["RIS", "BDS", "R", "ANN", "Mini-Project", "Lab(BDA)", "Economics"]

app = FastAPI(title="Voice Attendance API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

os.makedirs("data", exist_ok=True)
app.mount("/data", StaticFiles(directory="data"), name="data")

# Global model variables
model = None
model_error_msg = None
voiceprints = None
config = None
device = None
db = None

# Temporary storage for multi-step enrollment
enrollment_cache = {}  # {student_id: {1: embedding, 2: embedding, ...}}
enrollment_audio_cache = {}  # {student_id: {1: bytes, 2: bytes, ...}}


def init_db():
    """Connect to Firebase Firestore using service account credentials."""
    global db
    if not firebase_admin._apps:
        # Check potential credential paths
        cred_paths = [
            os.path.join(PROJECT_ROOT, "backend", "firebase-key.json"),
            os.path.join(PROJECT_ROOT, "firebase-key.json"),
            "firebase-key.json",
            "database-attendance-syst-162cd-firebase-adminsdk-fbsvc-bd7ec3dd18.json",
            os.path.join(PROJECT_ROOT, "database-attendance-syst-162cd-firebase-adminsdk-fbsvc-bd7ec3dd18.json")
        ]
        
        selected_cred = None
        for path in cred_paths:
            if os.path.exists(path):
                selected_cred = path
                break
                
        if selected_cred is None:
            # Fallback to absolute path just in case
            selected_cred = "/home/karthiksreenivasanp/Documents/s_github/voice-based-attendance/backend/firebase-key.json"

        cred = credentials.Certificate(selected_cred)
        firebase_admin.initialize_app(cred)
    db = firestore.client()


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def convert_to_wav(audio_bytes: bytes) -> bytes:
    """Convert WebM audio to WAV format using ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as tin:
        tin.write(audio_bytes)
        tin.flush()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tout:
            subprocess.run(["ffmpeg", "-y", "-i", tin.name, tout.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tout.seek(0)
            return tout.read()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two embedding vectors."""
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-10))


def extract_embedding(audio_bytes: bytes) -> np.ndarray:
    """Extract a voice embedding from raw audio bytes. Returns a 192-dim numpy array."""
    import soundfile as sf
    wav_bytes = convert_to_wav(audio_bytes)
    wav, sr = sf.read(io.BytesIO(wav_bytes))
    wav_tensor = torch.tensor(wav, dtype=torch.float32)
    if wav_tensor.dim() > 1 and wav_tensor.size(1) > 1:
        wav_tensor = wav_tensor.mean(dim=1)
    if sr != config["sample_rate"]:
        import torchaudio.transforms as T
        wav_tensor = T.Resample(sr, config["sample_rate"], dtype=wav_tensor.dtype)(wav_tensor)
        sr = config["sample_rate"]

    # --- APPLY BUTTERWORTH FILTER ---
    wav_tensor = apply_butterworth_filter(wav_tensor, sample_rate=sr)

    segment_samples = int(config["sample_rate"] * config["segment_seconds"])
    segments = chunk_audio(wav_tensor, segment_samples, None)
    embeddings = []
    with torch.no_grad():
        for seg in segments:
            _, emb = model(seg.unsqueeze(0).to(device))
            embeddings.append(emb.squeeze(0).cpu().numpy())
    if not embeddings:
        raise HTTPException(status_code=400, detail="Audio too short.")
    return np.mean(np.stack(embeddings, axis=0), axis=0)


def embedding_to_csv_row(emb: np.ndarray, row_type: str) -> dict:
    """Convert an embedding to a CSV-ready dict with dim_0..dim_N columns."""
    row = {"timestamp": datetime.now().isoformat(), "type": row_type}
    for i, v in enumerate(emb):
        row[f"dim_{i}"] = f"{v:.6f}"
    return row


# ======================== STARTUP ========================

@app.on_event("startup")
def startup_event():
    global model, voiceprints, config, device, model_error_msg
    init_db()
    print("Loading model and voiceprints...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        model_path = os.path.join(PROJECT_ROOT, "ml_pipeline", "work_dir", "best.pt")
        if not os.path.exists(model_path):
            if os.path.exists("best.pt"):
                model_path = "best.pt"
            elif os.path.exists(os.path.join(PROJECT_ROOT, "best.pt")):
                model_path = os.path.join(PROJECT_ROOT, "best.pt")
        model, _, config = load_checkpoint(model_path, device)
        model.eval()
        print("Model loaded successfully.")
    except Exception as e:
        model_error_msg = str(e)
        import traceback
        model_error_msg += "\n" + traceback.format_exc()
        print(f"Error loading model: {e}")

    # Load voiceprints from local file
    voiceprints = {}
    try:
        vp = np.load("models/voiceprints_tuned.npz")
        for k in vp.files:
            arr = vp[k]
            if len(arr.shape) > 1:
                voiceprints[k] = [arr[i] for i in range(arr.shape[0])]
            else:
                voiceprints[k] = arr
        print(f"Loaded {len(voiceprints)} voiceprints from local file.")
    except Exception as e:
        print(f"No local voiceprints file: {e}")

    # Load voiceprints from Firebase (permanent storage)
    try:
        for doc in db.collection("users").stream():
            data = doc.to_dict()
            embs = data.get("voice_embeddings")
            if embs:
                voiceprints[doc.id] = [np.array(e, dtype=np.float32) for e in embs]
            else:
                emb = data.get("voice_embedding")
                if emb:
                    voiceprints[doc.id] = np.array(emb, dtype=np.float32)
        print(f"Total voiceprints loaded: {len(voiceprints)}")
    except Exception as e:
        model_error_msg = f"Error loading from Firebase: {e}"
        print(f"Error loading from Firebase: {e}")


@app.get("/")
def status():
    """Health check endpoint."""
    return {
        "status": "Voice Attendance API is running!",
        "subjects": SUBJECTS,
        "model_error": model_error_msg
    }


@app.get("/api/subjects")
def get_subjects():
    return {"subjects": SUBJECTS}


# ======================== AUTH (Feature 1) ========================

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "STUDENT"
    name: str = ""
    roll_no: str = ""
    course: str = ""
    subject: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(req: RegisterRequest):
    """Register a new user with hashed password stored in Firebase."""
    doc = db.collection("users").document(req.username).get()
    if doc.exists:
        raise HTTPException(status_code=409, detail="Username already exists. Please login.")
    
    hashed = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_data = {
        "role": req.role,
        "name": req.name or req.username,
        "roll_no": req.roll_no,
        "course": req.course,
        "subject": req.subject,
        "password_hash": hashed,
        "voice_enrolled": False,
        "created_at": datetime.now().isoformat(),
    }
    db.collection("users").document(req.username).set(user_data)
    return {"status": "success", **{k: v for k, v in user_data.items() if k != "password_hash"}}


@app.post("/api/login")
def login(req: LoginRequest):
    """Login with password verification."""
    doc = db.collection("users").document(req.username).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    
    data = doc.to_dict()
    stored_hash = data.get("password_hash", "")
    if not stored_hash or not bcrypt.checkpw(req.password.encode("utf-8"), stored_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Wrong password.")
    
    return {
        "status": "success",
        "role": data.get("role"),
        "name": data.get("name"),
        "roll_no": data.get("roll_no"),
        "course": data.get("course"),
        "subject": data.get("subject"),
        "mentor": data.get("mentor"),
        "voice_enrolled": data.get("voice_enrolled", False),
    }

class UpdateMentorRequest(BaseModel):
    student_id: str
    mentor: str

@app.post("/api/update-mentor")
def update_mentor(req: UpdateMentorRequest):
    """Update a student's assigned mentor."""
    db.collection("users").document(req.student_id).update({"mentor": req.mentor})
    return {"status": "success"}


# ======================== LISTS (Feature 4) ========================

@app.get("/api/teachers")
def get_teachers():
    docs = db.collection("users").where(filter=FieldFilter("role", "==", "TEACHER")).stream()
    return {"status": "success", "teachers": [
        {"id": d.id, "name": d.to_dict().get("name"), "subject": d.to_dict().get("subject")} for d in docs
    ]}

@app.get("/api/students")
def get_students():
    """Get all enrolled students (Feature 4)."""
    docs = db.collection("users").where(filter=FieldFilter("role", "==", "STUDENT")).stream()
    students = []
    for d in docs:
        data = d.to_dict()
        students.append({
            "id": d.id, "name": data.get("name"), "roll_no": data.get("roll_no"),
            "course": data.get("course"), "voice_enrolled": data.get("voice_enrolled", False),
        })
    return {"status": "success", "students": students}


# ======================== SESSIONS (Feature 5) ========================

class SessionStartRequest(BaseModel):
    teacher_id: str
    lat: float
    lng: float
    radius: float = GEOFENCE_DEFAULT_RADIUS
    subject: str = ""

class SessionStopRequest(BaseModel):
    teacher_id: str

@app.post("/api/session/start")
def start_session(req: SessionStartRequest):
    # Deactivate ALL globally active sessions so only one class runs at a time
    for doc in db.collection("sessions").where(filter=FieldFilter("is_active", "==", True)).stream():
        doc.reference.update({"is_active": False, "end_time": datetime.now().isoformat()})
    
    sess = {
        "teacher_id": req.teacher_id,
        "lat": req.lat, "lng": req.lng, "radius": req.radius,
        "subject": req.subject,
        "is_active": True,
        "start_time": datetime.now().isoformat(),
    }
    _, ref = db.collection("sessions").add(sess)
    return {"status": "success", "session_id": ref.id, "start_time": sess["start_time"], "subject": req.subject}

@app.post("/api/session/stop")
def stop_session(req: SessionStopRequest):
    # Stop all globally active sessions so any teacher can take over
    for doc in db.collection("sessions").where(filter=FieldFilter("is_active", "==", True)).stream():
        doc.reference.update({"is_active": False, "end_time": datetime.now().isoformat()})
    return {"status": "success"}

@app.get("/api/session/active")
def get_active_session():
    """Get the currently active session details (Feature 5)."""
    docs = list(db.collection("sessions").where(filter=FieldFilter("is_active", "==", True)).stream())
    if not docs:
        return {"status": "success", "active": False}
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]
    data = sess.to_dict()
    return {"status": "success", "active": True, "session_id": sess.id, **data}


# ======================== 3-STEP ENROLLMENT (Feature 7) ========================

@app.post("/api/enroll-voice-step")
def enroll_voice_step(
    student_id: str = Form(...),
    step: int = Form(...),
    audio_file: UploadFile = File(...),
):
    """Enroll voice in 3 steps. Step 1/2/3, then combine on step 3."""
    global voiceprints

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    if step not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Step must be 1, 2, or 3.")

    audio_bytes = audio_file.file.read()

    # Save audio locally for immediate playback
    phrase_names = {1: "phrase1", 2: "phrase2", 3: "phrase3"}
    local_path = f"data/{student_id}_{phrase_names[step]}.webm"
    with open(local_path, "wb") as f:
        f.write(audio_bytes)

    # Extract embedding
    emb = extract_embedding(audio_bytes)

    # Cache this step
    if student_id not in enrollment_cache:
        enrollment_cache[student_id] = {}
        enrollment_audio_cache[student_id] = {}
    enrollment_cache[student_id][step] = emb
    enrollment_audio_cache[student_id][step] = audio_bytes

    if step < 3:
        return {"status": "success", "step": step, "message": f"Step {step} recorded. Proceed to step {step+1}."}

    # Step 3: Combine all 3 embeddings and finalize
    if not all(s in enrollment_cache.get(student_id, {}) for s in (1, 2, 3)):
        raise HTTPException(status_code=400, detail="Missing earlier steps. Please re-enroll from step 1.")

    emb1 = enrollment_cache[student_id][1]
    emb2 = enrollment_cache[student_id][2]
    emb3 = enrollment_cache[student_id][3]
    combined = np.mean(np.stack([emb1, emb2, emb3], axis=0), axis=0)
    all_embeddings = [emb1, emb2, emb3]

    # Save to memory
    if voiceprints is None:
        voiceprints = {}
    voiceprints[student_id] = all_embeddings

    # Save to local npz as backup
    try:
        save_dict = {}
        for k, v in voiceprints.items():
            if isinstance(v, list):
                save_dict[k] = np.stack(v, axis=0)
            else:
                save_dict[k] = v
        np.savez("models/voiceprints_tuned.npz", **save_dict)
    except Exception:
        pass

    # Save permanently to Firebase
    db.collection("users").document(student_id).set({
        "voice_enrolled": True,
        "voice_embeddings": [e.tolist() for e in all_embeddings],
        "voice_embedding": combined.tolist(), # Fallback
    }, merge=True)

    # Upload to Firestore (non-blocking, best-effort)
    csv_rows = []
    try:
        from firestore_audio_storage import upload_enrollment_audio, save_embeddings_csv
        for s in (1, 2, 3):
            upload_enrollment_audio(student_id, s, enrollment_audio_cache[student_id][s])
            csv_rows.append(embedding_to_csv_row(enrollment_cache[student_id][s], f"enroll_phrase{s}"))
        csv_rows.append(embedding_to_csv_row(combined, "combined"))
        save_embeddings_csv(student_id, csv_rows)
    except Exception as e:
        print(f"Drive upload failed (non-critical): {e}")

    # Cleanup cache
    enrollment_cache.pop(student_id, None)
    enrollment_audio_cache.pop(student_id, None)

    return {"status": "success", "step": 3, "message": "All 3 phrases enrolled successfully!"}


# ======================== DELETE VOICE (Feature 3) ========================

@app.delete("/api/voice/{student_id}")
def delete_voice(student_id: str):
    """Delete voice enrollment from Firebase. Keeps Drive data for audit."""

    doc = db.collection("users").document(student_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found.")

    data = doc.to_dict()
    old_embedding = data.get("voice_embedding")

    # Remove from Firebase
    db.collection("users").document(student_id).update({
        "voice_enrolled": False,
        "voice_embedding": firestore.DELETE_FIELD,
    })

    # Remove from memory
    voiceprints.pop(student_id, None)

    # Append deletion audit row to Drive CSV (best-effort)
    try:
        from firestore_audio_storage import append_embedding_row
        if old_embedding:
            row = {"timestamp": datetime.now().isoformat(), "type": "deleted"}
            for i, val in enumerate(old_embedding):
                row[f"dim_{i}"] = val
            append_embedding_row(student_id, row)
    except Exception as e:
        print(f"Failed to update storage audit trail: {e}")

    return {"status": "success", "message": "Voice enrollment deleted."}


# ======================== VERIFY VOICE ========================

@app.post("/api/verify-voice")
def verify_voice(student_id: str = Form(...), audio_file: UploadFile = File(...)):
    if model is None or not voiceprints:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    audio_bytes = audio_file.file.read()

    # Save test audio locally
    with open(f"data/{student_id}_test.webm", "wb") as f:
        f.write(audio_bytes)

    emb = extract_embedding(audio_bytes)

    # Upload verification audio and save attempt log to Firestore
    try:
        from firestore_audio_storage import upload_verification_audio, append_embedding_row
        upload_verification_audio(student_id, audio_bytes)
        append_embedding_row(student_id, embedding_to_csv_row(emb, "verify_attempt"))
    except Exception as e:
        print(f"Drive upload failed: {e}")

    if student_id in voiceprints:
        target = voiceprints[student_id]
        if isinstance(target, list):
            score = max(cosine(emb, e) for e in target)
        else:
            score = cosine(emb, target)
    else:
        scores = {}
        for spk, target in voiceprints.items():
            if isinstance(target, list):
                scores[spk] = max(cosine(emb, e) for e in target)
            else:
                scores[spk] = cosine(emb, target)
        if not scores:
            raise HTTPException(status_code=400, detail="No voiceprints enrolled.")
        _, score = max(scores.items(), key=lambda x: x[1])

    is_match = bool(score >= VOICE_MATCH_THRESHOLD)
    
    # Scale score for UI presentation (Raw 0.40 -> 80% UI Confidence)
    if is_match:
        display_score = 0.80 + ((score - VOICE_MATCH_THRESHOLD) / (1.0 - VOICE_MATCH_THRESHOLD)) * 0.19
    else:
        display_score = (score / VOICE_MATCH_THRESHOLD) * 0.79
        
    return {
        "status": "success" if is_match else "failed",
        "message": "Identity verified" if is_match else "Identity could not be verified",
        "confidence": float(display_score),
    }


# ======================== MARK ATTENDANCE (Feature 8: Latecomers) ========================

class MarkAttendanceRequest(BaseModel):
    student_id: str
    lat: float
    lng: float
    confidence: float

@app.post("/api/mark-attendance")
def mark_attendance(req: MarkAttendanceRequest):
    docs = list(db.collection("sessions").where(filter=FieldFilter("is_active", "==", True)).stream())
    if not docs:
        raise HTTPException(status_code=400, detail="No active class session.")
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]
    t = sess.to_dict()

    # Geofence check
    if req.lat != 0.0 and req.lng != 0.0:
        dist = haversine(req.lat, req.lng, t.get("lat", 0), t.get("lng", 0))
        if dist > t.get("radius", GEOFENCE_DEFAULT_RADIUS):
            raise HTTPException(status_code=403, detail=f"Geofence rejected. You are {dist:.1f}m away. Must be within {t.get('radius', GEOFENCE_DEFAULT_RADIUS)}m.")

    # Check if already marked
    existing = list(db.collection("attendance").where(filter=FieldFilter("session_id", "==", sess.id)).where(filter=FieldFilter("student_id", "==", req.student_id)).stream())
    if existing:
        return {"status": "success", "message": "Attendance already marked for this session."}

    # Latecomer detection
    now = datetime.now()
    is_late = False
    try:
        start = datetime.fromisoformat(t.get("start_time", now.isoformat()))
        if (now - start) > timedelta(minutes=LATECOMER_MINUTES):
            is_late = True
    except Exception:
        pass

    db.collection("attendance").add({
        "session_id": sess.id,
        "student_id": req.student_id,
        "status": "LATE" if is_late else "PRESENT",
        "confidence": req.confidence,
        "timestamp": now.isoformat(),
        "lat": req.lat, "lng": req.lng,
        "is_late": is_late,
        "subject": t.get("subject", ""),
    })

    msg = "Attendance marked as LATE (arrived after 10 min)." if is_late else "Attendance successfully marked."
    return {"status": "success", "message": msg, "is_late": is_late}


# ======================== ATTENDANCE (Feature 6 & 8) ========================

@app.get("/api/attendance")
def get_attendance():
    """Get attendance for the current active session."""
    docs = list(db.collection("sessions").where(filter=FieldFilter("is_active", "==", True)).stream())
    if not docs:
        return {"status": "success", "records": []}
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]

    records = []
    for doc in db.collection("attendance").where(filter=FieldFilter("session_id", "==", sess.id)).stream():
        d = doc.to_dict()
        user = db.collection("users").document(d["student_id"]).get()
        udata = user.to_dict() if user.exists else {}
        records.append({
            "student_id": d["student_id"], "name": udata.get("name", "Unknown"),
            "status": d["status"], "confidence": d.get("confidence", 0),
            "timestamp": d.get("timestamp", ""), "is_late": d.get("is_late", False),
        })
    return {"status": "success", "records": records}


class AttendanceUpdateRequest(BaseModel):
    student_id: str
    status: str

@app.post("/api/attendance/update")
def update_attendance(req: AttendanceUpdateRequest):
    """Teacher can override attendance status (e.g., change LATE to PRESENT)."""
    docs = list(db.collection("sessions").where(filter=FieldFilter("is_active", "==", True)).stream())
    if not docs:
        raise HTTPException(status_code=400, detail="No active session")
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]

    att = list(db.collection("attendance").where(filter=FieldFilter("session_id", "==", sess.id)).where(filter=FieldFilter("student_id", "==", req.student_id)).stream())
    if att:
        att[0].reference.update({"status": req.status})
    else:
        db.collection("attendance").add({
            "session_id": sess.id, "student_id": req.student_id,
            "status": req.status, "confidence": 1.0,
            "timestamp": datetime.now().isoformat(), "lat": 0.0, "lng": 0.0, "is_late": False,
        })
    return {"status": "success"}


@app.get("/api/attendance/history/{student_id}")
def get_attendance_history(student_id: str):
    """Get full attendance history for a student across all sessions (Feature 6)."""
    att_docs = list(db.collection("attendance").where(filter=FieldFilter("student_id", "==", student_id)).stream())
    records = []
    session_cache = {}
    for doc in att_docs:
        d = doc.to_dict()
        sid = d.get("session_id", "")
        if sid not in session_cache:
            sdoc = db.collection("sessions").document(sid).get()
            session_cache[sid] = sdoc.to_dict() if sdoc.exists else {}
        sdata = session_cache[sid]
        records.append({
            "date": d.get("timestamp", "")[:10],
            "subject": d.get("subject") or sdata.get("subject", "N/A"),
            "status": d["status"], "confidence": d.get("confidence", 0),
            "timestamp": d.get("timestamp", ""), "is_late": d.get("is_late", False),
        })
    records.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"status": "success", "records": records}


# ======================== CSV EXPORT (Feature 8) ========================

@app.get("/api/export-csv")
def export_csv():
    """Server-side CSV export with full student details and latecomer info."""
    docs = list(db.collection("sessions").stream())
    if not docs:
        raise HTTPException(status_code=400, detail="No sessions found to export")
    
    # Sort all sessions by start_time descending to get the most recent one
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]
    sdata = sess.to_dict()

    att_docs = list(db.collection("attendance").where(filter=FieldFilter("session_id", "==", sess.id)).stream())
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Roll No", "Course", "Subject", "Session Date", "Session Time", "Status", "Confidence", "Latitude", "Longitude", "Is Late", "Marked At"])

    for doc in att_docs:
        d = doc.to_dict()
        user = db.collection("users").document(d["student_id"]).get()
        u = user.to_dict() if user.exists else {}
        writer.writerow([
            d["student_id"], u.get("name", ""), u.get("roll_no", ""), u.get("course", ""),
            sdata.get("subject", ""), sdata.get("start_time", "")[:10], sdata.get("start_time", "")[11:19],
            d["status"], f"{d.get('confidence', 0):.2f}",
            d.get("lat", ""), d.get("lng", ""), d.get("is_late", False), d.get("timestamp", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{datetime.now().strftime('%Y-%m-%d')}.csv"},
    )


# ======================== VOICE PLAYBACK URLS (Feature 9) ========================

from fastapi.responses import StreamingResponse, Response

@app.get("/api/audio/{student_id}/{phrase}")
def proxy_audio(student_id: str, phrase: str):
    """Proxy audio directly from Firestore Base64 to avoid CORS/redirect issues."""
    try:
        from firestore_audio_storage import get_enrollment_audio_content
        content = get_enrollment_audio_content(student_id, phrase)
        if content:
            return Response(content=content, media_type="audio/webm")
    except Exception as e:
        print(f"Proxy audio failed: {e}")
    raise HTTPException(status_code=404, detail="Audio not found")

@app.get("/api/voice-urls/{student_id}")
def get_voice_urls(student_id: str):
    """Get playback URLs for enrolled voice recordings."""
    urls = {
        "phrase1": f"/api/audio/{student_id}/phrase1",
        "phrase2": f"/api/audio/{student_id}/phrase2",
        "phrase3": f"/api/audio/{student_id}/phrase3",
    }
    return {"status": "success", "urls": urls, "source": "proxy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
