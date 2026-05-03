from typing import List, Dict

class ClinicalSignificance:
    def __init__(self):
        # Define thresholds for clinical significance
        self.thresholds = {
            'positive_resonance': 60.0,
            'negative_resonance': 20.0,
            'pauses': 10,
            'overlaps': 3,
            'rapid_responses': 15,
            'silence_gaps': 5,
            'positive_feedback': True,
            'negative_feedback': False
        }

    def evaluate_clinical_significance(self, transcript: List[Dict], emotion_analysis: Dict, turn_patterns: Dict, feedback_analysis: Dict) -> Dict:
        """
        Evaluate the clinical significance of the conversation.
        
        Args:
        - transcript (List[Dict]): Transcription data
        - emotion_analysis (Dict): Results from emotional_resonance analysis
        - turn_patterns (Dict): Results from turn_pattern_analyzer
        - feedback_analysis (Dict): Results from feedback_loop_analyzer
        
        Returns:
        - A dictionary containing the clinical significance evaluation
        """
        if not transcript:
            return {}

        # Evaluate emotional resonance
        positive_resonance = emotion_analysis.get('positive_resonance', 0)
        negative_resonance = emotion_analysis.get('negative_resonance', 0)

        # Evaluate turn patterns
        pauses = turn_patterns.get('pauses', 0)
        overlaps = turn_patterns.get('overlaps', 0)
        rapid_responses = turn_patterns.get('rapid_responses', 0)
        silence_gaps = turn_patterns.get('silence_gaps', 0)

        # Evaluate feedback loops
        positive_feedback = feedback_analysis.get('positive_feedback_detected', False)
        negative_feedback = feedback_analysis.get('negative_feedback_detected', False)

        # Evaluate clinical significance
        emotional_connection = self._evaluate_emotional_connection(positive_resonance, negative_resonance)
        interaction_dynamics = self._evaluate_interaction_dynamics(turn_patterns, pauses, overlaps)
        feedback_dynamics = self._evaluate_feedback_dynamics(feedback_analysis)

        return {
            'emotional_connection': emotional_connection,
            'interaction_dynamics': interaction_dynamics,
            'feedback_dynamics': feedback_dynamics,
            'overall_assessment': self._synthesize_assessment(
                emotional_connection, interaction_dynamics, feedback_dynamics
            )
        }

    def _evaluate_emotional_connection(self, positive: float, negative: float) -> Dict:
        """
        Evaluate the emotional connection between client and therapist.
        
        Args:
        - positive (float): Positive resonance score
        - negative (float): Negative resonance score
        
        Returns:
        - A dictionary containing the emotional connection evaluation
        """
        score = positive - negative
        if score >= self.thresholds['positive_resonance']:
            assessment = 'Strong'
            insight = 'High emotional resonance indicates a secure therapeutic alliance.'
        elif score >= 0:
            assessment = 'Moderate'
            insight = 'Moderate emotional resonance suggests a developing therapeutic alliance.'
        else:
            assessment = 'Low'
            insight = 'Low emotional resonance may indicate a need for alliance strengthening.'

        return {
            'assessment': assessment,
            'score': round(score, 2),
            'insight': insight
        }

    def _evaluate_interaction_dynamics(self, turn_patterns: Dict, pauses: int, overlaps: int) -> Dict:
        """
        Evaluate the interaction dynamics in the conversation.
        
        Args:
        - turn_patterns (Dict): Turn pattern data
        - pauses (int): Number of pauses
        - overlaps (int): Number of overlaps
        
        Returns:
        - A dictionary containing the interaction dynamics evaluation
        """
        pauses = turn_patterns.get('pauses', pauses)
        overlaps = turn_patterns.get('overlaps', overlaps)

        if pauses <= self.thresholds['pauses'] and overlaps <= self.thresholds['overlaps']:
            assessment = 'Fluid'
            insight = 'Smooth interaction with balanced turn-taking.'
        elif pauses > self.thresholds['pauses'] and overlaps > self.thresholds['overlaps']:
            assessment = 'Disjointed'
            insight = 'Disjointed interaction suggests communication barriers or anxiety.'
        else:
            assessment = 'Mixed'
            insight = 'Mixed interaction patterns indicate areas for communication improvement.'

        return {
            'assessment': assessment,
            'insight': insight
        }

    def _evaluate_feedback_dynamics(self, feedback_analysis: Dict) -> Dict:
        """
        Evaluate the feedback dynamics in the conversation.
        
        Args:
        - feedback_analysis (Dict): Feedback loop analysis results
        
        Returns:
        - A dictionary containing the feedback dynamics evaluation
        """
        positive_feedback = feedback_analysis.get('positive_feedback_detected', False)
        negative_feedback = feedback_analysis.get('negative_feedback_detected', False)

        if positive_feedback and not negative_feedback:
            assessment = 'Supportive'
            insight = 'Client receives consistent positive validation, reinforcing engagement.'
        elif not positive_feedback and negative_feedback:
            assessment = 'Challenging'
            insight = 'Negative feedback loops may indicate resistance or misunderstanding.'
        else:
            assessment = 'Balanced'
            insight = 'Mixed feedback patterns suggest a nuanced therapeutic interaction.'

        return {
            'assessment': assessment,
            'insight': insight
        }

    def _synthesize_assessment(self, emotional_connection: Dict, interaction_dynamics: Dict, feedback_dynamics: Dict) -> Dict:
        """
        Synthesize the overall clinical assessment.
        
        Args:
        - emotional_connection (Dict): Emotional connection evaluation
        - interaction_dynamics (Dict): Interaction dynamics evaluation
        - feedback_dynamics (Dict): Feedback dynamics evaluation
        
        Returns:
        - A dictionary containing the overall clinical assessment
        """
        # Determine overall assessment level
        assessments = [emotional_connection['assessment'], interaction_dynamics['assessment'], feedback_dynamics['assessment']]
        assessment_counts = {}
        for assessment in assessments:
            assessment_counts[assessment] = assessment_counts.get(assessment, 0) + 1
        overall_assessment = max(assessment_counts, key=assessment_counts.get)

        # Generate insights
        insights = []
        insights.extend([emotional_connection['insight'], interaction_dynamics['insight'], feedback_dynamics['insight']])
        overall_insight = ' '.join([insight for insight in insights if insight])

        return {
            'overall_assessment': overall_assessment,
            'insight': overall_insight
        }