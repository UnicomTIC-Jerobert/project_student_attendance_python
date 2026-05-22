from flask import Flask, render_template, request, Response, redirect, url_for, jsonify
import cv2
import os
import sqlite3
from datetime import datetime
import time

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
# --- New API Endpoint for listing students ---
@app.route('/api/students')
def get_students():
    """Returns a list of registered students as JSON."""
    try:
        students = [s for s in os.listdir(DATASET_PATH) if os.path.isdir(os.path.join(DATASET_PATH, s))]
        return jsonify({"status": "success", "students": students})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Modify the root route to show the dashboard ---
@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('dashboard.html')

@app.route('/logs')
def view_logs():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, timestamp, event_type, camera_id FROM attendance ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)

@app.route('/register', methods=['POST'])
def register():
    student_id = request.form['student_id']
    if not student_id:
        return "Error: Student ID is required.", 400
    
    student_dir = os.path.join(DATASET_PATH, student_id)
    os.makedirs(student_dir, exist_ok=True)
    
    # Redirect to the capture page
    return redirect(url_for('capture_images', student_id=student_id))

@app.route('/capture/<student_id>')
def capture_images(student_id):
    """Renders the page to capture images for a student."""
    return render_template('capture.html', student_id=student_id)

def generate_frames(student_id):
    """A generator function to capture frames from webcam with a countdown."""
    student_dir = os.path.join(DATASET_PATH, student_id)
    cap = cv2.VideoCapture(0)
    
    # --- PHASE 1: WARM UP & COUNTDOWN ---
    countdown_seconds = 5 # Change to 30 here if you really want a 30 sec wait!
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > countdown_seconds:
            break # Countdown finished, exit this loop
            
        success, frame = cap.read()
        if not success:
            break
            
        remaining = int(countdown_seconds - elapsed) + 1
        
        # Draw the countdown timer on the video frame
        cv2.putText(frame, f"Get Ready! Starting in: {remaining}s", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


    # --- PHASE 2: CAPTURE IMAGES ---
    count = 0
    while count < NUM_IMAGES_TO_CAPTURE:
        success, frame = cap.read()
        if not success:
            break
        
        # Save every frame
        cv2.imwrite(os.path.join(student_dir, f"{count}.jpg"), frame)
        count += 1
        
        # Draw the progress on the video frame
        cv2.putText(frame, f"Capturing: {count}/{NUM_IMAGES_TO_CAPTURE} - Move your head!", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # Add a small delay so the 30 images are spaced out over ~3-4 seconds
        time.sleep(0.1) 


    # --- PHASE 3: FINISHED ---
    success, frame = cap.read()
    if success:
        cv2.putText(frame, "Done! Capture Complete.", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()


@app.route('/video_feed/<student_id>')
def video_feed(student_id):
    """Video streaming route that captures and saves images."""
    return Response(generate_frames(student_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Add this new route to app.py ---
@app.route('/api/check_status/<student_id>')
def check_status(student_id):
    """Checks if the registration images have finished saving."""
    student_dir = os.path.join(DATASET_PATH, student_id)
    
    # We check for the last image (index is NUM_IMAGES_TO_CAPTURE - 1, so 29.jpg)
    last_image_path = os.path.join(student_dir, f"{NUM_IMAGES_TO_CAPTURE - 1}.jpg")
    
    if os.path.exists(last_image_path):
        return jsonify({"status": "complete"})
    else:
        return jsonify({"status": "capturing"})