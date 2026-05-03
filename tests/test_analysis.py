"""Test suite for Clinical Intelligence System"""
import pytest
from src.main import TherapeuticCommunicationAnalyzer, analyze_transcript


@pytest.fixture
def sample_transcript():
    """Sample therapy session transcript"""
    return [
        {
            'timestamp': 0,
            'speaker': 'therapist',
            'text': 'Hello, how are you feeling today?'
        },
        {
            'timestamp': 1,
            'speaker': 'client',
            'text': 'I am feeling anxious about coming here.'
        },
        {
            'timestamp': 2,
            'speaker': 'therapist',
            'text': 'It is understandable to feel that way. Tell me more about what is causing this anxiety.'
        },
        {
            'timestamp': 3,
            'speaker': 'client',
            'text': 'I have been avoiding therapy for a long time because I am scared it will not help.'
        },
        {
            'timestamp': 4,
            'speaker': 'therapist',
            'text': 'That is a common fear, and it is important to address it. Let us work together to understand this fear better.'
        },
        {
            'timestamp': 5,
            'speaker': 'client',
            'text': 'I appreciate your understanding. I hope we can work through this together.'
        }
    ]


def test_analyze_transcript_success(sample_transcript):
    """Test successful transcript analysis"""
    result = analyze_transcript(sample_transcript, session_id='test_001', patient_id='test_patient')

    assert result['status'] == 'success'
    assert result['session_id'] == 'test_001'
    assert result['patient_id'] == 'test_patient'
    assert 'analysis' in result
    assert 'insight_report' in result


def test_analyze_empty_transcript():
    """Test analysis with empty transcript"""
    result = analyze_transcript([], session_id='test_002')

    assert result['status'] == 'error'
    assert 'message' in result


def test_sentiment_analysis(sample_transcript):
    """Test sentiment analysis component"""
    analyzer = TherapeuticCommunicationAnalyzer()
    result = analyzer.analyze_session(sample_transcript)

    assert result['status'] == 'success'
    analysis = result['analysis']

    # Check sentiment analysis results
    sentiment = analysis['sentiment_analysis']
    assert 'emotion_points' in sentiment
    assert 'summary' in sentiment
    assert len(sentiment['emotion_points']) > 0


def test_thematic_analysis(sample_transcript):
    """Test thematic extraction"""
    analyzer = TherapeuticCommunicationAnalyzer()
    result = analyzer.analyze_session(sample_transcript)

    thematic = result['analysis']['thematic_analysis']
    assert 'themes' in thematic
    assert 'cognitive_distortions' in thematic


def test_insight_report_generation(sample_transcript):
    """Test insight report generation"""
    analyzer = TherapeuticCommunicationAnalyzer()
    result = analyzer.analyze_session(sample_transcript)

    report = result['insight_report']
    assert 'session_id' in report
    assert 'sections' in report

    sections = report['sections']
    assert 'executive_summary' in sections
    assert 'thematic_analysis' in sections
    assert 'emotional_mapping' in sections
    assert 'clinical_hypothesis' in sections


def test_batch_analysis():
    """Test batch analysis"""
    sessions = [
        {
            'transcript': [
                {'speaker': 'therapist', 'text': 'Hello'},
                {'speaker': 'client', 'text': 'Hi, I am anxious'}
            ],
            'session_id': 'batch_001'
        },
        {
            'transcript': [
                {'speaker': 'therapist', 'text': 'How are you today?'},
                {'speaker': 'client', 'text': 'I am feeling sad'}
            ],
            'session_id': 'batch_002'
        }
    ]

    analyzer = TherapeuticCommunicationAnalyzer()
    results = analyzer.analyze_sessions_batch(sessions)

    assert len(results) == 2
    assert all(r['status'] == 'success' for r in results)


def test_summary_stats(sample_transcript):
    """Test summary statistics extraction"""
    analyzer = TherapeuticCommunicationAnalyzer()
    result = analyzer.analyze_session(sample_transcript)

    stats = analyzer.get_summary_stats(result)
    assert 'overall_sentiment' in stats
    assert 'emotional_stability' in stats
    assert 'dominant_theme' in stats
    assert 'therapeutic_alliance' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
