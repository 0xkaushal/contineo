"""
Weather Agent — instrumented with Contineo Observe + SQLite persistence
=======================================================================

This example shows how to add local persistence so timelines survive
process restarts. The only change from agent_with_attach.py is one
extra import and one extra argument to contineo.init():

    from contineo.storage import SqliteStorage

    contineo.init(
        project_id="weather-app",
        storage=SqliteStorage("./contineo.db"),   # ← add this
    )

After running this script you will find a contineo.db file next to it.
Run it again — the second run will show sessions from previous runs
loaded from disk.

Setup:
    cp .env.example .env      # add OPENROUTER_API_KEY
    python agent_with_sqlite.py
"""

import json
import os
import asyncio
from pathlib import Path
from typing import Annotated

import contineo
from contineo.storage import SqliteStorage                   # 1. import storage
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv()

# Database lives next to this script
DB_PATH = Path(__file__).parent / "contineo.db"

contineo.init(
    project_id="weather-app",
    storage=SqliteStorage(DB_PATH),                          # 2. pass storage
)


# ---------------------------------------------------------------------------
# Agent — unchanged from agent.py
# ---------------------------------------------------------------------------

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


tools         = [get_current_weather, get_weather_forecast]
tools_by_name = {t.name: t for t in tools}

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


app = build_graph()
contineo.attach(app, agent_name="weather-agent")             # 3. attach


# ---------------------------------------------------------------------------
# Run function — unchanged
# ---------------------------------------------------------------------------

def run(question: str) -> str:
    result = app.invoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_timeline(timeline) -> None:
    print(f"\n  Timeline — {len(timeline.entries)} spans\n")
    for entry in timeline.sorted_entries:
        icon   = "✓" if entry.status.value == "completed" else "✗"
        dur    = f"{entry.duration_ms:.1f}ms" if entry.duration_ms else "—"
        indent = "    " if entry.kind.value in ("tool", "memory", "context") else "  "
        print(f"{indent}{icon}  {entry.label:<45} {dur}")
    if timeline.total_ms:
        print(f"\n  Total: {timeline.total_ms:.0f}ms")


async def print_past_sessions() -> None:
    """Load and print all sessions stored in the database from previous runs."""
    from contineo.sdk.state import state
    if state.storage is None:
        return

    sessions = await state.storage.list_sessions("weather-app", limit=20)

    # Filter out sessions from this run (already printed above)
    current_sid = contineo.last_session_id()
    past = [s for s in sessions if s.session_id != current_sid]

    if not past:
        print("\n  (no previous sessions found in contineo.db)")
        return

    print(f"\n{'='*60}")
    print(f"  Previous sessions from contineo.db ({len(past)} found)")
    print(f"{'='*60}")

    for s in past[:5]:  # show up to 5 past sessions
        # Load full timeline for this session
        tl = await state.storage.get_timeline(s.session_id)
        if tl is None:
            continue
        status = "✓" if tl.is_complete else "…"
        total  = f"{tl.total_ms:.0f}ms" if tl.total_ms else "—"
        print(f"\n  {status} Session {s.session_id[:8]}…  ({len(tl.entries)} spans, {total})")
        for entry in tl.sorted_entries:
            icon   = "✓" if entry.status.value == "completed" else "✗"
            indent = "    " if entry.kind.value in ("tool", "memory", "context") else "  "
            dur    = f"{entry.duration_ms:.1f}ms" if entry.duration_ms else "—"
            print(f"{indent}{icon}  {entry.label:<45} {dur}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    questions = [
        "What is the current weather in Tokyo?",
        "Give me a 3-day forecast for London.",
    ]

    for question in questions:
        print(f"\n{'='*60}")
        print(f"  Q: {question}")
        print(f"{'='*60}")

        answer = run(question)
        print(f"\n  A: {answer}")

        import time; time.sleep(0.05)   # let storage writes settle

        tl = contineo.get_timeline(contineo.last_session_id())
        if tl:
            print_timeline(tl)

        print("-" * 60)

    # Show sessions from previous runs stored in contineo.db
    await print_past_sessions()

    print(f"\n  Database saved to: {DB_PATH}")
    print(f"  Run this script again to see sessions accumulate.\n")


if __name__ == "__main__":
    asyncio.run(main())
