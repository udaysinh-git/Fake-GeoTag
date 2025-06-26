from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .utils import embed_metadata
from .config import get_settings

class Runner:
    """Main application runner for the backend API."""
    def __init__(self, config: dict):
        self.config = config
        self.app = FastAPI(title="Fake GeoTag API")
        self.setup_routes()
        self.app.mount("/web", StaticFiles(directory="web"), name="web")

    def setup_routes(self):
        from fastapi import UploadFile, File, Form
        from fastapi.responses import FileResponse, JSONResponse
        import os, uuid

        @self.app.post("/api/fake-metadata")
        async def fake_metadata(
            file: UploadFile = File(...),
            latitude: float = Form(...),
            longitude: float = Form(...),
            date: str = Form(...),
            time: str = Form(...),
            map_image: UploadFile = File(None),
        ):
            """Endpoint to receive image and metadata, embed EXIF, and return new image. Accepts optional map screenshot."""
            import os
            import uuid
            gen_dir = os.path.join(os.path.dirname(__file__), '..', 'generated')
            os.makedirs(gen_dir, exist_ok=True)
            temp_input = os.path.join(gen_dir, f"temp_{uuid.uuid4().hex}_{file.filename}")
            temp_output = os.path.join(gen_dir, f"output_{uuid.uuid4().hex}_{file.filename}")
            temp_map = None
            with open(temp_input, "wb") as f:
                f.write(await file.read())
            map_img_bytes = None
            if map_image is not None:
                temp_map = os.path.join(gen_dir, f"temp_{uuid.uuid4().hex}_map.png")
                with open(temp_map, "wb") as mf:
                    mf.write(await map_image.read())
                map_img_bytes = temp_map
            try:
                embed_metadata(temp_input, temp_output, latitude, longitude, date, time, map_img_bytes)
                return FileResponse(temp_output, filename=file.filename)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
            finally:
                for f in [temp_input, temp_output, temp_map]:
                    if f and os.path.exists(f):
                        try:
                            os.remove(f)
                        except Exception:
                            pass

    def start(self):
        import uvicorn
        uvicorn.run(self.app, host=self.config.get("host", "127.0.0.1"), port=self.config.get("port", 8000))
