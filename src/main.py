"""Main orchestrator for clinical intelligence system analysis"""
from typing import Dict, List, Any
from datetime import datetime

from src.ingestion_layer import standardize_input, TranscriptEntry
from src.processing_layer import (
    SentimentAnalyzer,
    ThematicExtractor,
    TurnPatternAnalyzer,
    FeedbackLoopAnalyzer,
    ClinicalSignificance,
    RelationalDynamicsMapper
)
from src.output_layer import ReportFormatter, InsightReport


class TherapeuticCommunicationAnalyzer:
    """Main orchestrator for analyzing therapeutic communication"""

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.thematic_extractor = ThematicExtractor()
        self.turn_pattern_analyzer = TurnPatternAnalyzer()
        self.feedback_analyzer = FeedbackLoopAnalyzer()
        self.clinical_significance = ClinicalSignificance()
        self.relational_mapper = RelationalDynamicsMapper()

    def analyze_session(self, transcript_data: Any, session_id: str = "unknown", patient_id: str = "anonymous") -> Dict:
        """
        Comprehensive analysis of a therapeutic session.

        Args:
            transcript_data: Can be list of dicts, JSON string, or dict
            session_id: Identifier for the session
            patient_id: Identifier for the patient (anonymized)

        Returns:
            Complete analysis including insights report
        """
        # Standardize input
        try:
            entries = standardize_input(transcript_data)
        except ValueError as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }

        # Convert to dict format for processing
        transcript_dicts = [
            {
                'timestamp': e.timestamp,
                'speaker': e.speaker.value,
                'text': e.text,
                'time': str(e.timestamp)
            }
            for e in entries
        ]

        # Run all analyses
        sentiment_results = self.sentiment_analyzer.analyze_emotions(transcript_dicts)
        thematic_results = self.thematic_extractor.analyze_themes(transcript_dicts)
        turn_results = self.turn_pattern_analyzer.analyze_turns(transcript_dicts)
        feedback_results = self.feedback_analyzer.analyze_feedback_loops(transcript_dicts)
        relational_results = self.relational_mapper.analyze_session_dynamics(transcript_dicts)

        # Evaluate clinical significance
        clinical_eval = self.clinical_significance.evaluate_clinical_significance(
            transcript_dicts,
            sentiment_results.get('summary', {}),
            turn_results,
            feedback_results
        )

        # Generate insight report
        emotion_points = sentiment_results.get('emotion_points', [])
        report = ReportFormatter.build_complete_report(
            session_id=session_id,
            patient_id=patient_id,
            sentiment_analysis=sentiment_results,
            thematic_analysis=thematic_results,
            turn_patterns=turn_results,
            relational_analysis=relational_results,
            emotional_trajectory=emotion_points
        )

        # Compile comprehensive results
        return {
            'status': 'success',
            'session_id': session_id,
            'patient_id': patient_id,
            'analysis': {
                'sentiment_analysis': sentiment_results,
                'thematic_analysis': thematic_results,
                'turn_patterns': turn_results,
                'feedback_analysis': feedback_results,
                'relational_dynamics': relational_results,
                'clinical_significance': clinical_eval
            },
            'insight_report': report.to_dict(),
            'timestamp': datetime.now().isoformat()
        }

    def analyze_sessions_batch(self, sessions: List[Dict]) -> List[Dict]:
        """
        Analyze multiple sessions in batch.

        Args:
            sessions: List of dicts with 'transcript', 'session_id', 'patient_id'

        Returns:
            List of analysis results
        """
        results = []
        for session in sessions:
            result = self.analyze_session(
                transcript_data=session.get('transcript'),
                session_id=session.get('session_id', 'unknown'),
                patient_id=session.get('patient_id', 'anonymous')
            )
            results.append(result)
        return results

    def get_summary_stats(self, analysis_result: Dict) -> Dict:
        """
        Extract summary statistics from analysis result.

        Returns:
            Key metrics for quick overview
        """
        if analysis_result.get('status') != 'success':
            return {}

        analysis = analysis_result.get('analysis', {})
        sentiment = analysis.get('sentiment_analysis', {})
        thematic = analysis.get('thematic_analysis', {})
        relational = analysis.get('relational_dynamics', {})

        return {
            'overall_sentiment': sentiment.get('summary', {}).get('overall_sentiment', 'Unknown'),
            'emotional_stability': sentiment.get('summary', {}).get('emotional_stability', 'Unknown'),
            'dominant_theme': thematic.get('themes', [{}])[0].get('theme', 'Unknown') if thematic.get('themes') else 'Unknown',
            'therapeutic_alliance': relational.get('therapeutic_alliance', {}).get('rating', 'Unknown'),
            'number_of_emotional_shifts': len(sentiment.get('significant_shifts', [])),
            'number_of_themes': len(thematic.get('themes', [])),
            'cognitive_distortions_detected': len(thematic.get('cognitive_distortions', []))
        }


# Convenience function for quick analysis
def analyze_transcript(transcript_data: Any, session_id: str = "unknown", patient_id: str = "anonymous") -> Dict:
    """Quick analysis function"""
    analyzer = TherapeuticCommunicationAnalyzer()
    return analyzer.analyze_session(transcript_data, session_id, patient_id)
