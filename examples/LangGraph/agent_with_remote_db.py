"""
Weather Agent — instrumented with Contineo Observe + remote PostgreSQL
=======================================================================

This example shows how to point Contineo at a remote database instead
of a local SQLite file. The only change from agent_with_sqlite.py is
the storage argument to contineo.init():

    # SQLite (local)
    storage = await connect("sqlite:///./contineo.db")

    # PostgreSQL (remote)
    storage = await connect("postgresql://user:pass@host:5432/mydb")

The connect() factory auto-detects the dialect from the URL scheme.
The rest of the code — attach(), invoke(), get_timeline() — is identical.

Supported URL schemes:
    sqlite:///path/to/file.db          → SqliteStorage (no extra deps)
    sqlite:///:memory:                 → SqliteStorage in-memory
    postgresql://user:pass@host/db     → PostgresStorage (requires asyncpg)
    postgres://user:pass@host/db       → PostgresStorage (alias)

Setup:
    pip install "contineo[postgres]"   # for PostgreSQL
    cp .env.example .env               # add OPENROUTER_API_KEY and DATABASE_URL

    DATABASE_URL examples:
        sqlite:///./contineo.db
        postgresql://postgres:secret@localhost:5432/contineo
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Annotated

import contineo
from contineo.storage import connect                         # 1. import connect
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv()

# Read from env — swap between SQLite and Postgres without changing code
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contineo.db")


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


# ---------------------------------------------------------------------------
# Run function — unchanged
# ---------------------------------------------------------------------------

def run(question: str) -> str:
    result = app.invoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    global app

    # 2. connect() detects the dialect from the URL — no other code changes
    storage = await connect(DATABASE_URL)
    print(f"\n  Storage backend : {type(storage).__name__}")
    print(f"  DATABASE_URL    : {DATABASE_URL}\n")

    contineo.init(project_id="weather-app", storage=storage)

    app = build_graph()
    contineo.attach(app, agent_name="weather-agent")

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

        await asyncio.sleep(0.2)   # let fire() tasks settle

        tl = contineo.get_timeline(contineo.last_session_id())
        if tl:
            print(f"\n  Timeline — {len(tl.entries)} spans\n")
            for entry in tl.sorted_entries:
                icon   = "✓" if entry.status.value == "completed" else "✗"
                dur    = f"{entry.duration_ms:.1f}ms" if entry.duration_ms else "—"
                indent = "    " if entry.kind.value in ("tool", "memory", "context") else "  "
                print(f"{indent}{icon}  {entry.label:<45} {dur}")
            if tl.total_ms:
                print(f"\n  Total: {tl.total_ms:.0f}ms")

        print("-" * 60)

    # Show all sessions stored so far
    sessions = await storage.list_sessions("weather-app", limit=10)
    print(f"\n  All sessions in DB: {len(sessions)}")
    for s in sessions:
        status = "✓" if s.is_complete else "…"
        total  = f"{s.total_ms:.0f}ms" if s.total_ms else "—"
        print(f"    {status}  {s.session_id[:8]}…  {total}")

    await storage.close()


app = None  # initialised inside main() after storage is ready

if __name__ == "__main__":
    asyncio.run(main())
