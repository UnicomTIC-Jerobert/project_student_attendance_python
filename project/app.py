from flask import Flask, render_template, request, Response, redirect, url_for, jsonify
import cv2
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --- Configuration ---
DATASET_PATH = 'dataset'
NUM_IMAGES_TO_CAPTURE = 30
DATABASE_NAME = 'attendance.db'

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL, -- e.g., 'entry', 'exit', 'presence'
            camera_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

# --- API Endpoint for Logging ---
@app.route('/api/log_attendance', methods=['POST'])
def log_attendance():
    data = request.get_json()
    if not data or 'student_id' not in data:
        return jsonify({"status": "error", "message": "Missing student_id"}), 400

    student_id = data['student_id']
    event_type = data.get('event_type', 'presence') # Default to 'presence'
    camera_id = data.get('camera_id', 'unknown')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO attendance (student_id, timestamp, event_type, camera_id) VALUES (?, ?, ?, ?)",
                       (student_id, timestamp, event_type, camera_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": f"Logged {student_id}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Web Pages ---
@app.route('/')
def index():
    students = [s for s in os.listdir(DATASET_PATH) if os.path.isdir(os.path.join(DATASET_PATH, s))]
    return render_template('index.html', students=students)

@app.route('/logs')
def view_logs():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, timestamp, event_type, camera_id FROM attendance ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles the student registration form."""
    if request.method == 'POST':
        student_id = request.form['student_id']
        if not student_id:
            return "Error: Student ID is required.", 400
        
        student_dir = os.path.join(DATASET_PATH, student_id)
        os.makedirs(student_dir, exist_ok=True)
        
        # We will handle the image capture on a separate page/logic
        return redirect(url_for('capture_images', student_id=student_id))
        
    return render_template('register.html')

@app.route('/capture/<student_id>')
def capture_images(student_id):
    """Renders the page to capture images for a student."""
    return render_template('capture.html', student_id=student_id)

def generate_frames(student_id):
    """A generator function to capture frames from webcam and save them."""
    student_dir = os.path.join(DATASET_PATH, student_id)
    cap = cv2.VideoCapture(0)
    count = 0
    
    while count < NUM_IMAGES_TO_CAPTURE:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Save the frame as an image file
            if count % 2 == 0: # Save every other frame to get some variation
                 cv2.imwrite(os.path.join(student_dir, f"{count}.jpg"), frame)

            count += 1
            
            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # Yield the frame in the format required for streaming
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    cap.release()

@app.route('/video_feed/<student_id>')
def video_feed(student_id):
    """Video streaming route that captures and saves images."""
    return Response(generate_frames(student_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')