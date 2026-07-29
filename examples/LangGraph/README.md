# LangGraph Weather Agent

A ReAct-style weather agent built with LangGraph.

## Graph

```
[START] → assistant → tools → assistant → [END]
```

The assistant decides when to call tools. Once all tool calls are resolved it returns a final natural language answer.

## Tools

| Tool | Description |
|---|---|
| `get_current_weather` | Current conditions for a city (mocked) |
| `get_weather_forecast` | Multi-day forecast for a city (mocked) |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your OPENAI_API_KEY
```

## Run

```bash
python agent.py
```

## Swap mock data for a real API

Replace the `mock_data` dict in `get_current_weather` with a call to [OpenWeatherMap](https://openweathermap.org/api) or any other weather provider.
