# Video Editing Pipeline

## Overview

The video editing process is designed as a deterministic pipeline that transforms
user intent into executable video operations while clearly separating responsibilities
between client and server.

## Pipeline Stages

### 1. Upload

- The user selects a video file in the browser
- The file remains on the client side
- Only metadata is sent to the backend

### 2. Metadata Analysis

- Basic metadata (duration, resolution, codec) is extracted in the browser
- Results are stored as structured data
- No raw frames are transmitted to the server

### 3. Recipe Generation

- The user defines an editing plan
- The frontend converts the plan into a deterministic recipe
- The recipe describes transformations, not execution details

### 4. FFmpeg Execution

- FFmpeg.wasm executes the recipe in the browser
- Processing is isolated from server resources
- Execution results are deterministic and reproducible

### 5. Result Output

- The edited video is produced locally
- Optional export or download is handled client-side
- Backend records only the final metadata and plan reference

## Client vs Server Responsibilities

### Client Side

- Media handling
- FFmpeg execution
- Performance-sensitive operations

### Server Side

- Plan validation
- Metadata persistence
- Access control and auditability

## Performance and Security Boundaries

- No server-side video decoding
- No raw media storage in the backend
- Limited attack surface by reducing binary data handling
- Predictable load regardless of video complexity
