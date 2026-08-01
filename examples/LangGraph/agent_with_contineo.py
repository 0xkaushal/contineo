"""
Weather Agent — instrumented with Contineo Observe
===================================================

This is what a developer writes after:

    pip install "contineo[langgraph]"

Three things change from a plain LangGraph agent:

    1.  import contineo
    2.  contineo.init(project_id="...")         — once at startup
    3.  @contineo.observe(agent_name="...")     — on the run function

Nothing else changes. The agent code is identical to agent.py.
"""

import json
import os
from typing import Annotated

import contineo                                          # 1. import
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv()

contineo.init(project_id="weather-app")                 # 2. init once


# ---------------------------------------------------------------------------
# Agent — 100% standard LangGraph, nothing Contineo-specific below this line
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


# ---------------------------------------------------------------------------
# The only thing that changes from a plain agent — the decorator
# ---------------------------------------------------------------------------

@contineo.observe(agent_name="weather-agent")           # 3. observe
def run(question: str) -> str:
    result = app.invoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].content


# ---------------------------------------------------------------------------
# Run and print timeline
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    questions = [
        "What is the current weather in Tokyo?",
        "Give me a 3-day forecast for London.",
        "Compare the weather in New York and Mumbai right now.",
    ]

    for question in questions:
        print(f"\nQ: {question}")
        answer = run(question)
        print(f"A: {answer}")

        # Read the timeline Contineo recorded for this run
        timeline = contineo.get_timeline(contineo.last_session_id())
        print(f"\nTimeline — {len(timeline.entries)} spans\n")
        for entry in timeline.sorted_entries:
            icon   = "✓" if entry.status.value == "completed" else "✗"
            dur    = f"{entry.duration_ms:.1f}ms" if entry.duration_ms else "—"
            indent = "    " if entry.kind.value in ("tool", "memory", "context") else "  "
            print(f"{indent}{icon}  {entry.label:<45} {dur}")

        print(f"\n  Total: {timeline.total_ms:.0f}ms")
        print("-" * 60)
