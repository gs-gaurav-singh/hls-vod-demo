import logging
import uuid
from pathlib import Path
from fastapi.responses import RedirectResponse

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from .packager import package_file

logger = logging.getLogger(__name__)

app = FastAPI()
BASE_DIR = Path.cwd() / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
HLS_DIR = BASE_DIR / "hls"

try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    HLS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    logger.exception("Could not create application data directories under %s", BASE_DIR)
    raise

logger.info("Application data directories are ready under %s", BASE_DIR)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.mount("/hls", StaticFiles(directory=str(HLS_DIR)), name="hls")

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/static/player.html")

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if file.content_type not in ("video/mp4", "video/x-matroska", "video/quicktime"):
        logger.warning("Rejected upload with unsupported content type %r", file.content_type)
        raise HTTPException(status_code=400, detail="Unsupported file type")
    asset_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{asset_id}_{file.filename}"
    bytes_written = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                bytes_written += len(chunk)
    except Exception as exc:
        logger.exception("Failed to save uploaded file for asset_id=%s", asset_id)
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove partial upload for asset_id=%s", asset_id)
        raise HTTPException(status_code=500, detail="Unable to save uploaded file") from exc

    logger.info("Upload saved for asset_id=%s bytes=%d", asset_id, bytes_written)
    return {"asset_id": asset_id, "filename": dest.name}

@app.post("/package/{asset_id}")
def package(asset_id: str, background_tasks: BackgroundTasks):
    # Find uploaded file for asset_id (simple lookup by prefix)
    try:
        matches = list(UPLOAD_DIR.glob(f"{asset_id}_*"))
    except OSError as exc:
        logger.exception("Could not locate uploaded file for asset_id=%s", asset_id)
        raise HTTPException(status_code=500, detail="Unable to locate uploaded file") from exc
    if not matches:
        logger.warning("No uploaded file found for asset_id=%s", asset_id)
        raise HTTPException(status_code=404, detail="Uploaded file not found")
    input_path = matches[0]
    out_dir = HLS_DIR / asset_id
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        background_tasks.add_task(package_file, str(input_path), str(out_dir))
    except Exception as exc:
        logger.exception("Could not queue packaging for asset_id=%s", asset_id)
        raise HTTPException(status_code=500, detail="Unable to start packaging") from exc

    logger.info("Packaging queued for asset_id=%s", asset_id)
    return {"asset_id": asset_id, "status": "packaging_started"}

@app.get("/player/{asset_id}")
def player(asset_id: str):
    # Minimal redirect to static player or render template
    return {"player_url": f"/static/player.html?src=/hls/{asset_id}/index.m3u8"}
