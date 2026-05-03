import re

class EmotionalResonance:
    def __init__(self):
        self.emotion_indicators = {
            'Positive': [
                r'\b(happy|joyful|elated)\\b',
                r'\b(grateful|appreciative|humbled)\\b',
                r'\b(optimistic|hopeful|encouraged)\\b'
            ],
            'Negative': [
                r'\b(sad|depressed|unhappy)\\b',
                r'\b(angry|frustrated|irritated)\\b',
                r'\b(fearful|anxious|apprehensive)\\b'
            ]
        }

    def analyze_emotional_resonance(self, transcript: List[Dict]) -> Dict:
        """
        Analyze emotional resonance between therapist and client.
        
        Args:
        - transcript (List[Dict]): Transcription data with speaker, time, and text information
        
        Returns:
        - A dictionary containing the emotional resonance analysis results
        """
        if not transcript:
            return {}

        # Initialize counters for positive and negative emotions
        positive_emotions = 0
        negative_emotions = 0

        # Iterate through each line in the transcript
        for entry in transcript:
            speaker = entry.get('speaker', '')
            text = entry.get('text', '')

            # Check if the speaker is the client or therapist
            if speaker.lower() == 'client':
                client_text = text.lower()
                client_emotions = self._count_emotions(client_text)

                # Update positive and negative emotion counters
                positive_emotions += client_emotions['positive']
                negative_emotions += client_emotions['negative']

        # Calculate emotional resonance scores
        positive_resonance = (positive_emotions / max(1, len(transcript))) * 100
        negative_resonance = (negative_emotions / max(1, len(transcript))) * 100

        return {
            'positive_resonance': round(positive_resonance, 2),
            'negative_resonance': round(negative_resonance, 2)
        }

    def _count_emotions(self, text: str) -> Dict:
        """
        Count the number of positive and negative emotions in a given text.
        
        Args:
        - text (str): Text to analyze for emotions
        
        Returns:
        - A dictionary containing the count of positive and negative emotions
        """
        positive_count = 0
        negative_count = 0

        # Iterate through each indicator pattern
        for emotion_type, patterns in self.emotion_indicators.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    if emotion_type == 'Positive':
                        positive_count += 1
                    else:
                        negative_count += 1

        return {
            'positive': positive_count,
            'negative': negative_count
        }