# HLS VOD Demo

A lightweight HLS video-on-demand demo built with FastAPI and FFmpeg. The application allows users to upload a video, package it into HLS segments, and stream it in the browser using generated MPEG-TS segments and `.m3u8` playlists.

## Overview

This project demonstrates a simple VOD workflow:

- Upload a source video
- Package it into HLS format using FFmpeg
- Save the generated playlist and segments
- Serve the stream through a browser-based player
- Track status while the video is being converted

It is intended as a learning project and a starting point for building a more complete streaming backend.

---

## Features

- Upload video files in common formats such as MP4, MKV, and QuickTime
- Convert uploaded videos into HLS with FFmpeg
- Generate segmented files like `segment_00000.ts`
- Serve playlists from the local `data/hls` directory
- Track conversion progress through `status.json`
- Play previously packaged assets by asset ID
- Run locally with FastAPI and Uvicorn
- Container-ready with Docker

---

## Tech Stack

- Python 3.11
- FastAPI
- Uvicorn
- FFmpeg
- HTML/JavaScript static player
- Docker support

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
├── Dockerfile
├── LLD.md
├── requirements.txt
├── myenv/
└── README.md
