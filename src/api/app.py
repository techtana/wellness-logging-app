"""API Layer - Flask application for clinical intelligence system"""
from flask import Flask, request, jsonify
from datetime import datetime
import logging

from src.main import TherapeuticCommunicationAnalyzer
from src.config import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    """Factory function to create Flask application"""
    app = Flask(__name__)
    app.config.update(
        DEBUG=config.DEBUG,
        TESTING=config.TESTING,
        JSON_SORT_KEYS=False
    )

    # Initialize analyzer
    analyzer = TherapeuticCommunicationAnalyzer()

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'healthy',
            'service': 'Clinical Intelligence System',
            'timestamp': datetime.now().isoformat()
        }), 200

    # Main analysis endpoint
    @app.route('/api/v1/analyze', methods=['POST'])
    def analyze_session():
        """
        Analyze a therapy session transcript.

        Expected JSON:
        {
            "transcript": [...],  # List of dicts or JSON string
            "session_id": "...",  # Optional
            "patient_id": "..."   # Optional
        }
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400

            transcript = data.get('transcript')
            if not transcript:
                return jsonify({'error': 'Missing transcript field'}), 400

            session_id = data.get('session_id', f"session_{datetime.now().timestamp()}")
            patient_id = data.get('patient_id', 'anonymous')

            # Run analysis
            result = analyzer.analyze_session(
                transcript_data=transcript,
                session_id=session_id,
                patient_id=patient_id
            )

            return jsonify(result), 200 if result.get('status') == 'success' else 400

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return jsonify({
                'error': 'Analysis failed',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    # Batch analysis endpoint
    @app.route('/api/v1/analyze/batch', methods=['POST'])
    def analyze_batch():
        """
        Analyze multiple sessions in batch.

        Expected JSON:
        {
            "sessions": [
                {
                    "transcript": [...],
                    "session_id": "...",
                    "patient_id": "..."
                },
                ...
            ]
        }
        """
        try:
            data = request.get_json()

            if not data or 'sessions' not in data:
                return jsonify({'error': 'Missing sessions field'}), 400

            sessions = data.get('sessions', [])
            if not sessions:
                return jsonify({'error': 'sessions array is empty'}), 400

            # Run batch analysis
            results = analyzer.analyze_sessions_batch(sessions)

            return jsonify({
                'status': 'success',
                'sessions_analyzed': len(results),
                'results': results,
                'timestamp': datetime.now().isoformat()
            }), 200

        except Exception as e:
            logger.error(f"Batch analysis error: {str(e)}")
            return jsonify({
                'error': 'Batch analysis failed',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    # Get summary stats endpoint
    @app.route('/api/v1/summary/<session_id>', methods=['GET'])
    def get_summary(session_id):
        """Get summary statistics for a session"""
        return jsonify({
            'note': 'Store analysis results and retrieve by session_id',
            'session_id': session_id
        }), 501  # Not implemented (would need persistent storage)

    # API documentation endpoint
    @app.route('/api/v1/docs', methods=['GET'])
    def api_docs():
        """API documentation"""
        return jsonify({
            'service': 'Clinical Intelligence System - API',
            'version': '1.0.0',
            'endpoints': {
                'health': {
                    'method': 'GET',
                    'path': '/health',
                    'description': 'Health check endpoint'
                },
                'analyze': {
                    'method': 'POST',
                    'path': '/api/v1/analyze',
                    'description': 'Analyze a single therapy session transcript',
                    'required_fields': ['transcript'],
                    'optional_fields': ['session_id', 'patient_id']
                },
                'analyze_batch': {
                    'method': 'POST',
                    'path': '/api/v1/analyze/batch',
                    'description': 'Analyze multiple therapy session transcripts',
                    'required_fields': ['sessions']
                },
                'docs': {
                    'method': 'GET',
                    'path': '/api/v1/docs',
                    'description': 'This documentation'
                }
            },
            'transcript_format': {
                'example': [
                    {
                        'timestamp': 0,
                        'speaker': 'therapist',
                        'text': 'How are you feeling today?'
                    },
                    {
                        'timestamp': 1,
                        'speaker': 'client',
                        'text': 'I feel anxious about the situation.'
                    }
                ],
                'required_fields': ['text'],
                'optional_fields': ['timestamp', 'speaker', 'time', 'duration']
            }
        }), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500

    return app
