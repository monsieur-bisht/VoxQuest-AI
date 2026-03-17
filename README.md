# VoxQuest-AI

VoxQuest-AI is a starter full-stack **voice-first RPG storytelling assistant** and **speech AI benchmarking framework**.

## Stack
- **Frontend:** Next.js (voice recorder, waveform, narration panel, choice buttons)
- **Backend:** FastAPI (speech transcription endpoint, RPG engine, save/load, benchmarking, dataset tagging/export)
- **Storage:** SQLite (sessions, benchmark logs, dataset entries)

## Features Included
- Browser mic recording + waveform visualization
- Speech-to-speech gameplay loop (ASR endpoint -> RPG response -> browser TTS narration)
- Scene-based branching story engine with relationship score and emotional narration tuning
- Session save/load APIs
- Benchmarking outputs: WER, confidence, latency, language mode
- Dataset collection: language/noise/accent tagging + JSON/CSV export
- Hindi-English code-switch detection starter
- Docker support for frontend and backend

## Run Locally

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Then open http://localhost:3000.

## API Endpoints
- `POST /api/game/start`
- `POST /api/speech/transcribe`
- `POST /api/game/turn`
- `POST /api/game/save`
- `POST /api/game/load`
- `POST /api/dataset/tag`
- `GET /api/dataset/export?format=json|csv`

## Docker
```bash
docker compose up --build
```

## Environment Variables
- `NEXT_PUBLIC_API_BASE` (frontend): backend URL (default `http://localhost:8000`)

## ML Utilities
```bash
cd backend
# Config-driven model switch starter
cat ml_utils/model_config.json

# Benchmark runner (expects a started session_id and sample JSON file)
python ml_utils/benchmark_cli.py --session-id <session_id> --file <samples.json>

# Prepare exported dataset for Whisper fine-tuning pipeline
python ml_utils/whisper_finetune_prep.py --input /tmp/dataset.json --output /tmp/whisper.jsonl
```

## Notes
This is an initial starter implementation designed for extension:
- Plug in OpenAI Whisper in `/api/speech/transcribe`
- Replace browser TTS with ElevenLabs if needed
- Add persistent object storage for raw audio files
- Expand benchmark CLI + whisper fine-tuning utilities
