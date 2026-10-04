# Low-Level Design: HLS VOD Project

## 1. Purpose

This service accepts video uploads, packages an uploaded asset into an HLS playlist and segments using FFmpeg, and exposes generated files through FastAPI static-file serving. A small HTML player page uses hls.js (loaded from a CDN) when native browser HLS playback is unavailable.

This document describes the current implementation in `app/main.py`, `app/packager.py`, and `app/player.html`. It is not a specification for unimplemented behavior.

## 2. Components

- **FastAPI application (`app/main.py`)**: Creates storage directories, mounts the HLS output directory, validates upload content types, stores uploads, schedules packaging, and returns a player URL.
- **Packager (`app/packager.py`)**: Invokes the external `ffmpeg` executable, updates packaging status, and logs packaging outcomes.
- **Player (`app/player.html`)**: Reads a playlist URL from the `src` query parameter and plays it using hls.js or native HLS support.
- **Filesystem storage**: Stores original uploads and generated HLS output under the process working directory's `data` folder.
- **External FFmpeg process**: Encodes video/audio and writes the HLS playlist and MPEG-TS segments.

```mermaid
flowchart LR
    Client -->|POST /upload| API[FastAPI]
    API --> Uploads[(data/uploads)]
    Client -->|POST /package/{asset_id}| API
    API -->|in-process background task| Packager
    Packager -->|invoke| FFmpeg[ffmpeg executable]
    FFmpeg --> HLS[(data/hls/{asset_id})]
    Client -->|GET /hls/...| Static[HLS StaticFiles]
    Static --> HLS
    Client -->|open player page| Player[app/player.html]
    Player -->|fetch playlist| Static
```

## 3. Runtime and Configuration

- `BASE_DIR` is `Path.cwd() / "data"`; therefore storage location depends on the directory from which the application is launched.
- `UPLOAD_DIR` is `data/uploads`; `HLS_DIR` is `data/hls`.
- Both directories are created during module import. An `OSError` is logged and re-raised, preventing the app module from loading if storage setup fails.
- The application uses Python's standard `logging` module and relies on the server process (normally Uvicorn) to configure console handlers.
- Packaging requires `ffmpeg` to be installed and discoverable on `PATH`.
- Upload form handling requires `python-multipart`; no dependency manifest is currently present in the repository.
- `app/player.html` loads hls.js from jsDelivr at runtime, so that playback path requires client network access to the CDN.

## 4. Storage Model

For an accepted upload, a 32-character hexadecimal UUID is generated as the asset ID. The input file is stored as:

```text
data/uploads/{asset_id}_{original_filename}
```

Packaged output is written under:

```text
data/hls/{asset_id}/
  status.json
  index.m3u8
  segment_00000.ts
  segment_00001.ts
  ...
```

The exact number of segments depends on the input duration and the FFmpeg packaging result. `status.json` contains one of these current states:

- `running`: written before FFmpeg is invoked.
- `done`: written after FFmpeg exits successfully.
- `failed`: written when FFmpeg exits unsuccessfully or an exception occurs. An error string may be included, limited to the final 4000 characters for FFmpeg stderr/stdout failures.

There is no database, durable job queue, cleanup policy, or asset metadata registry. The package endpoint discovers input files by globbing for the asset ID prefix.

## 5. API Design

### `POST /upload`

**Request:** Multipart form with one field named `file`.

**Accepted declared content types:** `video/mp4`, `video/x-matroska`, and `video/quicktime`.

**Behavior:** Reads the upload in 1 MiB chunks and writes it to `UPLOAD_DIR`. On success, returns:

```json
{"asset_id": "<uuid-hex>", "filename": "<asset_id>_<original_filename>"}
```

**Errors:** Returns HTTP 400 for a disallowed content type. On a file read/write exception, logs the traceback, attempts to remove a partial file, and returns HTTP 500 with a generic message. The content-type check trusts the request header and does not inspect the file bytes.

### `POST /package/{asset_id}`

**Behavior:** Finds the first upload whose filename starts with `{asset_id}_`, creates `HLS_DIR/{asset_id}`, and schedules `package_file` using FastAPI `BackgroundTasks`. Returns immediately with:

```json
{"asset_id": "<asset_id>", "status": "packaging_started"}
```

This response means the task was queued for execution in the current application process; it does not mean packaging completed.

**Errors:** Returns HTTP 404 if no matching input file is found. Filesystem lookup or output-directory/task scheduling errors are logged and mapped to HTTP 500.

### `GET /player/{asset_id}`

Returns a JSON object containing a suggested player URL:

```json
{"player_url": "/static/player.html?src=/hls/{asset_id}/index.m3u8"}
```

The handler does not issue a redirect. The current application mounts only `/hls`; it does not mount `/static` or serve `app/player.html`, so the returned player URL is not currently served by this application without additional static-file configuration.

### `GET /hls/{path}`

FastAPI `StaticFiles` serves files beneath `HLS_DIR`. This makes the playlist and segments available at `/hls/{asset_id}/index.m3u8` and `/hls/{asset_id}/segment_....ts`. The mount also exposes other files present under the HLS directory, including `status.json`.

## 6. Packaging Details

`package_file(input_path, out_dir, hls_time=4)` performs these operations:

1. Writes `{"status": "running"}` to `status.json`.
2. Runs FFmpeg with an argument list (no shell), overwriting existing output, encoding video as H.264 (`libx264`) and audio as AAC, and using MPEG-TS HLS segments.
3. Uses a default segment duration of four seconds and an unlimited playlist (`-hls_list_size 0`).
4. Captures FFmpeg stdout/stderr. On a nonzero exit, writes a bounded error to `status.json` and logs a bounded diagnostic. On success, writes `{"status": "done"}`.
5. On an exception, logs the traceback and attempts to write a failed status. If writing that status also fails, logs that failure as well.

The background task runs in the API process. It is not durable across process termination and has no retry mechanism. There is currently no API endpoint that reports job status; clients can retrieve the static `status.json` file directly.

## 7. Logging and Error Handling

- API and packager modules use module-level loggers; logging output depends on the server's logging configuration.
- Startup directory creation, unsupported uploads, upload success/failure, package lookup/queueing, and packaging outcomes are logged.
- Expected client errors remain HTTP errors (unsupported type: 400; missing upload: 404). Operational failures return generic HTTP 500 responses while detailed information is kept in server logs.
- Upload failure handling attempts to remove partial files. Failure of that cleanup is separately logged.
- Packaging failure is recorded in `status.json`; exceptions are logged with tracebacks.
- The service does not wrap every function in `try/except`; handling is concentrated around filesystem and subprocess boundaries so programming errors are not silently hidden.

## 8. Security and Operational Constraints

- The service has no authentication or authorization. Upload and HLS routes are publicly accessible wherever the server is reachable.
- The upload MIME type is client-supplied and is not a reliable file-format validation mechanism.
- The original upload filename is included in the destination filename without normalization. Input filenames and `asset_id` values should be validated and normalized before exposing this service beyond a trusted development environment.
- HLS static serving exposes all files below `data/hls`, including status metadata and error details.
- Uploaded and generated media consume local disk indefinitely; there are no quotas, expiration, or cleanup jobs.
- In-process background tasks are suitable only for small/single-process use. Process restart loses queued work; multiple workers do not share job state beyond their shared filesystem.
- No request-size limit, upload timeout, packaging concurrency limit, or FFmpeg resource limit is configured in this code.

## 9. Current Gaps

- Add and maintain a dependency manifest, including FastAPI, an ASGI server, and `python-multipart`.
- Mount/serve `app/player.html` or change `/player/{asset_id}` to return a working redirect.
- Validate asset IDs and sanitize client-provided filenames; validate actual media content where required.
- Add a dedicated job-status endpoint and define stable status/error response schemas.
- For production workloads, move packaging to a durable worker/queue and add storage lifecycle, access control, limits, and monitoring.
