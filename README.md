# HLS VOD Demo

A lightweight video-on-demand demo built with FastAPI and FFmpeg. Users can upload a video, package it into HLS segments, and play the generated stream in the browser through a simple HTML player.

## Overview

This project demonstrates a minimal VOD workflow:

- Upload a video file
- Save it to the local upload directory
- Trigger FFmpeg packaging into HLS format
- Generate a playlist and segment files
- Monitor the packaging status
- Play the packaged stream by asset ID

It is intended as a learning project and a starting point for a larger streaming backend.

---

## Features

- Upload MP4, MKV, and QuickTime videos
- Convert media into HLS using FFmpeg
- Generate `.m3u8` playlists and `.ts` segment files
- Serve the packaged output via FastAPI static mounts
- Track progress and failures through `status.json`
- Replay existing packaged assets without re-uploading
- Simple browser UI for uploading and playback
- Local debug configuration for VS Code
- Docker-ready setup for container deployment

---

## Tech Stack

- Python 3.11
- FastAPI
- Uvicorn
- FFmpeg
- HTML + JavaScript player
- Docker

---

## Project Structure

```text
hls_vod_project/
├── app/
│   ├── main.py
│   ├── packager.py
│   └── static/
│       └── player.html
├── data/
│   ├── uploads/
│   └── hls/
├── .vscode/
│   └── launch.json
├── .dockerignore
├── .gitignore
├── Dockerfile
├── LLD.md
├── README.md
├── requirements.txt
├── myenv/
└── ...
```

---

## Prerequisites

Before running the project, make sure the following are installed:

- Python 3.11+
- FFmpeg on your system
- A virtual environment for the project

Please ensure `ffmpeg.exe` is available in your PATH or set the `FFMPEG_PATH` environment variable.

Example on Windows:

```powershell
$env:FFMPEG_PATH = "C:\path\to\ffmpeg.exe"
```

---

## Installation

Clone the repository and set up a virtual environment:

```bash
git clone <repo-url>
cd hls_vod_project
python -m venv myenv
```

Activate the environment:

### Windows PowerShell

```powershell
.\myenv\Scripts\Activate.ps1
```

### Windows Command Prompt

```cmd
myenv\Scripts\activate.bat
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run the Project

Start the FastAPI app:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

This redirects to the static player UI at:

```text
http://127.0.0.1:8000/static/player.html
```

---

## VS Code Debugging

A debug configuration is included in `.vscode/launch.json` for working with the app in VS Code.

Use the configuration named:

```text
Debug HLS VOD API
```

---

## API Endpoints

### Upload video

```http
POST /upload
```

Uploads a multipart video file and returns a generated `asset_id`.

### Package video into HLS

```http
POST /package/{asset_id}
```

Finds the uploaded file and schedules FFmpeg packaging for HLS conversion.

### Get player URL

```http
GET /player/{asset_id}
```

Returns the player page URL for a packaged asset.

---

## Generated Output

Uploaded original files are stored in:

```text
data/uploads/
```

Generated HLS assets are stored in:

```text
data/hls/{asset_id}/
```

Each packaged asset contains:

- `index.m3u8`
- `segment_*.ts`
- `status.json`

`status.json` can be one of:

- `running`
- `done`
- `failed`

---

## Docker

A Dockerfile is included for containerized deployment.

Build the image:

```bash
docker build -t hls-vod-demo .
```

Run the container:

```bash
docker run -p 8000:8000 -v ${PWD}/data:/app/data hls-vod-demo
```

---

## Notes

- This project is designed for local demos and learning purposes.
- It is not a full production CDN or streaming platform.
- Playback success depends on the browser and codec support for the generated HLS stream.
- Generated media files in `data/` should not be committed to Git.

---

## License

This project is intended for educational and demo use.

