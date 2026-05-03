import re
from typing import List, Dict

class FeedbackLoopAnalyzer:
    def __init__(self):
        self.positive_feedback_patterns = [
            r'\b(i see what you mean|that makes sense|good point)\b',
            r'\b(excellent|fantastic|wonderful)\b',
            r'\b(i appreciate|thank you|thanks for)\b',
            r'\b(yeah|exactly|right on)\b',
            r'\b(thats true|indeed|youre absolutely right)\b'
        ]
        self.negative_feedback_patterns = [
            r'\b(disagree|i disagree|ive never seen it that way)\b',
            r'\b(hmm|uh-huh|yeah but)\b',
            r'\b(unfortunately|however|nevertheless)\b',
            r'\b(i think not|no way|im not sure)\b',
            r'\b(but|i dont know|that doesnt help)\b'
        ]
        self.emotional_states = ['happy', 'sad', 'angry', 'confused', 'excited', 'frustrated', 'calm', 'anxious']
        self.conversation_state = 'positive'

    def analyze_feedback_loops(self, transcript: List[Dict]) -> Dict:
        """
        Analyze the presence of positive or negative feedback loops in the conversation.
        
        Args:
        - transcript (List[Dict]): Transcription data with speaker and text information
        
        Returns:
        - A dictionary containing the analysis results
        """
        if not transcript:
            return {}

        # Analyze positive and negative feedback loops
        positive_loop = False
        negative_loop = False

        # Iterate through each line in the transcript
        for i, entry in enumerate(transcript):
            speaker = entry.get('speaker', '')
            text = entry.get('text', '')

            # Detect positive feedback loops
            if self._detect_positive_feedback(text):
                positive_loop = True

            # Detect negative feedback loops
            if self._detect_negative_feedback(text):
                negative_loop = True

            # Detect emotional states
            emotion = self._detect_emotion(text)
            if emotion:
                self.conversation_state = emotion

        return {
            'positive_feedback_detected': positive_loop,
            'negative_feedback_detected': negative_loop,
            'current_emotional_state': self.conversation_state
        }

    def _detect_positive_feedback(self, text: str) -> bool:
        """
        Detect positive feedback patterns in the given text.
        
        Args:
        - text (str): Text to analyze for positive feedback
        
        Returns:
        - True if positive feedback is detected, False otherwise
        """
        for pattern in self.positive_feedback_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_negative_feedback(self, text: str) -> bool:
        """
        Detect negative feedback patterns in the given text.
        
        Args:
        - text (str): Text to analyze for negative feedback
        
        Returns:
        - True if negative feedback is detected, False otherwise
        """
        for pattern in self.negative_feedback_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_emotion(self, text: str) -> str:
        """
        Detect the dominant emotion in the given text.
        
        Args:
        - text (str): Text to analyze for emotions
        
        Returns:
        - The detected emotion, or 'neutral' if no emotion is detected
        """
        emotion_map = {}
        for emotion in self.emotional_states:
            pattern = rf'\b{emotion}\b'
            count = len(re.findall(pattern, text, re.IGNORECASE))
            if count > 0:
                emotion_map[emotion] = count
            # Also check for related adjectives
            related = {
                'happy': ['joyful', 'elated', 'grateful'],
                'sad': ['depressed', 'unhappy'],
                'angry': ['frustrated', 'irritated'],
                'anxious': ['fearful', 'apprehensive', 'worried'],
                'excited': ['thrilled', 'enthusiastic'],
                'calm': ['relaxed', 'peaceful'],
                'confused': ['bewildered', 'perplexed'],
            }
            for adj in related.get(emotion, []):
                count = len(re.findall(rf'\b{adj}\b', text, re.IGNORECASE))
                if count > 0:
                    emotion_map[emotion] = emotion_map.get(emotion, 0) + count
        if emotion_map:
            return max(emotion_map, key=emotion_map.get)
        return 'neutral'