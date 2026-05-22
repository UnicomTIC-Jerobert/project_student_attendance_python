### Answer 1: Why does the training take so much time?

The reason your `train_model.py` is taking a very long time is because of this specific line in the code:
`face_locations = face_recognition.face_locations(image, model="cnn")`

The `"cnn"` (Convolutional Neural Network) model is highly accurate, but it is **computationally massive**. Unless you have a powerful NVIDIA Graphics Card (GPU) configured with specific software (`CUDA` and a compiled version of `dlib`), Python is forcing your CPU to do all the heavy lifting. On a standard CPU, processing a single image with `"cnn"` can take several seconds to a minute! Since you are capturing 30 images per student, this adds up quickly.

**The Fix:**
Open your `train_model.py` file, find that line, and change `"cnn"` to `"hog"` (Histogram of Oriented Gradients). 

```python
# Change this:
# face_locations = face_recognition.face_locations(image, model="cnn")

# To this:
face_locations = face_recognition.face_locations(image, model="hog")
```
The `"hog"` model is heavily optimized for CPUs and will process your images **significantly faster** (usually in just a few seconds total) while still being plenty accurate for a Proof of Concept!

---

### Answer 2: Merging Step 5 and Step 6 into a single file

You are absolutely right to ask for this. Step 5 introduced the **API calls, Camera ID, and Debouncing** (preventing spam logs), while Step 6 introduced the **Tracker and Entry/Exit line**. 

To merge them, we will apply the debouncing logic and network error handling from Step 5 to the line-crossing events from Step 6. 

*Note: Because Step 6 uses advanced math to track movement, you must install one more library if you haven't already. Run this in your terminal:*
```bash
pip install scipy
```

Here is your fully merged, unified **`recognition_service.py`**:

```python
import cv2
import face_recognition
import pickle
import numpy as np
import requests
import time
from collections import OrderedDict
from scipy.spatial import distance as dist

# ==========================================
# CENTROID TRACKER CLASS (From Step 6)
# ==========================================
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
                if row in usedRows or col in usedCols: continue
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


# ==========================================
# CONFIGURATION & SETUP (Merged Step 5 & 6)
# ==========================================
ENCODINGS_FILE = 'known_face_encodings.pkl'
CAMERA_INDEX = 0 
CAMERA_ID = "DOOR_CAM_01" 
API_ENDPOINT = "http://127.0.0.1:5000/api/log_attendance"
DEBOUNCE_TIME = 10 # Wait 10 seconds before logging the same person crossing again

# State Management for Debouncing (From Step 5)
last_seen = {} 

# Initialize Tracker (From Step 6)
ct = CentroidTracker()
trackableObjects = {}

# Load Encodings
print("[INFO] Loading known face encodings...")
try:
    with open(ENCODINGS_FILE, 'rb') as f:
        data = pickle.load(f)
    known_face_encodings = data['encodings']
    known_face_names = data['names']
except FileNotFoundError:
    print("[ERROR] Encodings file not found. Please run train_model.py first.")
    exit()

print("[INFO] Starting video stream...")
cap = cv2.VideoCapture(CAMERA_INDEX)
time.sleep(2.0)

# ==========================================
# MAIN VIDEO LOOP
# ==========================================
while True:
    ret, frame = cap.read()
    if not ret: 
        print("[ERROR] Failed to grab frame.")
        break
    
    H, W, _ = frame.shape
    LINE_Y = H // 2 # The virtual entry/exit line in the middle of the screen

    # Convert format and detect faces
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    # Format for the tracker
    rects = [(left, top, right, bottom) for (top, right, bottom, left) in face_locations]
    objects = ct.update(rects)
    current_time = time.time()

    for (objectID, centroid) in objects.items():
        to = trackableObjects.get(objectID, None)
        
        # If new object, create a dictionary for it
        if to is None:
            to = {"objectID": objectID, "centroids": [centroid], "identified": False, "name": "Unknown"}
        else:
            # We have seen this object, append the new centroid
            to["centroids"].append(centroid)

            # --- 1. IDENTIFICATION LOGIC ---
            if not to["identified"]:
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

            # --- 2. ENTRY/EXIT & API DEBOUNCE LOGIC (Merged) ---
            # Check if they crossed the line top-to-bottom (Entry) or bottom-to-top (Exit)
            event_type = None
            if len(to["centroids"]) > 1:
                previous_y = to["centroids"][-2][1]
                current_y = centroid[1]
                
                if previous_y < LINE_Y and current_y >= LINE_Y:
                    event_type = "entry"
                elif previous_y > LINE_Y and current_y <= LINE_Y:
                    event_type = "exit"

            # If an event happened and we know who it is
            if event_type and to["name"] != "Unknown":
                name = to["name"]
                
                # Check Debounce: Have we logged them recently?
                if name not in last_seen or (current_time - last_seen[name]) > DEBOUNCE_TIME:
                    print(f"[EVENT] {name} is {event_type.upper()}ING")
                    
                    payload = {
                        "student_id": name,
                        "camera_id": CAMERA_ID,
                        "event_type": event_type
                    }
                    
                    # Send to Flask API safely
                    try:
                        response = requests.post(API_ENDPOINT, json=payload)
                        if response.status_code == 200:
                            print(f"[SUCCESS] Logged {event_type} for {name}")
                            last_seen[name] = current_time # Update debounce timer
                        else:
                            print(f"[ERROR] API Status {response.status_code}")
                    except requests.exceptions.ConnectionError:
                        print("[ERROR] Could not connect to Flask API. Is app.py running?")

        # Store the object data back in the dictionary
        trackableObjects[objectID] = to
        
        # Draw on the screen
        text = f"ID {objectID} ({to['name']})"
        cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)

    # Draw the virtual entry/exit line
    cv2.line(frame, (0, LINE_Y), (W, LINE_Y), (0, 255, 255), 2)
    cv2.imshow("Live Attendance Scanner", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### What this Merged File does:
1. It uses `hog` for fast face recognition.
2. It tracks moving faces to see if they cross the yellow line in the middle of the screen (Step 6).
3. If they cross the line, it checks if they have already been logged in the last 10 seconds (`DEBOUNCE_TIME`) (Step 5).
4. If they haven't been logged recently, it securely sends an API request to your Flask app containing their ID, whether it was an `entry` or `exit`, and the `CAMERA_ID` (Step 5).
5. If your Flask app is turned off, the script uses a `try/except` block so it will gently warn you instead of crashing the whole camera feed.
