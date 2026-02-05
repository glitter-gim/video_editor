# Architecture Overview

## Problem Statement

This project provides a web-based video editing environment where users can define
editing plans and execute them without installing native video tools locally.
The goal is to combine a lightweight backend API with client-side video processing
while maintaining predictable performance and clear security boundaries.

## High-Level Architecture

The system is composed of four main layers:

- Backend API (FastAPI)
- Web Client (Browser-based UI)
- FFmpeg (WebAssembly)
- MariaDB (Persistent Storage)

Each layer has a strictly defined responsibility to avoid overlap and unnecessary coupling.

## Component Responsibilities

### Backend (FastAPI)

- Exposes REST APIs for plan and video management
- Validates requests and persists structured data
- Acts as the authoritative source of truth for metadata
- Does not perform heavy video processing

### Frontend (Web Client)

- Provides the user interface for editing workflows
- Manages user interaction and state
- Coordinates video processing tasks using FFmpeg.wasm

### FFmpeg (WebAssembly)

- Executes video processing commands in the browser
- Applies editing recipes generated from user-defined plans
- Avoids server-side CPU-intensive workloads

### Database (MariaDB)

- Stores plans, videos, and their relationships
- Persists reproducible editing intent rather than binary media
- Enables auditing and future reprocessing

## Why This Architecture

- Scalability: Video processing does not consume server CPU
- Security: Raw media does not need to be uploaded to the backend
- Predictability: Backend logic remains simple and testable
- Portability: Editing logic can evolve independently from infrastructure
