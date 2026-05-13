from flask import Flask, render_template, request, Response, redirect, url_for
import cv2
import os

app = Flask(__name__)

# --- Configuration ---
DATASET_PATH = 'dataset'
NUM_IMAGES_TO_CAPTURE = 30 # Number of images to capture per student

# Ensure the dataset directory exists
os.makedirs(DATASET_PATH, exist_ok=True)

@app.route('/')
def index():
    """Renders the main page with a list of registered students."""
    students = [s for s in os.listdir(DATASET_PATH) if os.path.isdir(os.path.join(DATASET_PATH, s))]
    return render_template('index.html', students=students)

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