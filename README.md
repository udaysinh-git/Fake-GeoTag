# Fake GeoTag

A web app to upload a photo, select date/time/location, and embed this metadata into the image. Uses OpenStreetMap for location selection and a Python FastAPI backend for processing.

## Features

- Upload a photo
- Select date, time, and location (via map or coordinates)
- Embed metadata (EXIF) into the image
- Download the modified image

## Usage

1. Install dependencies with [uv](https://github.com/astral-sh/uv):
   ```sh
   uv venv
   uv pip install -r requirements.txt
   ```
2. Run the backend:
   ```sh
   python main.py
   ```
3. Open [http://localhost:8000/web/index.html](http://localhost:8000/web/index.html) in your browser.
