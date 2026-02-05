# Video Editor

A web-based video editing system designed around explicit editing intent,
client-side execution, and minimal backend responsibilities.

This project allows users to define reusable video editing plans and apply them
without requiring server-side video processing.

---

## Overview

The system is composed of:

- A FastAPI backend responsible for validation and persistence
- A browser-based frontend that executes video processing
- FFmpeg running via WebAssembly on the client
- MariaDB used to store structured metadata and editing intent

Raw video processing is intentionally kept out of the backend to reduce
infrastructure load and limit the server attack surface.

---

## Architecture

The project follows a strict separation of responsibilities between components.
Detailed explanations are provided in the documentation:

- **Architecture Overview**  
  Explains the overall system structure and responsibility boundaries

- **Video Editing Pipeline**  
  Describes how user input is transformed into deterministic video processing

- **API Design & Data Model**  
  Covers core API resources and how editing intent is represented in the database

See the `docs/` directory for these documents.

---

## Project Structure

```text
video-editor/
    ├── app
    │   ├── api
    │   │   ├── plan.py
    │   │   └── video.py
    │   ├── core
    │   │   ├── db.py
    │   │   └── models.py
    │   ├── main.py
    │   └── web
    │       ├── router.py
    │       ├── src
    │       │   └── api
    │       │       ├── client.ts
    │       │       └── schema.ts
    │       └── static
    │           ├── css
    │           │   ├── app.css
    │           │   └── vedit.css
    │           ├── ffmpeg
    │           │   ├── classes.js
    │           │   ├── const.js
    │           │   ├── errors.js
    │           │   ├── ffmpeg-core.js
    │           │   ├── ffmpeg-core.wasm
    │           │   ├── index.js
    │           │   ├── utils.js
    │           │   └── worker.js
    │           ├── js
    │           │   ├── app
    │           │   │   ├── api.js
    │           │   │   ├── app.js
    │           │   │   ├── ffmpeg.js
    │           │   │   ├── meta.js
    │           │   │   └── recipe.js
    │           │   └── t-min.js
    │           └── vendor
    │               └── ffmpeg
    │                   └── esm
    │                       ├── index.js
    │                       └── worker.js
    ├── data
    │   └── config
    │       ├── _conf_.example.py
    │       └── env
    │           └── video-editor
    │               └── .env.shared.example
    ├── docs
    │   ├── API_Design_and_Data_Model.md
    │   ├── Architecture_Overview.md
    │   └── Video_Editing_Pipeline.md
    ├── LICENSE
    ├── README.md
    ├── requirements.txt
    └── tools
        └── openapi-types.sh
```
