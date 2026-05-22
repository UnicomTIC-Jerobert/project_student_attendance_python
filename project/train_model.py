import face_recognition
import os
import pickle

# --- Configuration ---
DATASET_PATH = 'dataset'
ENCODINGS_FILE = 'known_face_encodings.pkl'

def train_model():
    """
    Processes all student images in the dataset folder, computes their
    face encodings, and saves them to a file.
    """
    known_encodings = []
    known_names = []

    print("[INFO] Starting to process images...")
    
    # Loop over each person in the dataset
    for student_id in os.listdir(DATASET_PATH):
        student_dir = os.path.join(DATASET_PATH, student_id)
        if not os.path.isdir(student_dir):
            continue

        print(f"[INFO] Processing images for {student_id}...")
        
        # Loop over each image for the current person
        for filename in os.listdir(student_dir):
            image_path = os.path.join(student_dir, filename)
            
            try:
                # Load the image and convert it from BGR (OpenCV) to RGB (face_recognition)
                image = face_recognition.load_image_file(image_path)
                
                # Detect the face box. We assume one face per image for training.
                face_locations = face_recognition.face_locations(image, model="hog") # Use "cnn" for more accuracy
                
                if len(face_locations) == 1:
                    # Get the encoding
                    encoding = face_recognition.face_encodings(image, face_locations)[0]
                    known_encodings.append(encoding)
                    known_names.append(student_id)
                else:
                    print(f"[WARNING] Image {filename} in {student_id} has 0 or >1 faces. Skipping.")

            except Exception as e:
                print(f"[ERROR] Could not process {image_path}: {e}")

    # Save the encodings and names to a file
    print("[INFO] Saving encodings to disk...")
    data = {"encodings": known_encodings, "names": known_names}
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)
        
    print("[INFO] Training complete.")

if __name__ == "__main__":
    train_model()