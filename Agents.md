# AGENTS.md

# Contineo Observe

> Runtime Intelligence Platform for AI Agents

**Mission**

Contineo Observe is a framework-agnostic runtime intelligence platform for AI agents.

It **does not build agents**.

It integrates with existing frameworks (Pipecat, LangGraph, OpenAI Agents SDK, LiveKit, MCP, etc.) to provide:

* Runtime Timeline
* Replay
* Tracing
* Analytics
* Cost Tracking

Future modules include Context, Memory, Governance and Voice Intelligence.

---

# Product Philosophy

We are **not** another:

* AI Framework
* Agent Framework
* Voice Framework
* RAG Framework
* Orchestrator

Instead we are the **Datadog + Chrome DevTools + OpenTelemetry for AI Agents**.

Our value begins **after** an agent starts running.

---

# V1 Scope

Only build the following.

## Included

* SDK
* Framework Adapter
* Event Bus
* Timeline Service
* Replay Service
* Tracing Service
* Analytics Service
* Cost Tracking
* Dashboard
* Session Explorer

## Explicitly Excluded

Do NOT implement:

* Context Engine
* Memory Engine
* Policy Engine
* Human Approval
* Voice Intelligence
* Evaluations
* Recommendations
* Security
* Multi-tenancy

These are V2+.

---

# Core Architecture

```
Framework

↓

Adapter

↓

Runtime Event Bus

↓

Timeline

Replay

Tracing

Analytics

↓

Storage

↓

Dashboard
```

Everything communicates through events.

No service should directly depend on another service.

---

# Event Driven Architecture

Everything revolves around runtime events.

Example events

```
session.started

session.finished

llm.started

llm.completed

tool.called

tool.completed

tool.failed

memory.read

memory.write

context.loaded

tts.started

tts.completed

stt.started

stt.completed

error
```

Every service subscribes to these events.

Never make Timeline call Analytics directly.

Never make Replay call Timeline.

Everything comes from the Event Bus.

---

# Architecture Principles

## 1. Framework Agnostic

Never tightly couple with Pipecat.

Instead create adapters.

```
integrations/

pipecat/

langgraph/

openai/

livekit/

mcp/

custom/
```

---

## 2. Event First

Events are immutable.

Every service derives state from events.

---

## 3. Modular

Every module must be removable.

Timeline should still work if Analytics is disabled.

Replay should work if Cost Tracking is disabled.

---

## 4. Feature Flags

EVERY feature must have a feature flag.

Example

```
ENABLE_TIMELINE=true

ENABLE_REPLAY=true

ENABLE_ANALYTICS=true

ENABLE_COST=true
```

Never hardcode features.

---

## 5. Zero Business Logic in SDK

SDK only captures events.

Business logic belongs to services.

---

# Repository Structure

```
contineo-observe/

apps/

dashboard/

backend/

packages/

sdk-python/

sdk-node/

shared/

event-schema/

integrations/

pipecat/

langgraph/

openai/

livekit/

mcp/

services/

event-bus/

timeline/

replay/

analytics/

cost/

storage/

docs/

examples/

tests/
```

---

# Event Schema

Every event must include

```
event_id

timestamp

project_id

session_id

trace_id

span_id

agent_name

framework

event_type

metadata
```

Events should be versioned.

```
version:1
```

Never introduce breaking changes.

---

# Timeline Service

Responsibilities

* Build execution timeline
* Waterfall view
* Session ordering

Must never calculate analytics.

---

# Replay Service

Responsibilities

Persist

* Prompt
* Output
* Tool Calls
* Metadata
* Event Sequence

Replay must never execute the agent.

It only reconstructs history.

---

# Analytics Service

Responsibilities

Aggregate

* Latency
* Success Rate
* Cost
* Tool Usage
* Average Duration

Never store raw session payloads.

Analytics works from events.

---

# Cost Service

Track

* Prompt Tokens
* Completion Tokens
* STT Cost
* TTS Cost
* Tool Cost

Everything should support multiple providers.

---

# Dashboard

Dashboard is read-only.

It visualizes.

Never performs business logic.

Views

* Timeline
* Replay
* Sessions
* Analytics
* Costs

---

# Storage

Recommended

Metadata

PostgreSQL

Events

ClickHouse

Replay

Object Storage

Cache

Redis

Abstract storage behind interfaces.

---

# Integrations

Every integration implements the same interface.

```
attach()

detach()

emit()

shutdown()
```

Never expose framework internals outside adapters.

---

# Coding Standards

## Language

Backend

Python

Frontend

React + TypeScript

---

## Formatting

Python

ruff

black

Frontend

eslint

prettier

---

## Architecture

Dependency Injection preferred.

Avoid singletons.

Avoid global state.

---

## Logging

Never use print().

Use structured logging.

Every log must include

```
trace_id

session_id

service
```

---

# Error Handling

No swallowed exceptions.

Every exception should emit

```
error.created
```

to the Event Bus.

---

# API Design

REST for CRUD.

WebSockets for live timeline updates.

---

# Documentation

Every public API requires

* Example
* Parameters
* Return values

Every service needs an architecture document.

---

# Testing

Minimum

* Unit Tests
* Integration Tests
* Adapter Tests

Replay correctness must be tested.

Timeline ordering must be tested.

---

# Performance Goals

Timeline generation

<100 ms

Replay load

<500 ms

Dashboard update

Real-time

SDK overhead

<5 ms/event

---

# Open Source Rules

Public APIs should remain stable.

Never break SDK APIs unnecessarily.

Deprecate before removing.

---

# Naming

Company

Contineo

Product

Contineo Observe

Future Products

* Contineo Context
* Contineo Memory
* Contineo Governance
* Contineo Voice
* Contineo Eval
* Contineo Insights

---

# Development Workflow

Before implementing any feature:

1. Define event schema.
2. Add feature flag.
3. Write interface.
4. Write tests.
5. Implement service.
6. Update documentation.
7. Add dashboard visualization.

Never skip steps.

---

# Long-term Vision

Contineo becomes the Runtime Intelligence Platform for AI Agents.

Observe is only the first product.

Future modules will plug into the same Event Bus without changing existing services.

The Event Bus is the heart of the platform.

Every new capability should consume events rather than introduce tight coupling.
