"""
LangGraph Weather Agent Example
--------------------------------
A simple ReAct-style weather agent built with LangGraph.

The agent:
  1. Receives a user question about the weather
  2. Decides to call a weather tool
  3. Gets the weather data (mocked)
  4. Responds with a natural language answer

Graph shape:
    [START] → assistant → tools → assistant → [END]
"""

import json
import os
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def get_current_weather(city: str) -> str:
    """Get the current weather for a given city.

    Args:
        city: The name of the city to get weather for.

    Returns:
        A JSON string with temperature, condition, humidity and wind speed.
    """
    # Mocked weather data — swap this for a real API call (e.g. OpenWeatherMap)
    mock_data = {
        "new york":     {"temperature": "22°C", "condition": "Partly Cloudy", "humidity": "65%", "wind": "15 km/h"},
        "london":       {"temperature": "14°C", "condition": "Rainy",         "humidity": "80%", "wind": "20 km/h"},
        "tokyo":        {"temperature": "28°C", "condition": "Sunny",         "humidity": "70%", "wind": "10 km/h"},
        "sydney":       {"temperature": "18°C", "condition": "Clear",         "humidity": "55%", "wind": "25 km/h"},
        "paris":        {"temperature": "16°C", "condition": "Cloudy",        "humidity": "72%", "wind": "12 km/h"},
        "mumbai":       {"temperature": "32°C", "condition": "Humid",         "humidity": "85%", "wind": "8 km/h"},
        "bangalore":    {"temperature": "24°C", "condition": "Pleasant",      "humidity": "60%", "wind": "14 km/h"},
    }

    data = mock_data.get(city.lower(), {
        "temperature": "20°C",
        "condition": "Unknown",
        "humidity": "60%",
        "wind": "10 km/h",
    })

    return json.dumps({"city": city, **data})


@tool
def get_weather_forecast(city: str, days: int = 3) -> str:
    """Get a multi-day weather forecast for a city.

    Args:
        city: The name of the city.
        days: Number of days to forecast (1-7).

    Returns:
        A JSON string with a list of daily forecasts.
    """
    import random

    conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear", "Stormy"]
    forecast = []

    for i in range(min(days, 7)):
        forecast.append({
            "day": i + 1,
            "condition": random.choice(conditions),
            "high": f"{random.randint(15, 35)}°C",
            "low":  f"{random.randint(5, 15)}°C",
        })

    return json.dumps({"city": city, "forecast": forecast})


tools = [get_current_weather, get_weather_forecast]
tools_by_name = {t.name: t for t in tools}


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
).bind_tools(tools)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def assistant_node(state: AgentState) -> AgentState:
    """Call the LLM with the current message history."""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def tools_node(state: AgentState) -> AgentState:
    """Execute any tool calls requested by the assistant."""
    last_message: AIMessage = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        result = tool_fn.invoke(tool_call["args"])
        tool_messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
            )
        )

    return {"messages": tool_messages}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def should_continue(state: AgentState) -> str:
    """Route back to tools if the assistant made tool calls, otherwise end."""
    last_message: AIMessage = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("assistant", assistant_node)
    graph.add_node("tools", tools_node)

    graph.add_edge(START, "assistant")
    graph.add_conditional_edges("assistant", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")

    return graph.compile()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(question: str) -> str:
    app = build_graph()
    result = app.invoke({
        "messages": [HumanMessage(content=question)]
    })
    return result["messages"][-1].content


if __name__ == "__main__":
    questions = [
        "What is the current weather in Tokyo?",
        "Give me a 5-day forecast for London.",
        "Compare the weather in New York and Mumbai right now.",
    ]

    for q in questions:
        print(f"\nQ: {q}")
        print(f"A: {run(q)}")
        print("-" * 60)
