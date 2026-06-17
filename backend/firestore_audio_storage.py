import io
import csv
import base64
from firebase_admin import firestore
from datetime import datetime

def _get_db():
    return firestore.client()

def upload_enrollment_audio(student_id: str, phrase_num: int, audio_bytes: bytes) -> str:
    """Convert audio to base64 and upload as a Firestore document."""
    db = _get_db()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    doc_id = f"{student_id}_phrase{phrase_num}"
    db.collection("enrolled_audio").document(doc_id).set({
        "student_id": student_id,
        "phrase_num": phrase_num,
        "audio_b64": audio_b64,
        "timestamp": datetime.now().isoformat()
    })
    return f"/api/audio/{student_id}/phrase{phrase_num}"

def upload_verification_audio(student_id: str, audio_bytes: bytes) -> str:
    """Upload an attendance verification audio file as base64."""
    db = _get_db()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    doc_id = f"{student_id}_{timestamp}"
    db.collection("attendance_audio").document(doc_id).set({
        "student_id": student_id,
        "audio_b64": audio_b64,
        "timestamp": datetime.now().isoformat()
    })
    return f"/api/audio_verify/{doc_id}"

def get_enrollment_audio_content(student_id: str, phrase: str) -> bytes:
    """Retrieve base64 audio from Firestore and decode to bytes."""
    db = _get_db()
    
    # Map "phrase1" to integer 1
    phrase_num = 1
    if "phrase2" in phrase: phrase_num = 2
    elif "phrase3" in phrase: phrase_num = 3
        
    doc_id = f"{student_id}_phrase{phrase_num}"
    doc = db.collection("enrolled_audio").document(doc_id).get()
    
    if doc.exists:
        data = doc.to_dict()
        audio_b64 = data.get("audio_b64")
        if audio_b64:
            return base64.b64decode(audio_b64)
    return None

def save_embeddings_csv(student_id: str, rows: list) -> str:
    """Save embeddings CSV as a text string inside a Firestore document."""
    if not rows: return ""
    db = _get_db()
    
    sample = rows[0]
    emb_keys = sorted([k for k in sample.keys() if k.startswith("dim_")])
    fieldnames = ["student_id", "timestamp", "type"] + emb_keys
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        row["student_id"] = student_id
        writer.writerow(row)
        
    csv_text = output.getvalue()
    
    db.collection("csv_storage").document(student_id).set({
        "student_id": student_id,
        "csv_text": csv_text,
        "updated_at": datetime.now().isoformat()
    })
    return f"firestore_csv_{student_id}"

def append_embedding_row(student_id: str, new_row: dict) -> None:
    """Append a row to the existing embeddings CSV string in Firestore."""
    db = _get_db()
    doc_ref = db.collection("csv_storage").document(student_id)
    doc = doc_ref.get()
    
    existing_rows = []
    if doc.exists:
        data = doc.to_dict()
        csv_text = data.get("csv_text", "")
        if csv_text:
            reader = csv.DictReader(io.StringIO(csv_text))
            existing_rows = list(reader)
            
    new_row["student_id"] = student_id
    existing_rows.append(new_row)
    save_embeddings_csv(student_id, existing_rows)
