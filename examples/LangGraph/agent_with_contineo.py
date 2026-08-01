"""
Weather Agent — instrumented with Contineo Observe
===================================================

This file shows exactly what a developer does after:

    pip install "contineo[langgraph]"

The agent itself is a standard LangGraph ReAct agent.
Contineo is added in THREE steps and nothing else changes:

    Step 1 — Import Contineo
    Step 2 — Create bus, timeline, and handler (before the agent runs)
    Step 3 — Pass handler into app.invoke() via the callbacks config

That's it. The agent code is untouched.

Setup:
    cp .env.example .env       # add OPENROUTER_API_KEY
    python agent_with_contineo.py
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# ==========================================================================
# Step 1 — Import Contineo
# ==========================================================================
from contineo.bus import EventBus
from contineo.events.base import Framework
from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.integrations.langgraph import ContineoCallbackHandler
from contineo.timeline import TimelineService

load_dotenv()


# ==========================================================================
# Agent — 100% unchanged from a standard LangGraph agent
# ==========================================================================

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


@tool
def get_current_weather(city: str) -> str:
    """Get the current weather for a given city."""
    mock_data = {
        "new york":  {"temperature": "22°C", "condition": "Partly Cloudy", "humidity": "65%", "wind": "15 km/h"},
        "london":    {"temperature": "14°C", "condition": "Rainy",         "humidity": "80%", "wind": "20 km/h"},
        "tokyo":     {"temperature": "28°C", "condition": "Sunny",         "humidity": "70%", "wind": "10 km/h"},
        "sydney":    {"temperature": "18°C", "condition": "Clear",         "humidity": "55%", "wind": "25 km/h"},
        "paris":     {"temperature": "16°C", "condition": "Cloudy",        "humidity": "72%", "wind": "12 km/h"},
        "mumbai":    {"temperature": "32°C", "condition": "Humid",         "humidity": "85%", "wind": "8 km/h"},
        "bangalore": {"temperature": "24°C", "condition": "Pleasant",      "humidity": "60%", "wind": "14 km/h"},
    }
    data = mock_data.get(city.lower(), {
        "temperature": "20°C", "condition": "Unknown", "humidity": "60%", "wind": "10 km/h",
    })
    return json.dumps({"city": city, **data})


@tool
def get_weather_forecast(city: str, days: int = 3) -> str:
    """Get a multi-day weather forecast for a city."""
    import random
    conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear", "Stormy"]
    forecast = [
        {
            "day": i + 1,
            "condition": random.choice(conditions),
            "high": f"{random.randint(15, 35)}°C",
            "low":  f"{random.randint(5,  15)}°C",
        }
        for i in range(min(days, 7))
    ]
    return json.dumps({"city": city, "forecast": forecast})


tools          = [get_current_weather, get_weather_forecast]
tools_by_name  = {t.name: t for t in tools}

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
).bind_tools(tools)


def assistant_node(state: AgentState) -> AgentState:
    return {"messages": [llm.invoke(state["messages"])]}


def tools_node(state: AgentState) -> AgentState:
    last: AIMessage = state["messages"][-1]
    results = []
    for call in last.tool_calls:
        output = tools_by_name[call["name"]].invoke(call["args"])
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
    return {"messages": results}


def should_continue(state: AgentState) -> str:
    last: AIMessage = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("assistant", assistant_node)
    g.add_node("tools",     tools_node)
    g.add_edge(START, "assistant")
    g.add_conditional_edges("assistant", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "assistant")
    return g.compile()


# ==========================================================================
# Step 2 — Create the Contineo bus, timeline, and callback handler
#          Do this ONCE, before any agent runs.
# ==========================================================================

bus      = EventBus()
timeline = TimelineService(bus)   # auto-subscribes to the bus — no extra wiring needed

PROJECT_ID = "weather-app"
AGENT_NAME = "weather-agent"


async def run_with_contineo(question: str) -> str:
    """Run one question through the agent, fully observed by Contineo."""

    # Every run gets its own session ID and trace ID
    session_id = str(uuid.uuid4())
    trace_id   = str(uuid.uuid4())
    span_id    = str(uuid.uuid4())

    # Create a handler tied to this specific session
    handler = ContineoCallbackHandler(
        bus=bus,
        project_id=PROJECT_ID,
        session_id=session_id,
        agent_name=AGENT_NAME,
        trace_id=trace_id,
    )

    # Tell Contineo this session is starting
    await bus.publish(SessionStartedEvent(
        project_id=PROJECT_ID,
        session_id=session_id,
        trace_id=trace_id,
        span_id=span_id,
        agent_name=AGENT_NAME,
        framework=Framework.LANGGRAPH,
        input=question,
    ))

    # -----------------------------------------------------------------------
    # Step 3 — Pass the handler into invoke via config={"callbacks": [...]}
    #          This is the ONLY change to a normal app.invoke() call.
    # -----------------------------------------------------------------------
    app = build_graph()
    t0  = time.monotonic()

    result = app.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"callbacks": [handler]},          # <-- the one Contineo line
    )

    duration_ms = (time.monotonic() - t0) * 1000
    answer      = result["messages"][-1].content

    # Tell Contineo this session is done
    await bus.publish(SessionFinishedEvent(
        project_id=PROJECT_ID,
        session_id=session_id,
        trace_id=trace_id,
        span_id=span_id,
        agent_name=AGENT_NAME,
        framework=Framework.LANGGRAPH,
        output=answer,
        duration_ms=round(duration_ms, 2),
        success=True,
    ))

    # -----------------------------------------------------------------------
    # Read the timeline back — this is the data you'd send to a dashboard,
    # store in a database, or log to your observability platform.
    # -----------------------------------------------------------------------
    tl = timeline.get_timeline(session_id)

    print(f"\n{'─' * 60}")
    print(f"  Q: {question}")
    print(f"  A: {answer}")
    print(f"{'─' * 60}")
    print(f"  Timeline — {len(tl.entries)} spans recorded\n")

    for entry in tl.sorted_entries:
        status_icon = "✓" if entry.status.value == "completed" else "✗"
        duration    = f"{entry.duration_ms:.1f}ms" if entry.duration_ms else "—"
        indent      = "    " if entry.kind.value in ("tool", "memory", "context") else "  "
        print(f"{indent}{status_icon}  {entry.label:<40}  {duration}")

    print(f"\n  Total: {tl.total_ms:.1f}ms\n")

    return answer


async def main():
    questions = [
        "What is the current weather in Tokyo?",
        "Give me a 3-day forecast for London.",
        "Compare the weather in New York and Mumbai right now.",
    ]

    for question in questions:
        await run_with_contineo(question)

    await bus.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
