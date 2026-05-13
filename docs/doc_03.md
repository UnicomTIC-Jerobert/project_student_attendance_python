**USER**

lets proceed to next step as well

**RESPONSE**

Fantastic! Let's transition from the standalone PoC to a more integrated and intelligent system.

Our next steps will focus on three key areas:
1.  **Data Persistence:** Storing attendance records in a database.
2.  **System Integration:** Making the `recognition_service` communicate with the Flask web app via a REST API.
3.  **Core Logic:** Implementing the entry/exit detection at a doorway.

---

### **Step 4: Database Integration and REST API**

First, let's modify our Flask app to handle a database and expose an API endpoint for logging attendance. We'll use SQLite for simplicity, which is perfect for this stage.

**1. Update Dependencies**
The `requests` library will be needed for our recognition service to call the API.
```bash
pip install requests
```

**2. Modify `app.py`**
We'll add code to set up a simple SQLite database and create two new routes: one to log attendance (`/api/log_attendance`) and one to view the logs (`/logs`).

**File: `app.py` (Updated)**
```python
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

# ... (The rest of your registration and capture routes from Step 1 remain the same) ...
# ... (register, capture_images, generate_frames, video_feed) ...

# Ensure you have the full code from the previous step here.
# I've omitted it for brevity.
```

**3. Create a New Template for Viewing Logs**

**File: `templates/logs.html`**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Attendance Logs</title>
    <style>
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Attendance Log</h1>
    <a href="/">Back to Home</a>
    <table>
        <tr>
            <th>Student ID</th>
            <th>Timestamp</th>
            <th>Event Type</th>
            <th>Camera ID</th>
        </tr>
        {% for log in logs %}
        <tr>
            <td>{{ log[0] }}</td>
            <td>{{ log[1] }}</td>
            <td>{{ log[2] }}</td>
            <td>{{ log[3] }}</td>
        </tr>
        {% else %}
        <tr>
            <td colspan="4">No logs yet.</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
```

**4. Update `templates/index.html`**
Add a link to the new logs page.

```html
<!-- Add this line in your index.html -->
<a href="/logs">View Attendance Logs</a>
```

---

### **Step 5: Connecting the Recognition Service to the API**

Now, let's modify the `recognition_service.py` to call the API endpoint instead of just printing to the console.

A crucial addition here is **debouncing**. We don't want to log a student's attendance 30 times per second. We'll add logic to only log a student's presence once every, say, 30 seconds.

**File: `recognition_service.py` (Updated)**
```python
import cv2
import face_recognition
import pickle
import numpy as np
import requests # New import
import time # New import

# --- Configuration ---
ENCODINGS_FILE = 'known_face_encodings.pkl'
CAMERA_INDEX = 0 
CAMERA_ID = "DOOR_CAM_01" # Give your camera a unique name
API_ENDPOINT = "http://127.0.0.1:5000/api/log_attendance"
DEBOUNCE_TIME = 30 # Seconds to wait before logging the same person again

# --- State Management for Debouncing ---
last_seen = {} # Dictionary to store the last time a person was seen

# --- Load Encodings ---
print("[INFO] Loading known face encodings...")
with open(ENCODINGS_FILE, 'rb') as f:
    data = pickle.load(f)
known_face_encodings = data['encodings']
known_face_names = data['names']

# --- Initialize Video ---
print("[INFO] Starting video stream...")
cap = cv2.VideoCapture(CAMERA_INDEX)

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to grab frame.")
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    current_time = time.time()

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
        name = "Unknown"

        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]

        # --- LOG ATTENDANCE WITH DEBOUNCING ---
        if name != "Unknown":
            # Check if we've seen this person recently
            if name not in last_seen or (current_time - last_seen[name]) > DEBOUNCE_TIME:
                print(f"[LOG] Logging {name} to API...")
                payload = {
                    "student_id": name,
                    "camera_id": CAMERA_ID,
                    "event_type": "presence" # For now, we use a generic event type
                }
                try:
                    response = requests.post(API_ENDPOINT, json=payload)
                    if response.status_code == 200:
                        print(f"[SUCCESS] Logged {name}")
                        last_seen[name] = current_time # Update the last seen time
                    else:
                        print(f"[ERROR] Failed to log. Status: {response.status_code}, Message: {response.text}")
                except requests.exceptions.ConnectionError as e:
                    print(f"[ERROR] Could not connect to API: {e}")

        # Draw a box around the face and display the name
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    cv2.imshow('Live Attendance', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

```

---

### **Step 6: Implementing Entry/Exit Logic**

This is a more advanced computer vision task. It requires **object tracking**. Simply detecting a face isn't enough; you need to know it's the *same face* moving across a line.

The simplest way to do this is with a **Centroid Tracker**. It calculates the center point of each face's bounding box and tracks that point from frame to frame.

We'll define a virtual line in the middle of the screen. If a person's tracked path crosses this line from top to bottom, they are "entering." If they cross from bottom to top, they are "exiting."

**1. Create a Simple Centroid Tracker**
Let's add a basic tracker to our `recognition_service.py`. This is a simplified implementation.

**File: `recognition_service.py` (Final, with Entry/Exit Logic)**
*You will replace the previous `recognition_service.py` with this more advanced version.*

```python
import cv2
import face_recognition
import pickle
import numpy as np
import requests
import time
from collections import OrderedDict
from scipy.spatial import distance as dist

# --- Centroid Tracker Class (simplified) ---
class CentroidTracker:
    def __init__(self, maxDisappeared=50):
        self.nextObjectID = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        self.maxDisappeared = maxDisappeared

    def register(self, centroid):
        self.objects[self.nextObjectID] = centroid
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        del self.objects[objectID]
        del self.disappeared[objectID]

    def update(self, rects):
        if len(rects) == 0:
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)
            return self.objects

        inputCentroids = np.zeros((len(rects), 2), dtype="int")
        for (i, (startX, startY, endX, endY)) in enumerate(rects):
            cX = int((startX + endX) / 2.0)
            cY = int((startY + endY) / 2.0)
            inputCentroids[i] = (cX, cY)

        if len(self.objects) == 0:
            for i in range(0, len(inputCentroids)):
                self.register(inputCentroids[i])
        else:
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())
            D = dist.cdist(np.array(objectCentroids), inputCentroids)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            usedRows = set()
            usedCols = set()
            for (row, col) in zip(rows, cols):
                if row in usedRows or col in usedCols:
                    continue
                objectID = objectIDs[row]
                self.objects[objectID] = inputCentroids[col]
                self.disappeared[objectID] = 0
                usedRows.add(row)
                usedCols.add(col)
            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            unusedCols = set(range(0, D.shape[1])).difference(usedCols)
            if D.shape[0] >= D.shape[1]:
                for row in unusedRows:
                    objectID = objectIDs[row]
                    self.disappeared[objectID] += 1
                    if self.disappeared[objectID] > self.maxDisappeared:
                        self.deregister(objectID)
            else:
                for col in unusedCols:
                    self.register(inputCentroids[col])
        return self.objects

# --- Configuration ---
# ... (Keep the same config as before: ENCODINGS_FILE, API_ENDPOINT, etc.)
CAMERA_INDEX = 0

# --- State Management ---
# ... (last_seen dictionary for debouncing)

# --- Initialize Tracker ---
ct = CentroidTracker()
trackableObjects = {}

# --- Load Encodings & Initialize Video ---
# ... (Same as before)
print("[INFO] Loading known face encodings...")
with open('known_face_encodings.pkl', 'rb') as f:
    data = pickle.load(f)
known_face_encodings = data['encodings']
known_face_names = data['names']

cap = cv2.VideoCapture(CAMERA_INDEX)
time.sleep(2.0)

# --- Main Loop ---
while True:
    ret, frame = cap.read()
    if not ret: break
    
    H, W, _ = frame.shape
    # Define the virtual line (center of the frame)
    LINE_Y = H // 2

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    rects = [(left, top, right, bottom) for (top, right, bottom, left) in face_locations]
    
    objects = ct.update(rects)

    for (objectID, centroid) in objects.items():
        to = trackableObjects.get(objectID, None)
        if to is None:
            to = {"objectID": objectID, "centroids": [centroid], "identified": False, "name": "Unknown"}
        else:
            y = [c[1] for c in to["centroids"]]
            direction = centroid[1] - np.mean(y)
            to["centroids"].append(centroid)

            if not to["identified"]:
                # Try to identify the person if not already identified
                # Find the closest face_encoding to this centroid
                min_dist = float('inf')
                matched_encoding = None
                for (top, right, bottom, left), enc in zip(face_locations, face_encodings):
                    face_centroid_x = (left + right) // 2
                    face_centroid_y = (top + bottom) // 2
                    d = dist.euclidean((face_centroid_x, face_centroid_y), centroid)
                    if d < min_dist and d < 50: # 50 pixel tolerance
                        min_dist = d
                        matched_encoding = enc

                if matched_encoding is not None:
                    matches = face_recognition.compare_faces(known_face_encodings, matched_encoding, tolerance=0.5)
                    face_distances = face_recognition.face_distance(known_face_encodings, matched_encoding)
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            to["name"] = known_face_names[best_match_index]
                            to["identified"] = True

            # Check for line crossing
            if len(to["centroids"]) > 1 and to["centroids"][-2][1] < LINE_Y and centroid[1] >= LINE_Y:
                if to["name"] != "Unknown":
                    print(f"EVENT: {to['name']} is ENTERING")
                    # Send API request for "entry"
                    requests.post(API_ENDPOINT, json={"student_id": to["name"], "event_type": "entry"})
            elif len(to["centroids"]) > 1 and to["centroids"][-2][1] > LINE_Y and centroid[1] <= LINE_Y:
                if to["name"] != "Unknown":
                    print(f"EVENT: {to['name']} is EXITING")
                    # Send API request for "exit"
                    requests.post(API_ENDPOINT, json={"student_id": to["name"], "event_type": "exit"})

        trackableObjects[objectID] = to
        text = f"ID {objectID} ({to['name']})"
        cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)

    # Draw the line
    cv2.line(frame, (0, LINE_Y), (W, LINE_Y), (0, 255, 255), 2)
    cv2.imshow("Live Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

### **Step 7: Upgrading to Your RTSP Cameras**

This is now a very simple change. In your `recognition_service.py` file, find the `CAMERA_INDEX` variable and replace it with the RTSP URL of your camera.

**Find your camera's RTSP URL:**
*   **Ezviz:** Usually `rtsp://<username>:<password>@<ip_address>:554/H.264` or similar. You may need to enable RTSP in the camera's settings.
*   **Imou:** Often `rtsp://<username>:<password>@<ip_address>:554/cam/realmonitor?channel=1&subtype=0`.

**Change this line:**
`cap = cv2.VideoCapture(CAMERA_INDEX)`

**To this:**
`RTSP_URL = "rtsp://admin:YourCameraPassword@192.168.1.50:554/cam/realmonitor?channel=1&subtype=0"`
`cap = cv2.VideoCapture(RTSP_URL)`

### **How to Run the Integrated System**

1.  **Start the Web App:** This now acts as your database server and API.
    ```bash
    flask run
    ```
    Keep this terminal open.

2.  **Start the Recognition Service:** Open a **new terminal**, activate the virtual environment (`venv\Scripts\activate` or `source venv/bin/activate`), and run the service.
    ```bash
    python recognition_service.py
    ```
    This script will now connect to your camera, track faces, and send entry/exit events to your Flask app.

3.  **Test It:**
    *   Walk towards the camera so you cross the virtual horizontal line. Check the terminal running the recognition service—it should print "ENTERING".
    *   Walk away from the camera, crossing the line again. It should print "EXITING".
    *   Open your browser to `http://127.0.0.1:5000/logs`. You should see the new entry and exit events logged in the table!

You now have a much more powerful system with a database, a functional API, and the core logic for door-based attendance tracking. From here, you can move on to deploying this to a more permanent server, adding the in-hall cameras, or improving the accuracy with YOLO.
