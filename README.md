# Recipe Road 🍳

An AI-powered voice-guided cooking assistant that helps you find and prepare recipes using natural language.

## Features

### 🔍 Recipe Search and Creation
1. Describe what you want to cook in plain text
2. List available ingredients
3. Get 3 AI-curated recipe suggestions from the internet
4. Recipes are formatted into clear phases and steps
5. Select your preferred recipe

### 🎙️ Voice Recipe Assistant
1. Real-time voice guidance using OpenAI's Realtime API
2. Text-to-speech instructions for each cooking step
3. Voice recognition for hands-free interaction
4. Mark steps as complete with voice commands
5. Set cooking timers by voice
6. Ask questions about the recipe anytime

## Tech Stack

- **Backend**: FastAPI + Python 3.13
- **AI**: OpenAI GPT-4o + Realtime API
- **Voice**: OpenAI Whisper (transcription) + TTS
- **WebSockets**: Real-time bidirectional communication
- **Package Management**: uv

## Prerequisites

- Python 3.13+
- OpenAI API key with access to GPT-4o and Realtime API
- uv package manager (`pip install uv`)

## Installation

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/recipe-road.git
cd recipe-road
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

3. Run the application:
```bash
./run.sh
```

### Docker Setup

1. Build and run with Docker Compose:
```bash
export OPENAI_API_KEY='your-api-key-here'
docker-compose up --build
```

## Usage

### CLI Interface (Recommended)

The easiest way to use Recipe Road is through the interactive CLI:

1. Start the API server:
```bash
./run.sh
```

2. In another terminal, run the CLI:
```bash
./run_cli.sh
```

The CLI provides:
- Interactive recipe search
- Recipe selection with detailed view
- Voice assistant integration
- Real-time audio streaming
- Timer management

### API Usage

#### 1. Search for Recipes

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "description": "quick pasta dinner",
    "ingredients": ["pasta", "tomatoes", "garlic", "olive oil"],
    "dietary_restrictions": ["vegetarian"]
  }'
```

#### 2. Select a Recipe

```bash
curl -X POST http://localhost:8000/select/{session_id} \
  -H "Content-Type: application/json" \
  -d '{
    "recipe_index": 0,
    "search_results": {...},
    "full_recipe_text": "detailed recipe text"
  }'
```

#### 3. Start Voice Assistant

Connect to the WebSocket endpoint:
```
ws://localhost:8000/assistant/{session_id}
```

Send audio data as binary messages, receive:
- Audio responses (binary)
- Control messages (JSON): `step_completed`, `timer_requested`

## Example Client

Run the example client to see the API in action:

```bash
uv run python example_client.py
```

## Project Structure

```
recipe-road/
├── src/
│   ├── agents/
│   │   ├── search.py      # Recipe search agent
│   │   ├── creator.py     # Recipe formatter agent
│   │   └── assistant.py   # Voice assistant handler
│   └── api.py            # FastAPI application
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── run.sh
└── example_client.py
```

## API Endpoints

- `GET /` - Health check
- `POST /search` - Search for recipes
- `POST /select/{session_id}` - Select and format a recipe
- `WS /assistant/{session_id}` - Voice assistant WebSocket
- `DELETE /session/{session_id}` - End a session

## Development

### Running Tests

```bash
uv run pytest
```

### Code Style

```bash
uv run ruff check .
uv run ruff format .
```

## Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (required)

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
