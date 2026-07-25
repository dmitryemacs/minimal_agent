# mini-agent

Minimal AI agent with bash access. Works on Windows, macOS, Linux, Android (Termux).

## Requirements

- Python 3.7+
- `pip install requests`

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key (OpenRouter)
export OPENROUTER_API_KEY="sk-or-your-key"

# 3. Run
python agent.py
```

### Using .env file

Create a `.env` file next to `agent.py`:

```
OPENROUTER_API_KEY=sk-or-your-key
MODEL=inclusionai/ling-3.0-flash:free
```

### Choosing a model

```bash
# Via environment variable
export MODEL="anthropic/claude-sonnet-4"

# Or in .env file
MODEL=anthropic/claude-sonnet-4
```

## REPL Commands

| Command | Description |
|---|---|
| `/exit` | Quit (saves session) |
| `/clear` | Clear conversation, start new session |
| `/history` | Show message history |
| `/auto` | Toggle auto-confirm for commands |
| `/sessions` | List saved sessions |
| `/resume ID` | Resume a saved session |
| `/new` | Save current session and start new |

## Building a Binary

```bash
pip install pyinstaller
python build.py
```

Output: `dist/mini-agent` (single file, ~12 MB, no dependencies).

### Running the binary

```bash
export OPENROUTER_API_KEY="sk-or-..."
./dist/mini-agent
```

## Cross-Platform

| Platform | How to run |
|---|---|
| macOS | `python agent.py` or built binary |
| Linux | `python agent.py` or built binary |
| Windows | `python agent.py` or `dist/mini-agent.exe` |
| Android (Termux) | `pkg install python && python agent.py` |

## Project Structure

```
agent.py    # REPL loop + orchestration (entry point)
api.py      # OpenRouter HTTP client (streaming)
tools.py    # Bash tool + confirmation prompt
config.py   # Configuration + .env loading
build.py    # Build script
```

## How It Works

1. User enters a message
2. Agent sends it to the model via OpenRouter API
3. Model may call a bash command (tool calling)
4. Agent shows the command and asks for confirmation `[y/n/a]`
5. Executes the command and sends the result back to the model
6. Repeats until the model gives a final answer
