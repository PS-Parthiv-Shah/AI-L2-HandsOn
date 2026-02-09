# AI Engineering L2: Hands-On Projects 🚀

This repository contains hands-on projects for the AI Engineering Level 2 course.

---

## 🧙‍♂️ Weekend Wizard

Weekend Wizard is a friendly AI agent designed to help you plan a chill weekend itinerary. It can check the weather, recommend books based on your favorite genres, tell jokes, share dog pictures, and even quiz you with trivia.

The agent uses a **ReAct (Reasoning and Acting)** loop to decide which tools to call over the **Model Context Protocol (MCP)** and runs fully locally using **Ollama**.

### � Features

- **Agentic Loop**: Decides when to use tools vs. when to answer directly.
- **MCP Tool Server**: Robust tools for Weather, Books, Jokes, Dog Photos, and Geocoding.
- **Personalization**: Uses a `prefs.json` file to tailor recommendations (e.g., favorite book genres).
- **Web Interface**: Includes a FastAPI backend and a clean HTML/JS chat UI.
- **Robustness**: Built-in retry logic for API calls and JSON "repair" for LLM outputs.

### 🛠️ Prerequisites

1.  **Python 3.10+**
2.  **Ollama**: Install from [ollama.com](https://ollama.com).
3.  **Local Model**: Pull the Mistral model:
    ```bash
    ollama pull mistral:7b
    ```

### 📦 Installation

1.  **Clone** the project and enter the directory.
2.  **Create a Virtual Environment** and activate it:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r weekend-wizard/requirements.txt
    ```

### 🎮 How to Run

#### 1. CLI Agent
Ideal for a quick terminal-based chat.
```bash
python weekend-wizard/src/agent_fun.py
```

#### 2. Web Interface (Robust Start)
To avoid "Port already in use" errors, use the startup script:
```bash
python weekend-wizard/start_web.py
```
This script automatically kills any lingering processes on port 8000 before starting.

1.  **Start the Backend**:
    ```bash
    python weekend-wizard/start_web.py
    ```
2.  **Open the UI**:
    Open `weekend-wizard/templates/index.html` in your browser.

### ⚙️ Configuration

You can personalize the agent by editing `weekend-wizard/config/prefs.json`:
```json
{
  "favorite_genre": "Science Fiction",
  "home_city": "New York",
  "model_temperature": 0.3
}
```

### 🔍 Observability

- **Logs**: Check `weekend-wizard/wizard.log` for a full history of LLM calls, tool usage, and errors.
- **CLI Feedback**: The CLI shows "Thinking..." and "Calling tool..." animations to keep you informed.
- **Web UI Feedback**: The chat interface streams real-time status updates while the agent is working.

### 📁 Project Structure

```
.
├── weekend-wizard/   # Core project logic, UI, and config
│   ├── src/          # Agent and MCP Server logic
│   ├── templates/    # Frontend UI (HTML/JS)
│   ├── config/       # Preferences
│   └── start_web.py  # Web UI startup script
├── .gitignore        # Git exclusion rules
└── README.md         # This file!
```

### 📚 Tools Included

- `get_weather`: Current conditions via Open-Meteo.
- `city_to_coords`: Geocoding city names to coordinates.
- `book_recs`: Suggestions via Open Library.
- `random_joke`: Safe one-liners from JokeAPI.
- `random_dog`: Dog image URLs via Dog CEO.
- `trivia`: Questions from Open Trivia DB.
