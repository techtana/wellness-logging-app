# Clinical Intelligence System

An API for analyzing therapeutic communication transcripts and generating structured clinical insights for mental health professionals.

## Overview

The system takes therapy session transcripts and runs them through six analysis modules, producing a clinician-ready insight report covering emotional dynamics, themes, cognitive distortions, relational patterns, and recommended interventions.

## Project Structure

```
wellness-logging-app/
├── src/
│   ├── ingestion_layer/
│   │   ├── parser.py             # Transcript parsing and standardization
│   │   └── __init__.py
│   ├── processing_layer/
│   │   ├── sentiment_analysis.py
│   │   ├── thematic_extraction.py
│   │   ├── relational_dynamics.py
│   │   ├── turn_pattern_analyzer.py
│   │   ├── feedback_loop_analyzer.py
│   │   └── clinical_significance.py
│   ├── output_layer/
│   │   ├── report.py             # Insight report generation
│   │   └── __init__.py
│   ├── api/
│   │   └── app.py                # Flask API
│   ├── config.py
│   └── main.py                   # Orchestrator
├── tests/
│   └── test_analysis.py
├── run.py
└── requirements.txt
```

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
cp .env.example .env

python run.py
```

The API starts at `http://127.0.0.1:5000`.

```bash
# With options
python run.py --host 0.0.0.0 --port 8000 --debug
```

## API Endpoints

### Health check
```
GET /health
```

### Analyze a session
```
POST /api/v1/analyze
Content-Type: application/json

{
    "transcript": [
        {"timestamp": 0, "speaker": "therapist", "text": "How have you been feeling this week?"},
        {"timestamp": 5, "speaker": "client",    "text": "Honestly, I have been struggling a lot with anxiety."}
    ],
    "session_id": "session_001",
    "patient_id": "anonymous"
}
```

### Analyze multiple sessions
```
POST /api/v1/analyze/batch
Content-Type: application/json

{
    "sessions": [
        {"transcript": [...], "session_id": "session_001"},
        {"transcript": [...], "session_id": "session_002"}
    ]
}
```

### API documentation
```
GET /api/v1/docs
```

## Response Structure

A successful response includes two top-level keys: `analysis` (raw module outputs) and `insight_report` (formatted clinician report).

```json
{
    "status": "success",
    "session_id": "session_001",
    "analysis": {
        "sentiment_analysis": {...},
        "thematic_analysis": {...},
        "turn_patterns": {...},
        "feedback_analysis": {...},
        "relational_dynamics": {...},
        "clinical_significance": {...}
    },
    "insight_report": {
        "sections": {
            "executive_summary": {...},
            "thematic_analysis": {...},
            "emotional_mapping": {...},
            "clinical_hypothesis": {...},
            "relational_dynamics": {...},
            "recommendations": {...}
        }
    }
}
```

## Transcript Format

The `transcript` field accepts a list of turn objects. Only `text` is required.

| Field | Required | Description |
|-------|----------|-------------|
| `text` | Yes | The spoken text |
| `speaker` | No | `"therapist"`, `"client"`, or `"other"` |
| `timestamp` | No | Turn start time in seconds |
| `duration` | No | Turn duration in seconds |
| `confidence` | No | ASR confidence score (0–1) |

**Validation:** transcripts must have at least 2 distinct speakers and a combined text length of 50+ characters.

## Python Usage

```python
from src.main import TherapeuticCommunicationAnalyzer

analyzer = TherapeuticCommunicationAnalyzer()

result = analyzer.analyze_session(
    transcript_data=[
        {"timestamp": 0,  "speaker": "therapist", "text": "How have you been feeling since we last met?"},
        {"timestamp": 8,  "speaker": "client",    "text": "I have been very anxious, especially at work."},
        {"timestamp": 20, "speaker": "therapist", "text": "Tell me more about what is causing that anxiety."},
        {"timestamp": 28, "speaker": "client",    "text": "I always worry I will fail and let everyone down."}
    ],
    session_id="session_001",
    patient_id="anonymous"
)

report = result["insight_report"]["sections"]
print(report["executive_summary"]["overall_tone_trajectory"])
print(report["recommendations"]["next_session_focus"])
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```env
DEBUG=False
API_HOST=127.0.0.1
API_PORT=5000

ENABLE_CLINICAL_VALIDATION=True
ENABLE_HYPOTHESIS_GENERATION=True

EMOTION_INTENSITY_THRESHOLD=15.0
DOMINANT_THEME_THRESHOLD=0.3
MIN_THEME_INSTANCES=3
```

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src
```

## Code Quality

```bash
black src/
flake8 src/ --max-line-length=100
```

## Privacy

All patient identifiers should be anonymized before submission. Transcripts are processed in-memory with no persistence by default. For production use, add encrypted storage, authentication, and audit logging.

## License

See [LICENSE](LICENSE).

---

Version 1.0.0 | Updated 2026-05-03
