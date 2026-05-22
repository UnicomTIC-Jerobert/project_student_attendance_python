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

