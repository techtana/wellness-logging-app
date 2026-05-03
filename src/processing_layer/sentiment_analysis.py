"""
Sentiment & Emotion Analysis Module
Detects emotional shifts and intensity in clinical conversations
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

class Emotion(Enum):
    ANXIOUS = "Anxious"
    DEPRESSION = "Depressed"
    FRUSTRATION = "Frustrated"
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
    intensity: float  # 0-100 scale
    context: str = ""
    triggers: List[str] = field(default_factory=list)

@dataclass
class SentimentTrend:
    start_time: str
    end_time: str
    overall_sentiment: str
    intensity_range: Tuple[float, float]

class SentimentAnalyzer:
    """Analyzes sentiment and emotional patterns in clinical transcripts"""
    
    def __init__(self):
        self.emotion_indicators = {
            Emotion.ANXIOUS: [
                r'\b(fearful|worried|scared|nervous|uneasy)\b',
                r'\b(panic|dread|terror|apprehension)\b',
                r'\b(jumpy|on edge|tense|stressed)\b'
            ],
            Emotion.DEPRESSION: [
                r'\b(sad|depressed|down|blue|miserable)\b',
                r'\b(hollow|empty|numb|drained)\b',
                r'\b(heartbroken|grief|loss|bereaved)\b'
            ],
            Emotion.FRUSTATED: [
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
                r'\b(reckless|reckless|rebellious)\b'
            ],
            Emotion.WORRIED: [
                r'\b(concerned|concerned|preoccupied)\b',
                r'\b(anxious|uneasy|uneasy)\b',
                r'\b(disturbed|troubled|upset)\b'
            ],
            Emotion.CONFUSED: [
                r'\b(lost|lost|uncertain)\b',
                r'\b(perplexed|baffled|puzzled)\b',
                r'\b(dazed|dazed|distracted)\b'
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
        
        # Check for each emotion's indicators
        for emotion, patterns in self.emotion_indicators.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Calculate intensity based on word frequency and intensity markers
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    intensity = min(100, len(matches) * 25)  # Base intensity
                    
                    # Boost intensity with intensity markers
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
            # Default to neutral if no strong emotions detected
            return EmotionPoint(
                timestamp=timestamp,
                emotion=Emotion.CALM,
                intensity=10,
                context="Neutral conversation"
            )
        
        # Determine dominant emotion
        dominant_emotion = max(detected_emotions.items(), key=lambda x: x[1]['intensity'])
        
        # Build context
        context = f"Segment at {timestamp}: {text[:100]}..."
        
        return EmotionPoint(
            timestamp=timestamp,
            emotion=Emotion([e for e in Emotion if e.value == dominant_emotion[0]][0]),
            intensity=dominant_emotion[1]['intensity'],
            context=context,
            triggers=dominant_emotion[1]['triggers']
        )
    
    def track_emotional_trajectory(self, transcript: List[Dict]) -> List[EmotionPoint]:
        """Track emotional shifts throughout an entire session"""
        emotion_points = []
        
        for entry in transcript:
            # Extract timestamp
            if 'time' in entry:
                timestamp = entry['time']
            else:
                timestamp = datetime.now().strftime('%H:%M')
            
            # Process text
            if 'text' in entry:
                emotion_point = self.analyze_segment(entry['text'], timestamp)
            else:
                emotion_point = EmotionPoint(
                    timestamp=timestamp,
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
            
            # Calculate shift
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
        
        # Calculate metrics
        total_intensity = sum(ep.intensity for ep in emotion_points)
        avg_intensity = total_intensity / len(emotion_points)
        
        # Identify most common emotion
        emotion_counts = {}
        for ep in emotion_points:
            emotion = ep.emotion.value
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        
        # Assess emotional stability
        shifts = self.identify_emotional_shifts(emotion_points)
        high_volatility = len(shifts) > (len(emotion_points) * 0.3)
        
        stability_assessment = {
            'stable': 'Stable',
            'moderate': 'Moderate',
            'high': 'High'
        }
        
        return {
            'overall_sentiment': dominant_emotion,
            'average_intensity': round(avg_intensity, 1),
            'emotional_stability': stability_assessment.get('high' if high_volatility else 'moderate' if len(shifts) > len(emotion_points) * 0.1 else 'stable', 'stable'),
            'emotion_distribution': emotion_counts,
            'key_shifts': shifts[:5],  # Top 5 shifts
            'assessment': f"Patient shows {dominant_emotion.lower()} emotions with {stability_assessment.get('high' if high_volatility else 'moderate' if len(shifts) > len(emotion_points) * 0.1 else 'stable', 'stable')} emotional stability"
        }

# Main function to analyze session
def analyze_session(transcript: List[Dict]) -> Dict:
    """Main function to analyze clinical session"""
    analyzer = SentimentAnalyzer()
    
    # Track emotions throughout session
    emotion_points = analyzer.track_emotional_trajectory(transcript)
    
    # Generate summary
    summary = analyzer.generate_sentiment_summary(emotion_points)
    
    # Identify shifts
    shifts = analyzer.identify_emotional_shifts(emotion_points)
    
    return {
        'emotion_points': emotion_points,
        'summary': summary,
        'significant_shifts': shifts,
        'analysis_timestamp': datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Example usage
    sample_transcript = [
        {'time': '09:00', 'text': 'I feel so anxious about coming here today.'},
        {'time': '09:05', 'text': 'But talking to you helps calm me down.'},
        {'time': '09:15', 'text': 'I think I might finally get through this.'},
        {'time': '09:20', 'text': 'Sometimes I feel so worried about the future.'}
    ]
    
    result = analyze_session(sample_transcript)
    print("Sentiment Analysis Complete")
    print(f"Overall: {result['summary']['overall_sentiment']}")
    print(f"Stability: {result['summary']['emotional_stability']}")
    print(f"Intensity: {result['summary']['average_intensity']}")
    print(f"Significant shifts: {len(result['significant_shifts'])}")