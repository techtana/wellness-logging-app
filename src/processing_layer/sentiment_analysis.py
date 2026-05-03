"""Sentiment & Emotion Analysis Module"""
import re
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, field
from enum import Enum


class Emotion(Enum):
    ANXIOUS = "Anxious"
    DEPRESSED = "Depressed"
    FRUSTRATED = "Frustrated"
    HOPEFUL = "Hopeful"
    HAPPY = "Happy"
    ANGRY = "Angry"
    WORRIED = "Worried"
    CONFUSED = "Confused"
    CALM = "Calm"
    EMBARRASSED = "Embarrassed"


@dataclass
class EmotionPoint:
    timestamp: str
    emotion: Emotion
    intensity: float
    context: str = ""
    triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'emotion': self.emotion.value,
            'intensity': round(self.intensity, 2),
            'context': self.context,
            'triggers': self.triggers
        }


class SentimentAnalyzer:
    """Analyzes sentiment and emotional patterns in clinical transcripts"""

    def __init__(self):
        self.emotion_indicators = {
            Emotion.ANXIOUS: [
                r'\b(fearful|worried|scared|nervous|uneasy)\b',
                r'\b(panic|dread|terror|apprehension)\b',
                r'\b(jumpy|on edge|tense|stressed)\b'
            ],
            Emotion.DEPRESSED: [
                r'\b(sad|depressed|down|blue|miserable)\b',
                r'\b(hollow|empty|numb|drained)\b',
                r'\b(heartbroken|grief|loss|bereaved)\b'
            ],
            Emotion.FRUSTRATED: [
                r'\b(angry|mad|upset|fed up)\b',
                r'\b(irritated|exasperated|disgusted)\b',
                r'\b(annoyed|vexed|resentful)\b'
            ],
            Emotion.HOPEFUL: [
                r'\b(optimistic|hopeful|positive|upbeat)\b',
                r'\b(inspired|motivated|confident)\b',
                r'\b(recovered|healed|improved)\b'
            ],
            Emotion.HAPPY: [
                r'\b(happy|joyful|excited|pleased)\b',
                r'\b(content|satisfied|blessed)\b',
                r'\b(grateful|thankful|lucky)\b'
            ],
            Emotion.ANGRY: [
                r'\b(rage|furious|enraged|livid)\b',
                r'\b(bitter|vengeful|hostile)\b',
                r'\b(reckless|rebellious)\b'
            ],
            Emotion.WORRIED: [
                r'\b(concerned|preoccupied)\b',
                r'\b(anxious|uneasy)\b',
                r'\b(disturbed|troubled|upset)\b'
            ],
            Emotion.CONFUSED: [
                r'\b(lost|uncertain)\b',
                r'\b(perplexed|baffled|puzzled)\b',
                r'\b(dazed|distracted)\b'
            ],
            Emotion.CALM: [
                r'\b(relaxed|peaceful|serene)\b',
                r'\b(at peace|centered|balanced)\b',
                r'\b(composed|collected|controlled)\b'
            ],
            Emotion.EMBARRASSED: [
                r'\b(shy|awkward|clumsy)\b',
                r'\b(hesitant|reluctant|bashful)\b',
                r'\b(ashamed|self-conscious)\b'
            ]
        }

    def analyze_segment(self, text: str, timestamp: str) -> EmotionPoint:
        """Analyze a single text segment and detect emotions"""
        detected_emotions = {}

        for emotion, patterns in self.emotion_indicators.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    intensity = min(100, len(matches) * 25)

                    intensity_markers = ['very', 'extremely', 'terribly', 'absolutely', 'incredibly']
                    for marker in intensity_markers:
                        if marker in text.lower():
                            intensity = min(100, intensity + 15)
                            break

                    detected_emotions[emotion.value] = {
                        'intensity': intensity,
                        'triggers': list(set(matches))
                    }

        if not detected_emotions:
            return EmotionPoint(
                timestamp=timestamp,
                emotion=Emotion.CALM,
                intensity=10,
                context="Neutral conversation"
            )

        dominant_emotion = max(detected_emotions.items(), key=lambda x: x[1]['intensity'])
        context = f"Segment at {timestamp}: {text[:100]}..."

        return EmotionPoint(
            timestamp=timestamp,
            emotion=Emotion[dominant_emotion[0].upper().replace(' ', '_')],
            intensity=dominant_emotion[1]['intensity'],
            context=context,
            triggers=dominant_emotion[1]['triggers']
        )

    def track_emotional_trajectory(self, transcript: List[Dict]) -> List[EmotionPoint]:
        """Track emotional shifts throughout an entire session"""
        emotion_points = []

        for entry in transcript:
            timestamp = entry.get('timestamp') or entry.get('time', datetime.now().strftime('%H:%M'))
            text = entry.get('text', '')

            if text:
                emotion_point = self.analyze_segment(text, str(timestamp))
            else:
                emotion_point = EmotionPoint(
                    timestamp=str(timestamp),
                    emotion=Emotion.CALM,
                    intensity=10
                )

            emotion_points.append(emotion_point)

        return emotion_points

    def identify_emotional_shifts(self, emotion_points: List[EmotionPoint]) -> List[Dict]:
        """Identify significant emotional shifts in the session"""
        shifts = []

        for i in range(1, len(emotion_points)):
            prev = emotion_points[i - 1]
            curr = emotion_points[i]

            intensity_change = curr.intensity - prev.intensity
            emotion_changed = curr.emotion.value != prev.emotion.value

            if intensity_change >= 15 or intensity_change <= -15 or emotion_changed:
                shifts.append({
                    'from_time': prev.timestamp,
                    'from_emotion': prev.emotion.value,
                    'from_intensity': prev.intensity,
                    'to_time': curr.timestamp,
                    'to_emotion': curr.emotion.value,
                    'to_intensity': curr.intensity,
                    'shift_direction': 'increase' if intensity_change > 0 else 'decrease',
                    'magnitude': abs(intensity_change)
                })

        return shifts

    def generate_sentiment_summary(self, emotion_points: List[EmotionPoint]) -> Dict:
        """Generate overall sentiment summary"""
        if not emotion_points:
            return {
                'overall_sentiment': 'Neutral',
                'average_intensity': 0,
                'emotional_stability': 'Unknown',
                'key_shifts': []
            }

        total_intensity = sum(ep.intensity for ep in emotion_points)
        avg_intensity = total_intensity / len(emotion_points)

        emotion_counts = {}
        for ep in emotion_points:
            emotion = ep.emotion.value
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]

        shifts = self.identify_emotional_shifts(emotion_points)
        high_volatility = len(shifts) > (len(emotion_points) * 0.3)

        stability = 'High Volatility' if high_volatility else 'Moderate Stability' if shifts else 'Stable'

        return {
            'overall_sentiment': dominant_emotion,
            'average_intensity': round(avg_intensity, 1),
            'emotional_stability': stability,
            'emotion_distribution': emotion_counts,
            'key_shifts': shifts[:5],
            'assessment': f"Patient shows {dominant_emotion.lower()} emotions with {stability}"
        }

    def analyze_emotions(self, transcript: List[Dict]) -> Dict:
        """Main analysis method"""
        emotion_points = self.track_emotional_trajectory(transcript)
        summary = self.generate_sentiment_summary(emotion_points)
        shifts = self.identify_emotional_shifts(emotion_points)

        return {
            'emotion_points': [ep.to_dict() for ep in emotion_points],
            'summary': summary,
            'significant_shifts': shifts,
            'analysis_timestamp': datetime.now().isoformat()
        }
