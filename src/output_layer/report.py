"""Output Layer - Generates clinician-ready insight reports"""
from typing import Dict, List, Any
from datetime import datetime
import json


class InsightReport:
    """Structured insight report for clinicians"""

    def __init__(self, session_id: str, patient_id: str):
        self.session_id = session_id
        self.patient_id = patient_id
        self.timestamp = datetime.now().isoformat()
        self.sections = {}

    def add_executive_summary(self, summary_data: Dict) -> None:
        self.sections['executive_summary'] = {
            'overall_tone_trajectory': summary_data.get('tone_trajectory', 'Unknown'),
            'key_takeaways': summary_data.get('takeaways', []),
            'priority_focus_area': summary_data.get('focus_area', 'TBD'),
            'session_duration': summary_data.get('duration', 'Unknown')
        }

    def add_thematic_analysis(self, thematic_data: Dict) -> None:
        self.sections['thematic_analysis'] = {
            'dominant_themes': thematic_data.get('dominant_themes', []),
            'underlying_themes': thematic_data.get('underlying_themes', []),
            'pattern_detection': thematic_data.get('pattern_detection', []),
            'cognitive_distortions': thematic_data.get('cognitive_distortions', [])
        }

    def add_emotional_mapping(self, emotional_data: Dict) -> None:
        self.sections['emotional_mapping'] = {
            'key_shifts': emotional_data.get('shifts', []),
            'emotional_trajectory': emotional_data.get('trajectory', []),
            'predictors': emotional_data.get('predictors', []),
            'stability_assessment': emotional_data.get('stability', 'Unknown')
        }

    def add_clinical_hypothesis(self, hypothesis_data: Dict) -> None:
        self.sections['clinical_hypothesis'] = {
            'potential_interventions': hypothesis_data.get('interventions', []),
            'therapeutic_approaches': hypothesis_data.get('approaches', []),
            'journaling_prompts': hypothesis_data.get('prompts', []),
            'follow_up_focus': hypothesis_data.get('follow_up', '')
        }

    def add_relational_dynamics(self, relational_data: Dict) -> None:
        self.sections['relational_dynamics'] = {
            'therapeutic_alliance_rating': relational_data.get('alliance_rating', 'Unknown'),
            'communication_patterns': relational_data.get('patterns', {}),
            'power_dynamics': relational_data.get('power_dynamics', {}),
            'areas_of_strength': relational_data.get('strengths', []),
            'areas_for_improvement': relational_data.get('improvements', [])
        }

    def add_clinical_recommendations(self, recommendations: Dict) -> None:
        self.sections['recommendations'] = {
            'immediate_actions': recommendations.get('immediate', []),
            'next_session_focus': recommendations.get('next_session', ''),
            'monitoring_points': recommendations.get('monitoring', []),
            'red_flags': recommendations.get('red_flags', [])
        }

    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'patient_id': self.patient_id,
            'timestamp': self.timestamp,
            'sections': self.sections
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class ReportFormatter:
    """Format analysis results into clinician-ready insights"""

    @staticmethod
    def generate_executive_summary(
        sentiment_analysis: Dict,
        thematic_analysis: Dict,
        emotional_trajectory: List[Dict]
    ) -> Dict:
        if emotional_trajectory:
            avg_intensity = sum(e['intensity'] for e in emotional_trajectory) / len(emotional_trajectory)
            if avg_intensity > 60:
                tone = "Session showed elevated emotional intensity with some volatility"
            elif avg_intensity > 40:
                tone = "Session maintained moderate emotional engagement"
            else:
                tone = "Session showed stable, controlled emotional tone"
        else:
            tone = "Unable to determine tone trajectory"

        themes = thematic_analysis.get('dominant_themes', [])
        top_themes = [t['theme'] for t in themes[:3]] if themes else []

        takeaways = []
        if themes:
            takeaways.append(f"Primary themes discussed: {', '.join(top_themes)}")

        if emotional_trajectory:
            shift_count = sum(
                1 for i in range(1, len(emotional_trajectory))
                if emotional_trajectory[i]['emotion'] != emotional_trajectory[i - 1]['emotion']
            )
            if shift_count > 2:
                takeaways.append(f"Notable emotional shifts: {shift_count} significant changes in emotional state")

        distortions = thematic_analysis.get('cognitive_distortions', [])
        if distortions:
            priority = f"Address cognitive distortion: {distortions[0].get('distortion_type', 'unknown')}"
        else:
            priority = "Continue current therapeutic approach with focus on identified themes"

        return {
            'tone_trajectory': tone,
            'takeaways': takeaways,
            'focus_area': priority,
            'duration': 'Standard session'
        }

    @staticmethod
    def format_thematic_deep_dive(thematic_analysis: Dict) -> Dict:
        return {
            'dominant_themes': [t['theme'] for t in thematic_analysis.get('dominant_themes', [])[:3]],
            'underlying_themes': [
                f"{t['theme']} - recurs {t['instances']} times"
                for t in thematic_analysis.get('recurring_themes', [])[:3]
            ],
            'pattern_detection': thematic_analysis.get('narrative_shifts', [])[:5],
            'cognitive_distortions': [
                d.get('distortion_type', 'unknown')
                for d in thematic_analysis.get('cognitive_distortions', [])[:3]
            ]
        }

    @staticmethod
    def format_emotional_mapping(sentiment_analysis: Dict, thematic_analysis: Dict) -> Dict:
        emotion_points = sentiment_analysis.get('emotion_points', [])
        shifts = sentiment_analysis.get('significant_shifts', [])

        key_shifts = []
        for shift in shifts[:3]:
            key_shifts.append(
                f"At {shift.get('to_time', 'unknown')}: "
                f"Emotional shift from {shift.get('from_emotion', '?')} "
                f"to {shift.get('to_emotion', '?')} (magnitude: {shift.get('magnitude', 0):.1f})"
            )

        predictors = []
        for distortion in thematic_analysis.get('cognitive_distortions', [])[:2]:
            predictors.append(
                f"{distortion.get('distortion_type', 'unknown')} pattern "
                f"tends to precede emotional shifts"
            )

        return {
            'key_shifts': key_shifts,
            'trajectory': emotion_points,
            'predictors': predictors,
            'stability': sentiment_analysis.get('summary', {}).get('emotional_stability', 'Unknown')
        }

    @staticmethod
    def generate_clinical_hypothesis(
        thematic_analysis: Dict,
        sentiment_analysis: Dict,
        emotional_trajectory: List[Dict]
    ) -> Dict:
        hypotheses = {
            'interventions': [],
            'approaches': [],
            'prompts': [],
            'follow_up': ''
        }

        distortion_to_intervention = {
            'Catastrophizing': 'Reality testing and probability estimation',
            'Overgeneralization': 'Generating alternative explanations and exceptions',
            'All-or-Nothing Thinking': 'Exploring middle ground and shades of gray',
            'Personalization': 'External locus of control exploration'
        }

        distortions = thematic_analysis.get('cognitive_distortions', [])
        for dist in distortions[:2]:
            dist_type = dist.get('distortion_type', '')
            if dist_type in distortion_to_intervention:
                hypotheses['interventions'].append(distortion_to_intervention[dist_type])

        themes = thematic_analysis.get('dominant_themes', [])
        if any('relationship' in t.get('theme', '').lower() for t in themes):
            hypotheses['approaches'].append('Attachment-focused interventions')
        if any('identity' in t.get('theme', '').lower() for t in themes):
            hypotheses['approaches'].append('Identity exploration and values clarification')

        if themes:
            theme = themes[0].get('theme', '')
            hypotheses['prompts'] = [
                f"How does your experience with {theme.lower()} connect to your core beliefs about yourself?",
                f"What would acceptance of your {theme.lower()} struggle look like?",
                f"Where do you see {theme.lower()} showing up in other areas of your life?"
            ]

        if emotional_trajectory:
            final_emotion = emotional_trajectory[-1].get('emotion', '')
            if final_emotion in ['anxious', 'frustrated']:
                hypotheses['follow_up'] = (
                    f"Begin next session by exploring the {final_emotion.lower()} feeling at session end"
                )

        return hypotheses

    @staticmethod
    def build_complete_report(
        session_id: str,
        patient_id: str,
        sentiment_analysis: Dict,
        thematic_analysis: Dict,
        turn_patterns: Dict,
        relational_analysis: Dict,
        emotional_trajectory: List[Dict]
    ) -> InsightReport:
        report = InsightReport(session_id, patient_id)

        exec_summary = ReportFormatter.generate_executive_summary(
            sentiment_analysis, thematic_analysis, emotional_trajectory
        )
        report.add_executive_summary(exec_summary)

        report.add_thematic_analysis(
            ReportFormatter.format_thematic_deep_dive(thematic_analysis)
        )

        report.add_emotional_mapping(
            ReportFormatter.format_emotional_mapping(sentiment_analysis, thematic_analysis)
        )

        report.add_clinical_hypothesis(
            ReportFormatter.generate_clinical_hypothesis(
                thematic_analysis, sentiment_analysis, emotional_trajectory
            )
        )

        alliance = relational_analysis.get('therapeutic_alliance', {})
        report.add_relational_dynamics({
            'alliance_rating': alliance.get('rating', 'Unknown'),
            'patterns': relational_analysis.get('speaker_profiles', {}),
            'power_dynamics': relational_analysis.get('power_dynamics', {}),
            'strengths': ['Collaborative engagement', 'Emotional responsiveness'],
            'improvements': []
        })

        report.add_clinical_recommendations({
            'immediate': ['Continue current approach', 'Monitor for escalation of identified distortions'],
            'next_session': exec_summary.get('focus_area', 'TBD'),
            'monitoring': ['Emotional stability trends', 'Cognitive pattern changes'],
            'red_flags': []
        })

        return report
