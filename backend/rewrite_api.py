import re

with open("/home/karthiksreenivasanp/Documents/s_github/voice-attendance-firebase/backend/api.py", "r") as f:
    content = f.read()

# Imports
content = content.replace("import sqlite3", "import firebase_admin\nfrom firebase_admin import credentials, firestore\nfrom google.cloud.firestore_v1.base_query import FieldFilter")

# init_db and globals
new_init = """db = None

def init_db():
    global db
    if not firebase_admin._apps:
        if os.path.exists('firebase-key.json'):
            cred = credentials.Certificate('firebase-key.json')
        else:
            cred = credentials.Certificate('/home/karthiksreenivasanp/Documents/s_github/voice-attendance-4b469-firebase-adminsdk-fbsvc-ad340dded7.json')
        firebase_admin.initialize_app(cred)
    db = firestore.client()
"""
content = re.sub(r'DB_PATH = "attendance.db"\n\ndef init_db\(\):[\s\S]*?conn\.close\(\)', new_init, content)

# Login
login_new = """@app.post("/api/login")
async def login(req: LoginRequest):
    users_ref = db.collection('users').document(req.username)
    doc = users_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        return {
            "status": "success", 
            "role": data.get("role"), 
            "name": data.get("name"),
            "roll_no": data.get("roll_no"),
            "course": data.get("course"),
            "subject": data.get("subject"),
            "voice_enrolled": data.get("voice_enrolled", False)
        }
    else:
        role = req.role or "STUDENT"
        name = req.name or req.username
        new_user = {
            "role": role,
            "name": name,
            "roll_no": req.roll_no,
            "course": req.course,
            "subject": req.subject,
            "voice_enrolled": False
        }
        users_ref.set(new_user)
        return {"status": "success", **new_user}"""
content = re.sub(r'@app\.post\("/api/login"\)\nasync def login[\s\S]*?(?=@app\.get\("/api/teachers"\))', login_new + '\n\n', content)

# Teachers
teachers_new = """@app.get("/api/teachers")
async def get_teachers():
    docs = db.collection('users').where(filter=FieldFilter("role", "==", "TEACHER")).stream()
    teachers = [{"id": doc.id, "name": doc.to_dict().get("name"), "subject": doc.to_dict().get("subject")} for doc in docs]
    return {"status": "success", "teachers": teachers}"""
content = re.sub(r'@app\.get\("/api/teachers"\)\nasync def get_teachers[\s\S]*?(?=class SessionRequest)', teachers_new + '\n\n', content)

# Session Start
session_start_new = """@app.post("/api/session/start")
async def start_session(req: SessionRequest):
    docs = db.collection('sessions').where(filter=FieldFilter("teacher_id", "==", req.teacher_id)).where(filter=FieldFilter("is_active", "==", True)).stream()
    for doc in docs:
        doc.reference.update({"is_active": False})
        
    new_sess = {
        "teacher_id": req.teacher_id,
        "lat": req.lat,
        "lng": req.lng,
        "radius": req.radius,
        "is_active": True,
        "start_time": datetime.now().isoformat()
    }
    _, doc_ref = db.collection('sessions').add(new_sess)
    return {"status": "success", "session_id": doc_ref.id}"""
content = re.sub(r'@app\.post\("/api/session/start"\)\nasync def start_session[\s\S]*?(?=class StopSessionRequest)', session_start_new + '\n\n', content)

# Session Stop
session_stop_new = """@app.post("/api/session/stop")
async def stop_session(req: StopSessionRequest):
    docs = db.collection('sessions').where(filter=FieldFilter("teacher_id", "==", req.teacher_id)).where(filter=FieldFilter("is_active", "==", True)).stream()
    for doc in docs:
        doc.reference.update({"is_active": False})
    return {"status": "success"}"""
content = re.sub(r'@app\.post\("/api/session/stop"\)\nasync def stop_session[\s\S]*?(?=@app\.get\("/api/attendance"\))', session_stop_new + '\n\n', content)

# Get Attendance
get_att_new = """@app.get("/api/attendance")
async def get_attendance():
    docs = list(db.collection('sessions').where(filter=FieldFilter("is_active", "==", True)).stream())
    if not docs:
        return {"status": "success", "records": []}
    
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]
    session_id = sess.id
    
    att_docs = db.collection('attendance').where(filter=FieldFilter("session_id", "==", session_id)).stream()
    records = []
    for doc in att_docs:
        data = doc.to_dict()
        user_doc = db.collection('users').document(data["student_id"]).get()
        name = user_doc.to_dict().get("name") if user_doc.exists else "Unknown"
        records.append({
            "student_id": data["student_id"],
            "name": name,
            "status": data["status"],
            "confidence": data["confidence"]
        })
    return {"status": "success", "records": records}"""
content = re.sub(r'@app\.get\("/api/attendance"\)\nasync def get_attendance[\s\S]*?(?=class AttendanceUpdateRequest)', get_att_new + '\n\n', content)

# Update Attendance
update_att_new = """@app.post("/api/attendance/update")
async def update_attendance(req: AttendanceUpdateRequest):
    docs = list(db.collection('sessions').where(filter=FieldFilter("is_active", "==", True)).stream())
    if not docs:
        raise HTTPException(status_code=400, detail="No active session")
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]
    session_id = sess.id
    
    att_docs = list(db.collection('attendance').where(filter=FieldFilter("session_id", "==", session_id)).where(filter=FieldFilter("student_id", "==", req.student_id)).stream())
    if att_docs:
        att_docs[0].reference.update({"status": req.status})
    else:
        db.collection('attendance').add({
            "session_id": session_id,
            "student_id": req.student_id,
            "status": req.status,
            "confidence": 1.0,
            "timestamp": datetime.now().isoformat(),
            "lat": 0.0,
            "lng": 0.0
        })
    return {"status": "success"}"""
content = re.sub(r'@app\.post\("/api/attendance/update"\)\nasync def update_attendance[\s\S]*?(?=@app\.post\("/api/enroll-voice"\))', update_att_new + '\n\n', content)

# Mark Attendance
mark_att_new = """@app.post("/api/mark-attendance")
async def mark_attendance(req: MarkAttendanceRequest):
    docs = list(db.collection('sessions').where(filter=FieldFilter("is_active", "==", True)).stream())
    if not docs:
        raise HTTPException(status_code=400, detail="No active class session to mark attendance for.")
    sess = sorted(docs, key=lambda x: x.to_dict().get("start_time", ""), reverse=True)[0]
    session_id = sess.id
    t_data = sess.to_dict()
    t_lat = t_data.get("lat", 0.0)
    t_lng = t_data.get("lng", 0.0)
    t_radius = t_data.get("radius", 500.0)
    
    if req.lat != 0.0 and req.lng != 0.0:
        dist = haversine(req.lat, req.lng, t_lat, t_lng)
        if dist > t_radius:
            raise HTTPException(status_code=403, detail=f"Geofence rejected. You are {dist:.1f}m away. Must be within {t_radius}m.")

    att_docs = list(db.collection('attendance').where(filter=FieldFilter("session_id", "==", session_id)).where(filter=FieldFilter("student_id", "==", req.student_id)).stream())
    if not att_docs:
        db.collection('attendance').add({
            "session_id": session_id,
            "student_id": req.student_id,
            "status": 'PRESENT',
            "confidence": req.confidence,
            "timestamp": datetime.now().isoformat(),
            "lat": req.lat,
            "lng": req.lng
        })
    return {"status": "success", "message": "Attendance successfully marked."}"""
content = re.sub(r'@app\.post\("/api/mark-attendance"\)\nasync def mark_attendance[\s\S]*?(?=if __name__ == "__main__":)', mark_att_new + '\n\n', content)

# Voice Enroll Firebase persistence
enroll_firebase = """        # Update voiceprints dictionary
        if voiceprints is None:
            voiceprints = {}
        voiceprints[student_id] = query

        # Save to .npz
        np.savez("models/voiceprints_tuned.npz", **voiceprints)

        # Mark in Firestore
        db.collection('users').document(student_id).set({"voice_enrolled": True}, merge=True)

        return {"status": "success", "message": "Voice enrolled successfully!"}"""
content = content.replace('        # Update voiceprints dictionary\n        if voiceprints is None:\n            voiceprints = {}\n        voiceprints[student_id] = query\n\n        # Save to .npz\n        np.savez("models/voiceprints_tuned.npz", **voiceprints)\n\n        return {"status": "success", "message": "Voice enrolled successfully!"}', enroll_firebase)

with open("/home/karthiksreenivasanp/Documents/s_github/voice-attendance-firebase/backend/api.py", "w") as f:
    f.write(content)

print("api.py converted to Firebase")
