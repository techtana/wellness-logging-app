"""Thematic Extraction Module - identifies themes, narrative shifts, and cognitive distortions"""
import re
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, field
from enum import Enum


class CognitiveDistortion(Enum):
    CATASTROPHIZING = "Catastrophizing"
    OVERGENERALIZATION = "Overgeneralization"
    MIND_READING = "Mind Reading"
    EMOTIONAL_REASONING = "Emotional Reasoning"
    ALL_OR_NOTHING = "All-or-Nothing Thinking"
    MAGNIFICATION = "Magnification/Minimization"
    LABELING = "Labeling"
    PERSONALIZATION = "Personalization"
    SHOULD_STATEMENTS = "Should Statements"
    CONTROL_ISSUES = "Control Issues"


class ThemeType(Enum):
    DOMINANT = "Dominant"
    UNDERLYING = "Underlying"
    SHIFTING = "Shifting"
    RECURRING = "Recurring"


@dataclass
class ThemeEntry:
    theme: str
    type: ThemeType
    instances: int
    first_instance: str
    last_instance: str
    examples: List[str] = field(default_factory=list)
    severity: str = "Moderate"

    def to_dict(self) -> Dict:
        return {
            'theme': self.theme,
            'type': self.type.value,
            'instances': self.instances,
            'first_instance': self.first_instance,
            'last_instance': self.last_instance,
            'examples': self.examples,
            'severity': self.severity
        }


@dataclass
class NarrativeShift:
    timestamp: str
    previous_theme: str
    new_theme: str
    transition_type: str
    intensity: float

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'previous_theme': self.previous_theme,
            'new_theme': self.new_theme,
            'transition_type': self.transition_type,
            'intensity': round(self.intensity, 2)
        }


@dataclass
class CognitiveDistortionInstance:
    timestamp: str
    distortion_type: CognitiveDistortion
    severity: str
    context: str

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'distortion_type': self.distortion_type.value,
            'severity': self.severity,
            'context': self.context
        }


class ThematicExtractor:
    """Extracts and analyzes themes in clinical transcripts"""

    def __init__(self):
        self.theme_keywords = {
            'Work': ['work', 'job', 'career', 'office', 'boss', 'coworker', 'meeting', 'deadline'],
            'Relationships': ['partner', 'spouse', 'friend', 'family', 'dating', 'marriage'],
            'Health': ['health', 'doctor', 'hospital', 'symptom', 'pain', 'medication'],
            'Family': ['parent', 'child', 'sibling', 'mother', 'father', 'grandparent'],
            'Money': ['money', 'financial', 'budget', 'debt', 'paycheck', 'cost'],
            'Spirituality': ['faith', 'belief', 'god', 'purpose', 'meaning', 'spiritual'],
            'Identity': ['who', 'person', 'identity', 'self', 'values', 'beliefs']
        }

        self.distortion_patterns = {
            CognitiveDistortion.CATASTROPHIZING: [
                r'\b(worst case|disaster|devastating|unbearable|horrific)\b',
                r'\b(everything will fall apart)\b'
            ],
            CognitiveDistortion.OVERGENERALIZATION: [
                r'\b(always|never|every time|all the time)\b',
                r'\b(I always|I never)\b'
            ],
            CognitiveDistortion.MIND_READING: [
                r'\b(they are thinking|they feel|they must|they wouldn\'t)\b',
                r'\b(he is|she is)\b'
            ],
            CognitiveDistortion.EMOTIONAL_REASONING: [
                r'\b(I feel like|I am sure|gut feeling|feels like)\b',
                r'\b(what I feel is true)\b'
            ],
            CognitiveDistortion.ALL_OR_NOTHING: [
                r'\b(completely|totally|perfect|failure|success)\b',
                r'\b(good or bad|happy or sad)\b'
            ],
            CognitiveDistortion.MAGNIFICATION: [
                r'\b(so small|tiny|huge|massive|enormous)\b',
                r'\b(terrible|awful|horrifying)\b'
            ],
            CognitiveDistortion.LABELING: [
                r'\b(a failure|a loser|a fool|an idiot|an imposter)\b',
                r'\b(a jerk|a mess|a burden)\b'
            ],
            CognitiveDistortion.PERSONALIZATION: [
                r'\b(it\'s my fault|I caused|I should have)\b',
                r'\b(they did it because of me)\b'
            ],
            CognitiveDistortion.SHOULD_STATEMENTS: [
                r'\b(I should|you should|we should|they should)\b',
                r'\b(had to|must|need to|ought to)\b'
            ],
            CognitiveDistortion.CONTROL_ISSUES: [
                r'\b(need to control|can\'t stand it if|can\'t tolerate)\b',
                r'\b(feels like I have no choice)\b'
            ]
        }

    def identify_themes(self, transcript: List[Dict]) -> List[ThemeEntry]:
        """Identify dominant and recurring themes in the transcript"""
        if not transcript:
            return []

        theme_occurrences = {}

        for i, entry in enumerate(transcript):
            text = entry.get('text', '').lower()

            for theme, keywords in self.theme_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        theme_key = f"{theme}:{keyword}"
                        if theme_key not in theme_occurrences:
                            theme_occurrences[theme_key] = {
                                'theme': theme,
                                'first_instance': i,
                                'last_instance': i,
                                'examples': [],
                                'instances': 0
                            }

                        theme_occurrences[theme_key]['instances'] += 1
                        theme_occurrences[theme_key]['last_instance'] = i
                        if len(theme_occurrences[theme_key]['examples']) < 3:
                            theme_occurrences[theme_key]['examples'].append(text[:50])

        themes = []
        for theme_key, data in theme_occurrences.items():
            theme_type = self._classify_theme_type(data['instances'], len(transcript))
            themes.append(ThemeEntry(
                theme=data['theme'],
                type=theme_type,
                instances=data['instances'],
                first_instance=str(data['first_instance']),
                last_instance=str(data['last_instance']),
                examples=data['examples']
            ))

        themes.sort(key=lambda x: x.instances, reverse=True)
        return themes[:10]  # Top 10 themes

    def _classify_theme_type(self, instances: int, total: int) -> ThemeType:
        """Classify theme type based on occurrence frequency"""
        frequency = instances / max(1, total)
        if frequency > 0.3:
            return ThemeType.DOMINANT
        elif frequency > 0.1:
            return ThemeType.RECURRING
        elif frequency > 0.05:
            return ThemeType.SHIFTING
        else:
            return ThemeType.UNDERLYING

    def identify_narrative_shifts(self, transcript: List[Dict]) -> List[NarrativeShift]:
        """Identify significant narrative shifts in the session"""
        if len(transcript) < 2:
            return []

        shifts = []
        shift_markers = ['but', 'however', 'actually', 'instead', 'really', 'wait', 'oh', 'honestly']

        for i in range(1, len(transcript)):
            prev_text = transcript[i - 1].get('text', '').lower()
            curr_text = transcript[i].get('text', '').lower()

            prev_topics = set(word for word in prev_text.split() if len(word) > 4)
            curr_topics = set(word for word in curr_text.split() if len(word) > 4)

            if prev_topics and curr_topics:
                overlap = len(prev_topics.intersection(curr_topics)) / max(len(prev_topics), len(curr_topics))
            else:
                overlap = 1.0

            has_shift_marker = any(marker in curr_text for marker in shift_markers)

            if overlap < 0.3 and has_shift_marker:
                prev_theme = self._infer_theme(prev_text)
                curr_theme = self._infer_theme(curr_text)

                timestamp = transcript[i].get('timestamp') or transcript[i].get('time', str(i))

                shifts.append(NarrativeShift(
                    timestamp=str(timestamp),
                    previous_theme=prev_theme,
                    new_theme=curr_theme,
                    transition_type="Abrupt" if overlap < 0.1 else "Gradual",
                    intensity=min(100, 50 + (len(prev_topics - curr_topics) * 5))
                ))

        return shifts

    def identify_cognitive_distortions(self, transcript: List[Dict]) -> List[CognitiveDistortionInstance]:
        """Identify cognitive distortions in client speech"""
        distortions = []

        for entry in transcript:
            if entry.get('speaker', '').lower() == 'client':
                text = entry.get('text', '').lower()
                timestamp = entry.get('timestamp') or entry.get('time', '0')

                for distortion, patterns in self.distortion_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, text, re.IGNORECASE):
                            intensity_markers = ['absolutely', 'completely', 'totally']
                            severity = "High" if any(m in text for m in intensity_markers) else "Moderate"

                            distortions.append(CognitiveDistortionInstance(
                                timestamp=str(timestamp),
                                distortion_type=distortion,
                                severity=severity,
                                context=text[:100]
                            ))
                            break

        return distortions

    def _infer_theme(self, text: str) -> str:
        """Infer theme from text"""
        for theme, keywords in self.theme_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return theme
        return "General"

    def analyze_themes(self, transcript: List[Dict]) -> Dict:
        """Main analysis method"""
        themes = self.identify_themes(transcript)
        shifts = self.identify_narrative_shifts(transcript)
        distortions = self.identify_cognitive_distortions(transcript)

        dominant_themes = [t for t in themes if t.type == ThemeType.DOMINANT]
        recurring_themes = [t for t in themes if t.type == ThemeType.RECURRING]

        distortion_summary = {}
        for dist in distortions:
            dist_type = dist.distortion_type.value
            if dist_type not in distortion_summary:
                distortion_summary[dist_type] = {'count': 0, 'severity': []}
            distortion_summary[dist_type]['count'] += 1
            distortion_summary[dist_type]['severity'].append(dist.severity)

        return {
            'themes': [t.to_dict() for t in themes],
            'dominant_themes': [t.to_dict() for t in dominant_themes],
            'recurring_themes': [t.to_dict() for t in recurring_themes],
            'narrative_shifts': [s.to_dict() for s in shifts],
            'cognitive_distortions': [d.to_dict() for d in distortions],
            'distortion_summary': distortion_summary,
            'analysis_timestamp': datetime.now().isoformat()
        }
