import cv2
import face_recognition
import pickle
import numpy as np

# --- Configuration ---
ENCODINGS_FILE = 'known_face_encodings.pkl'
# For testing, we use the built-in webcam. Change to your RTSP URL for your camera.
# CAMERA_URL = "rtsp://user:pass@ip_address:port/stream_path"
CAMERA_INDEX = 0  # 0 for the default webcam

# --- Load Encodings ---
print("[INFO] Loading known face encodings...")
with open(ENCODINGS_FILE, 'rb') as f:
    data = pickle.load(f)
known_face_encodings = data['encodings']
known_face_names = data['names']

# --- Initialize Video ---
print("[INFO] Starting video stream...")
cap = cv2.VideoCapture(CAMERA_INDEX) # Or cv2.VideoCapture(CAMERA_URL)

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to grab frame.")
        break

    # Convert the frame from BGR to RGB for face_recognition
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect faces in the frame
    face_locations = face_recognition.face_locations(rgb_frame, model="hog") # "hog" is faster for real-time
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    # Loop through each face found in the frame
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
        name = "Unknown"

        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
        
        # --- LOG ATTENDANCE HERE ---
        # This is where you would send the data (e.g., name, timestamp)
        # to your database or API endpoint. For now, we just print it.
        if name != "Unknown":
            print(f"Attendance Logged: {name}")

        # Draw a box around the face and display the name
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Live Attendance', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
cap.release()
cv2.destroyAllWindows()