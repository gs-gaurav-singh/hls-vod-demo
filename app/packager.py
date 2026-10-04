import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def package_file(input_path: str, out_dir: str, hls_time: int = 4):
    out_dir_p = Path(out_dir)
    status_file = out_dir_p / "status.json"
    asset_id = out_dir_p.name
    logger.info("Packaging started for asset_id=%s", asset_id)

    try:
        status_file.write_text(json.dumps({"status": "running"}), encoding="utf-8")
        seg_pattern = str(out_dir_p / "segment_%05d.ts")
        playlist = str(out_dir_p / "index.m3u8")
        ffmpeg_executable = os.environ.get("FFMPEG_PATH", "ffmpeg")
        cmd = [
            ffmpeg_executable, "-y", "-i", input_path,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-profile:v", "baseline",
            "-level", "3.0", "-pix_fmt", "yuv420p", "-start_number", "0",
            "-hls_time", str(hls_time), "-hls_list_size", "0",
            "-hls_segment_filename", seg_pattern, playlist,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            error = (proc.stderr or proc.stdout or "FFmpeg exited with an error").strip()
            error_excerpt = error[-4000:]
            status_file.write_text(
                json.dumps({"status": "failed", "error": error_excerpt}),
                encoding="utf-8",
            )
            logger.error(
                "Packaging failed for asset_id=%s returncode=%d: %s",
                asset_id,
                proc.returncode,
                error[-2000:],
            )
        else:
            status_file.write_text(json.dumps({"status": "done"}), encoding="utf-8")
            logger.info("Packaging completed for asset_id=%s", asset_id)
    except Exception as exc:
        logger.exception("Packaging failed unexpectedly for asset_id=%s", asset_id)
        try:
            status_file.write_text(
                json.dumps({"status": "failed", "error": str(exc)}),
                encoding="utf-8",
            )
        except OSError:
            logger.exception("Could not update packaging status for asset_id=%s", asset_id)
