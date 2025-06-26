# Fake GeoTag

Fake GeoTag is a beginner-friendly web app that lets you upload a photo, select a date, time, and location, and then embed this metadata (EXIF) into the image. It uses OpenStreetMap for location selection and a Python FastAPI backend for processing. This project is for educational purposes only.

---

## Features

- Upload a photo
- Select date, time, and location (via map or coordinates)
- Embed metadata (EXIF) into the image
- Download the modified image

---

## Getting Started (Beginner Friendly)

### 1. Install [uv](https://github.com/astral-sh/uv) (if you don't have it)

**uv** is a fast Python package manager. If you don't have it, open your terminal/command prompt and run:

**On Windows:**

```sh
pip install uv
```

**On Mac/Linux:**

```sh
pip3 install uv
```

If you get a 'pip not found' error, [install Python first](https://www.python.org/downloads/).

### 2. Set up your environment and install dependencies

```sh
uv venv
uv pip install -r requirements.txt
```

### 3. Run the backend server

```sh
python main.py
```

### 4. Open the web app

Open your browser and go to: [http://localhost:8000/web/index.html](http://localhost:8000/web/index.html)

---

## Frequently Asked Questions (FAQ)

**Q: What is uv and why do I need it?**  
A: uv is a fast tool for managing Python packages and virtual environments. It makes setup easier and faster, especially for beginners.

**Q: I get an error about 'uv' not found!**  
A: Make sure you installed uv using `pip install uv` (or `pip3 install uv` on Mac/Linux). If you still have issues, try restarting your terminal or check your Python installation.

**Q: How do I select a location?**  
A: Click on the map to set the marker, or use the 'Use My Location' button if your browser supports it.

**Q: Where is my modified image saved?**  
A: After processing, a download link will appear. Click it to save the new image to your computer.

**Q: Is this safe to use for real photos?**  
A: This project is for educational purposes only. Do not use it for sensitive or private images.

**Q: I want to learn more about EXIF metadata. Where can I start?**  
A: Check out [Wikipedia's EXIF article](https://en.wikipedia.org/wiki/Exif) or the [piexif documentation](https://piexif.readthedocs.io/en/latest/).

---

## Disclaimer

This project is for educational purposes only. Do not use it for illegal or unethical activities. The authors are not responsible for any misuse.
