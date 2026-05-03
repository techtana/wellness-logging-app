# Clinical Intelligence System - Therapeutic AI Engine

An AI-powered system for analyzing therapeutic communication and generating clinician-ready insights from mental health counseling sessions.

## 🎯 Overview

The Clinical Intelligence System evolves from descriptive analysis ("What was said?") to prescriptive/synthetic analysis ("What does this pattern suggest, and what should the clinician consider next?").

### Key Features

- **Sentiment & Emotion Analysis**: Granular detection of emotional shifts and intensity tracking
- **Thematic Extraction**: Identifies recurring themes, narrative shifts, and cognitive distortions
- **Relational Dynamics Mapping**: Analyzes therapeutic alliance and inter-speaker dynamics
- **Turn Pattern Analysis**: Examines conversation flow and engagement patterns
- **Feedback Loop Detection**: Identifies positive/negative feedback cycles
- **Clinical Significance Evaluation**: Synthesizes findings into clinically meaningful insights
- **Insight Report Generation**: Produces structured, actionable reports for clinicians

## 🏗️ Project Architecture

```
src/
├── ingestion_layer/          # Transcript parsing and standardization
├── processing_layer/         # Core analysis modules
│   ├── sentiment_analysis.py
│   ├── thematic_extraction.py
│   ├── relational_dynamics.py
│   ├── turn_pattern_analyzer.py
│   ├── feedback_loop_analyzer.py
│   └── clinical_significance.py
├── output_layer/             # Report generation and formatting
├── api/                      # Flask API endpoints
├── config.py                 # Configuration management
└── main.py                   # Main orchestrator
```

## 📊 System Flow

1. **Ingestion**: Parse and standardize therapy session transcripts
2. **Processing**: Apply six analysis modules in parallel
3. **Synthesis**: Evaluate clinical significance across analyses
4. **Output**: Generate structured insight reports

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd wellness-logging-app

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### Running the API Server

```bash
# Start the server
python run.py

# Or with custom settings
python run.py --host 0.0.0.0 --port 8000 --debug
```

The API will be available at `http://localhost:5000`

## 📡 API Endpoints

### Health Check
```
GET /health
```

### Analyze Single Session
```
POST /api/v1/analyze
Content-Type: application/json

{
    "transcript": [
        {
            "timestamp": 0,
            "speaker": "therapist",
            "text": "Hello, how are you feeling today?"
        },
        {
            "timestamp": 1,
            "speaker": "client",
            "text": "I'm feeling anxious about the upcoming presentation."
        }
    ],
    "session_id": "session_2024_001",
    "patient_id": "anonymous"
}
```

### Analyze Batch Sessions
```
POST /api/v1/analyze/batch
Content-Type: application/json

{
    "sessions": [
        {
            "transcript": [...],
            "session_id": "session_001",
            "patient_id": "patient_001"
        },
        {
            "transcript": [...],
            "session_id": "session_002",
            "patient_id": "patient_002"
        }
    ]
}
```

### API Documentation
```
GET /api/v1/docs
```

## 🔬 Analysis Output

Each analysis returns structured insights including:

### Executive Summary
- Overall tone trajectory
- Top 3 key takeaways
- Priority focus area for next session

### Thematic Deep Dive
- Dominant themes (>30% frequency)
- Underlying themes (>10% frequency)
- Narrative shifts and transitions
- Cognitive distortions detected

### Emotional Mapping
- Key emotional shifts over time
- Emotional trajectory visualization
- Emotional predictors and triggers
- Stability assessment

### Clinical Hypothesis
- Potential interventions (CBT, ACT, etc.)
- Therapeutic approaches to consider
- Journaling prompts for the client
- Follow-up session focus areas

### Relational Dynamics
- Therapeutic alliance rating
- Communication patterns
- Power dynamics assessment
- Strengths and areas for improvement

## 💡 Usage Examples

### Python Direct Usage

```python
from src.main import analyze_transcript

# Simple analysis
transcript = [
    {'speaker': 'therapist', 'text': 'How are you feeling?'},
    {'speaker': 'client', 'text': 'I feel anxious and overwhelmed.'}
]

result = analyze_transcript(
    transcript_data=transcript,
    session_id='session_001',
    patient_id='patient_001'
)

# Access specific insights
report = result['insight_report']
summary = report['sections']['executive_summary']
print(f"Overall tone: {summary['overall_tone_trajectory']}")
print(f"Priority focus: {summary['priority_focus_area']}")
```

### Using the API

```bash
# Analyze a session
curl -X POST http://localhost:5000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d @session.json

# Get API documentation
curl http://localhost:5000/api/v1/docs
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_analysis.py -v
```

## ⚙️ Configuration

Edit `.env` to customize behavior:

```env
# Debug mode
DEBUG=False

# API settings
API_HOST=127.0.0.1
API_PORT=5000

# Feature flags
ENABLE_CLINICAL_VALIDATION=True
ENABLE_HYPOTHESIS_GENERATION=True

# Analysis thresholds
EMOTION_INTENSITY_THRESHOLD=15.0
MIN_THEME_INSTANCES=3
DOMINANT_THEME_THRESHOLD=0.3
```

## 📚 Development

### Project Phases

- **Phase 2.1**: Data Foundation & Ingestion Module ✅
- **Phase 2.2**: Core Processing & Intelligence Module ✅
- **Phase 2.3**: Inference & User Interface (In Progress)
- **Phase 3**: Testing, Validation & Deployment

### Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

### Code Style

```bash
# Format code
black src/

# Check linting
flake8 src/ --max-line-length=100
```

## 📋 Transcript Format

Transcripts can be provided in multiple formats:

### List of Dictionaries (Recommended)
```json
[
    {
        "timestamp": 0,
        "speaker": "therapist",
        "text": "How have you been?",
        "duration": 5
    },
    {
        "timestamp": 5,
        "speaker": "client",
        "text": "Honestly, I've been struggling.",
        "duration": 8
    }
]
```

### Supported Fields
- **text** (required): Transcript text
- **speaker** (optional): "therapist", "client", or "other"
- **timestamp** (optional): Start time in seconds
- **time** (alternative): Alternative timestamp field
- **duration** (optional): Duration in seconds
- **confidence** (optional): 0-1 confidence score

## 🔒 Privacy & Security

- All patient identifiers should be anonymized
- Use generic IDs (patient_001, anonymous) instead of real names
- Transcripts are processed in-memory by default
- For production, implement encrypted storage and audit logging

## 📖 References

- **SDP.md**: Technical development plan
- **PRD.md**: Product requirements and philosophy
- **Architecture**: Modular microservices design

## 🤝 Support

For issues, questions, or suggestions, please refer to the documentation or create an issue in the repository.

## 📄 License

See LICENSE file for details.

---

**Version**: 1.0.0  
**Last Updated**: 2024-05-03  
**Status**: Beta - Ready for clinical pilot testing
