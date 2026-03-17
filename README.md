# VoxQuest-AI 🎙️⚔️

Voice-first interactive RPG system for benchmarking real-world speech AI. Includes ASR evaluation, multilingual voice interactions, speech-to-speech pipeline, dataset logging, and dynamic LLM storytelling.

## Features

- 🎙️ **Voice-First Interface**: Speak your choices in the RPG story
- 🤖 **ASR Pipeline**: OpenAI Whisper & wav2vec2 transcription
- 🗣️ **Text-to-Speech**: Natural narration using gTTS/pyttsx3
- 📊 **WER/CER Evaluation**: Real-time speech quality metrics
- 🌐 **Multilingual Support**: Hindi-English code-switched speech
- 🎮 **Branching Story Engine**: Dynamic RPG narrative with LLM
- 📈 **Benchmarking Dashboard**: Performance tracking & visualization
- 💾 **Dataset Export**: Anonymized speech data for model training

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Next.js    │───▶│  FastAPI     │───▶│  ASR (Whisper)  │
│  Frontend   │    │  Backend     │    │  LLM (OpenAI)   │
│  Port 3000  │◀───│  Port 8000   │    │  TTS (gTTS)     │
└─────────────┘    └──────────────┘    └─────────────────┘
                         │
                   ┌─────▼──────┐
                   │  ML Eval   │
                   │  WER/CER   │
                   │  Dataset   │
                   └────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- ffmpeg (for audio processing)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys (optional)
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

### Docker Compose

```bash
docker-compose up --build
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for LLM & Whisper API |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model size: tiny/base/small/medium/large |
| `TTS_ENGINE` | `gtts` | TTS engine: gtts/pyttsx3 |
| `LLM_PROVIDER` | `openai` | LLM provider: openai/anthropic |
| `LLM_MODEL` | `gpt-3.5-turbo` | LLM model name |
| `DATA_DIR` | `./data` | Directory for storing data |

## API Endpoints

### Story API
- `POST /api/story/start` - Start new game session
- `POST /api/story/choice` - Submit player choice
- `GET /api/story/state/{session_id}` - Get game state
- `POST /api/story/save/{session_id}` - Save game
- `POST /api/story/reset/{session_id}` - Reset game

### ASR API
- `POST /api/asr/transcribe` - Transcribe audio file
- `GET /api/asr/models` - List available ASR models

### TTS API
- `POST /api/tts/synthesize` - Convert text to speech

### Benchmark API
- `POST /api/benchmark/run` - Run benchmark suite
- `GET /api/benchmark/metrics` - Get aggregate metrics
- `GET /api/benchmark/results` - Get all results

### Dataset API
- `GET /api/dataset/entries` - List dataset entries
- `GET /api/dataset/export` - Export dataset (JSON/CSV)

## Running Evaluations

### CLI Benchmark Tool

```bash
# List available models
python -m ml.cli.benchmark_cli list-models

# Quick transcription test
python -m ml.cli.benchmark_cli quick-test --text "Hello world" --model whisper-base

# Run full benchmark
python -m ml.cli.benchmark_cli run --model whisper-base --output ./results

# Generate report from saved results
python -m ml.cli.benchmark_cli report --results-file ./results/benchmark_results.json
```

### Python API

```python
from ml.evaluation.benchmark_runner import BenchmarkRunner, BenchmarkConfig, TestCase

config = BenchmarkConfig(
    model_name="whisper-base",
    test_cases=[
        TestCase(reference_text="Hello world", language="en"),
        TestCase(reference_text="जंगल में जाओ", language="hi"),
    ]
)
runner = BenchmarkRunner(config)
results = runner.run()
print(f"Average WER: {results['avg_wer']:.2%}")
```

## Multilingual Support

The system supports Hindi-English (Hinglish) code-switched speech via the `jungle_quest_multilingual` scenario:

```bash
python -c "
from ml.scenarios.scenario_loader import ScenarioLoader
loader = ScenarioLoader()
scenario = loader.load('ml/scenarios/multilingual_story.json')
phrases = loader.get_benchmark_phrases(scenario)
for p in phrases:
    print(f'{p[\"language\"]}: {p[\"text\"]}')
"
```

## Metrics & Evaluation

| Metric | Description |
|--------|-------------|
| WER | Word Error Rate (lower is better) |
| CER | Character Error Rate (lower is better) |
| RTF | Real-Time Factor (< 1.0 = faster than real-time) |
| Latency (p99) | 99th percentile response latency |

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_eval_service.py -v
```

## Dataset Export

```bash
# Export as JSON
curl http://localhost:8000/api/dataset/export?format=json -o dataset.json

# Export as CSV
curl http://localhost:8000/api/dataset/export?format=csv -o dataset.csv
```

## License

MIT

---

# Original README
Voice-first interactive RPG system for benchmarking real-world speech AI. Includes ASR evaluation, multilingual voice interactions, speech-to-speech pipeline, dataset logging, and dynamic LLM storytelling. Built to simulate real conversational voice UX under noisy and accented conditions.
