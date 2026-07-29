# Contineo Observe - Development Roadmap

> Build one ticket at a time. Never ask an AI coding agent to build
> multiple major features in one prompt.

## Ground Rules

-   One ticket = One PR
-   Review before merge
-   Tests required
-   No architecture changes during implementation
-   Keep tasks under \~500 lines of code

## Phase 0 - Bootstrap

### Ticket 1

-   Create monorepo
-   Backend
-   Dashboard
-   Python SDK
-   Shared package

### Ticket 2

-   Docker Compose
-   PostgreSQL
-   ClickHouse
-   Redis
-   Environment setup

### Ticket 3

-   Configuration
-   Feature flags
-   Logging

## Phase 1 - SDK

### Ticket 4

Design SDK API: - observe.init() - observe.attach() - observe.emit()

### Ticket 5

Create event models: - Event - Session - Trace - Span - ToolCall -
LLMCall

### Ticket 6

Implement event validation.

### Ticket 7

Implement event emitter.

## Phase 2 - Event Bus

### Ticket 8

publish(), subscribe(), unsubscribe()

### Ticket 9

Dispatcher

### Ticket 10

Tests

## Phase 3 - Storage

### Ticket 11

Storage abstraction

### Ticket 12

PostgreSQL

### Ticket 13

ClickHouse

### Ticket 14

Repository layer

## Phase 4 - Timeline

### Ticket 15

Timeline model

### Ticket 16

Timeline builder (pure function)

### Ticket 17

Timeline API

### Ticket 18

Timeline UI

## Phase 5 - Replay

### Ticket 19

Replay model

### Ticket 20

Replay builder

### Ticket 21

Replay API

### Ticket 22

Replay UI

## Phase 6 - Analytics

### Ticket 23

Metric definitions

### Ticket 24

Aggregation

### Ticket 25

Analytics API

### Ticket 26

Dashboard

## Phase 7 - Integrations

### Ticket 27

Integration interface

### Ticket 28

Pipecat adapter

### Ticket 29

Example application

## Phase 8 - Polish

### Ticket 30

Search

### Ticket 31

Filtering

### Ticket 32

Dark mode

### Ticket 33

Documentation

### Ticket 34

Landing page

## Prompt Template

Task: - Goal - Inputs - Outputs - Constraints - Tests - Definition of
Done

## V1 Done

-   SDK
-   Event Bus
-   Timeline
-   Replay
-   Analytics
-   Cost Tracking
-   Pipecat Integration
-   Dashboard
