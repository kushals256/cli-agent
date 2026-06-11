# 🤖 CLI Agent — Frontend Reconstruction

A conversational CLI agent that clones websites by generating fully working HTML, CSS, and JavaScript files — powered by NVIDIA's Gemma AI model.

> An AI-powered tool that automates frontend website cloning using browser automation and LLM reasoning.

---

## ✨ Features

- **Conversational CLI** — Chat with the agent directly in your terminal
- **AI-Powered Reasoning** — The agent thinks step-by-step using a ReAct-style loop (START → THINK → TOOL → OBSERVE → OUTPUT)
- **Browser Automation** — Uses Playwright to open websites, extract DOM structure, and gather styles
- **Code Generation** — Generates clean, semantic HTML/CSS/JS based on extracted data
- **Auto-Retry** — Handles malformed AI responses gracefully with retry logic
- **Context Trimming** — Keeps API payloads lean for fast responses across all steps
- **Beautiful Output** — Color-coded step display using Rich

---

## 🏗️ Architecture

```
User Input
    │
    ▼
┌─────────┐     ┌─────────┐     ┌──────────┐
│  main.py │────▶│ agent.py │────▶│  llm.py  │
│  (CLI)   │     │  (Loop)  │     │ (NVIDIA) │
└─────────┘     └────┬─────┘     └──────────┘
                     │
                     ▼
               ┌──────────┐
               │ tools.py  │
               │ (Browser, │
               │  FS, Shell)│
               └──────────┘
```

### Agent Loop

```
START ──▶ THINK ──▶ TOOL ──▶ OBSERVE ──▶ THINK ──▶ ... ──▶ OUTPUT
```

The agent loops through reasoning steps, never completing everything in a single step. Each iteration:
1. **THINK** — Reasons about what to do next
2. **TOOL** — Executes one action (open browser, extract DOM, save file, etc.)
3. **OBSERVE** — Receives the tool result
4. Repeats until all files are generated and validated

---

## 📁 Project Structure

```
cli-agent/
├── main.py              # CLI entry point (Rich-powered interface)
├── agent.py             # Core agent loop with ReAct reasoning
├── llm.py               # NVIDIA API wrapper (streaming support)
├── tools.py             # Tool registry (Playwright, file system, shell)
├── prompt.py            # System prompt for the AI agent
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- An [NVIDIA API Key](https://build.nvidia.com/) (free tier available)

### Installation

```bash
# Clone the repository
git clone https://github.com/kushals256/cli-agent.git
cd cli-agent

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Set up your API key
cp .env.example .env
# Edit .env and add your NVIDIA API key
```

### Usage

```bash
python3 main.py
```

Then type your instruction:

```
You: Clone the Scaler Academy website header and hero section from https://www.scaler.com/academy/
```

The agent will:
1. Open the website using Playwright
2. Extract the DOM structure and styles
3. Generate `index.html`, `style.css`, and `script.js`
4. Save the files locally
5. Validate the output

Open the generated `index.html` in your browser to see the result.

---

## 🛠️ Tools Available

| Tool | Description |
|------|-------------|
| `browser_open(url)` | Opens a website in headless Chromium |
| `browser_extract_dom()` | Extracts cleaned HTML body structure |
| `browser_extract_styles()` | Extracts colors, fonts, and spacing |
| `fs_write_file(path, content)` | Writes a file to disk |
| `shell_exec(command)` | Runs a terminal command |
| `validator_compare(source_url, local_path)` | Validates generated output |

---

## ⚙️ Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `NVIDIA_API_KEY` | Your NVIDIA API key for the Gemma model |

The agent uses the `meta/llama-3.1-8b-instruct` model via NVIDIA's OpenAI-compatible API. You can change this in `agent.py`.

---

## 📄 License

This project is built for educational purposes.
