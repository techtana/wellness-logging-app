"""Main orchestrator for clinical intelligence system analysis"""
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.ingestion_layer import standardize_input, TranscriptEntry
from src.processing_layer import (
    SentimentAnalyzer, ThematicExtractor, TurnPatternAnalyzer,
    FeedbackLoopAnalyzer, ClinicalSignificance, RelationalDynamicsMapper
)
from src.output_layer import ReportFormatter, InsightReport


class TherapeuticCommunicationAnalyzer:
    """Main orchestrator. Pass ai_analyzer to enable AI-powered analysis."""

    def __init__(self, ai_analyzer=None):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.thematic_extractor = ThematicExtractor()
        self.turn_pattern_analyzer = TurnPatternAnalyzer()
        self.feedback_analyzer = FeedbackLoopAnalyzer()
        self.clinical_significance = ClinicalSignificance()
        self.relational_mapper = RelationalDynamicsMapper()
        self.ai_analyzer = ai_analyzer

    def analyze_session(
        self,
        transcript_data: Any,
        session_id: str = "unknown",
        patient_id: str = "anonymous"
    ) -> Dict:
        try:
            entries = standardize_input(transcript_data)
        except ValueError as e:
            return {'status': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()}

        transcript_dicts = [
            {'timestamp': e.timestamp, 'speaker': e.speaker.value, 'text': e.text, 'time': str(e.timestamp)}
            for e in entries
        ]

        # Turn pattern and feedback analyzers are timestamp-based; keep keyword versions always
        turn_results = self.turn_pattern_analyzer.analyze_turns(transcript_dicts)
        feedback_results = self.feedback_analyzer.analyze_feedback_loops(transcript_dicts)

        ai_enhanced = False
        sentiment_results = thematic_results = relational_results = None

        if self.ai_analyzer:
            sentiment_results = self.ai_analyzer.analyze_emotions(transcript_dicts)
            thematic_results = self.ai_analyzer.analyze_themes(transcript_dicts)
            relational_results = self.ai_analyzer.analyze_dynamics(transcript_dicts)
            ai_enhanced = bool(sentiment_results or thematic_results or relational_results)

        if not ai_enhanced:
            sentiment_results = self.sentiment_analyzer.analyze_emotions(transcript_dicts)
            thematic_results = self.thematic_extractor.analyze_themes(transcript_dicts)
            relational_results = self.relational_mapper.analyze_session_dynamics(transcript_dicts)

        clinical_eval = self.clinical_significance.evaluate_clinical_significance(
            transcript_dicts, sentiment_results.get('summary', {}), turn_results, feedback_results
        )

        # Build insight report
        if ai_enhanced and self.ai_analyzer:
            ai_sections = self.ai_analyzer.generate_report_sections(
                transcript_dicts, session_id, patient_id,
                sentiment_results, thematic_results, relational_results
            )
            report = InsightReport(session_id, patient_id)
            if ai_sections:
                report.sections = ai_sections
            else:
                report = self._build_keyword_report(
                    session_id, patient_id, sentiment_results, thematic_results,
                    turn_results, relational_results
                )
        else:
            report = self._build_keyword_report(
                session_id, patient_id, sentiment_results, thematic_results,
                turn_results, relational_results
            )

        return {
            'status': 'success',
            'session_id': session_id,
            'patient_id': patient_id,
            'ai_enhanced': ai_enhanced,
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

    def _build_keyword_report(self, session_id, patient_id, sentiment, thematic, turn_patterns, relational):
        return ReportFormatter.build_complete_report(
            session_id=session_id,
            patient_id=patient_id,
            sentiment_analysis=sentiment,
            thematic_analysis=thematic,
            turn_patterns=turn_patterns,
            relational_analysis=relational,
            emotional_trajectory=sentiment.get('emotion_points', [])
        )

    def analyze_sessions_batch(self, sessions: List[Dict]) -> List[Dict]:
        return [
            self.analyze_session(
                transcript_data=s.get('transcript'),
                session_id=s.get('session_id', 'unknown'),
                patient_id=s.get('patient_id', 'anonymous')
            )
            for s in sessions
        ]

    def get_summary_stats(self, result: Dict) -> Dict:
        if result.get('status') != 'success':
            return {}
        analysis = result.get('analysis', {})
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


def analyze_transcript(
    transcript_data: Any,
    session_id: str = "unknown",
    patient_id: str = "anonymous"
) -> Dict:
    analyzer = TherapeuticCommunicationAnalyzer()
    return analyzer.analyze_session(transcript_data, session_id, patient_id)
