# API Design and Data Model

## Design Principles

- APIs describe intent, not execution
- Resources are explicit and minimal
- Data models prioritize reproducibility over convenience

## Core API Resources

### Plan

Represents a user-defined editing intent.

- Defines how a video should be transformed
- Independent of specific input files
- Can be reused across multiple videos

Typical responsibilities:

- Create and update editing plans
- Validate logical consistency
- Provide a stable contract for recipe generation

### Video

Represents a concrete video instance.

- References source metadata
- Links to one or more plans
- Tracks processing state and results

Typical responsibilities:

- Store metadata
- Associate with plans
- Record execution outcomes

## API Endpoints (Conceptual)

- Create and retrieve plans
- Register videos and metadata
- Bind plans to videos
- Query processing history

The API avoids endpoints that directly manipulate binary video data.

## Data Model Philosophy

The MariaDB schema reflects the following assumptions:

- Editing intent is more valuable than binary output
- Videos and plans are first-class, independent entities
- Relationships are explicit and traceable

This model enables:

- Reprocessing with updated tools
- Auditing of editing decisions
- Consistent behavior across environments
