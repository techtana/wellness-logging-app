"""
Thematic Extraction Module
Identifies recurring themes, narrative shifts, and cognitive distortions
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple
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

@dataclass
class NarrativeShift:
    timestamp: str
    previous_theme: str
    new_theme: str
    transition_type: str
    intensity: float

@dataclass
class CognitiveDistortionInstance:
    timestamp: str
    distortion_type: CognitiveDistortion
    severity: str
    context: str

class ThematicExtractor:
    """Extracts and analyzes themes in clinical transcripts"""
    
    def __init__(self):
        # Pre-defined themes and their potential underlying meanings
        self.theme_mappings = {
            'Work': ['Job Satisfaction', 'Career Growth', 'Work-Life Balance', 'Professional Identity'],
            'Relationships': ['Intimacy', 'Communication', 'Trust Issues', 'Social Support'],
            'Health': ['Pain Management', 'Disease Process', 'Self-Care', 'Medical Trauma'],
            'Family': ['Parenting', 'Sibling Dynamics', 'Family History', 'Generational Patterns'],
            'Money': ['Financial Stress', 'Security', 'Value System', 'Consumer Behavior'],
            'Spirituality': ['Meaning', 'Purpose', 'Faith', 'Connection'],
            'Identity': ['Self-Concept', 'Values', 'Beliefs', 'Personal Growth'],
            'Trauma': ['PTSD', 'Flashbacks', 'Triggers', 'Safety Concerns']
        }
        
        # Cognitive distortion patterns
        self.distortion_patterns = {
            CognitiveDistortion.CATASTROPHIZING: [
                r'\b(worst case|disaster|devastating|unbearable|horrific)\b',
                r'\b(if this happens, it means)\b',
                r'\b(everything will fall apart)\b'
            ],
            CognitiveDistortion.OVERGENERALIZATION: [
                r'\b(always|never|every time|all the time|all people)\b',
                r'\b(people like|I always|I never)\b',
                r'\b(such people|they all|no one)\b'
            ],
            CognitiveDistortion.MIND_READING: [
                r'\b(they are|they feel|they think|they must)\b',
                r'\b(they wouldn\'t|they wouldn\'t want)\b',
                r'\b(he is|she is|it must be)\b'
            ],
            CognitiveDistortion.EMOTIONAL_REASONING: [
                r'\b(feeling is|I know|I feel like|I am sure)\b',
                r'\b(gut feeling|feels like|I have a feeling)\b',
                r'\b(what I feel is true)\b'
            ],
            CognitiveDistortion.ALL_OR_NOTHING: [
                r'\b(completely|totally|100%|perfect|failure)\b',
                r'\b(successful or fail|good or bad|happy or sad)\b',
                r'\b(either|or neither|one thing or the other)\b'
            ],
            CognitiveDistortion.MAGNIFICATION: [
                r'\b(so small|tiny|negligible|nothing)\b',
                r'\b(huge|massive|colossal|infinite)\b',
                r'\b(enormous|terrible|awful|horrifying)\b'
            ],
            CognitiveDistortion.LABELING: [
                r'\b(a failure|a loser|a slob)\b',
                r'\b(a fool|an idiot|an imposter)\b',
                r'\b(a jerk|a mess|a burden)\b'
            ],
            CognitiveDistortion.PERSONALIZATION: [
                r'\b(it\'s my fault|I caused|I should have)\b',
                r'\b(I did this|I am responsible for)\b',
                r'\b(they did it because of me)\b'
            ],
            CognitiveDistortion.SHOULD_STATEMENTS: [
                r'\b(I should|you should|we should|they should)\b',
                r'\b(had to|must|need to)\b',
                r'\b(ought to|supposed to|better\')\b'
            ],
            CognitiveDistortion.CONTROL_ISSUES: [
                r'\b(need to control|can\'t stand it if)\b',
                r'\b(feels like I have no choice)\b',
                r'\b(can\'t tolerate|can\'t deal with)\b'
            ]
        }
    
    def identify_themes(self, transcript: List[Dict], window_size: int = 10) -> List[ThemeEntry]:
        """
        Identify dominant and recurring themes in the transcript
        Uses a sliding window approach
        """
        if not transcript:
            return []
        
        # Preprocess transcript
        processed_text = []
        for entry in transcript:
            if 'text' in entry:
                processed_text.append(entry['text'].lower())
            else:
                processed_text.append("")
        
        # Identify potential themes using keyword matching
        theme_keywords = {
            'Work': ['work', 'job', 'career', 'office', 'boss', 'coworker', 'colleague', 'meeting', 'deadline', 'project'],
            'Relationships': ['partner', 'spouse', 'friend', 'family', 'friend', 'social', 'dating', 'marriage', 'relationship'],
            'Health': ['health', 'doctor', 'hospital', 'symptom', 'pain', 'medication', 'treatment', 'sick', 'illness'],
            'Family': ['parent', 'child', 'sibling', 'mother', 'father', 'grandparent', 'extended', 'heritage'],
            'Money': ['money', 'financial', 'budget', 'spending', 'savings', 'debt', 'paycheck', 'cost'],
            'Spirituality': ['faith', 'belief', 'god', 'purpose', 'meaning', 'spiritual', 'religious'],
            'Identity': ['who', 'person', 'identity', 'self', 'values', 'beliefs', 'hopes', 'goals']
        }
        
        # Detect themes with sliding window
        theme_occurrences = {}
        for i in range(len(processed_text)):
            window_start = max(0, i - window_size)
            window_end = min(len(processed_text), i + window_size)
            window_text = " ".join(processed_text[window_start:window_end])
            
            for theme, keywords in theme_keywords.items():
                for keyword in keywords:
                    if keyword in window_text:
                        theme_key = f"{theme}:{keyword}"
                        if theme_key not in theme_occurrences:
                            theme_occurrences[theme_key] = {
                                'theme': theme,
                                'first_instance': f"{window_start}",
                                'last_instance': f"{window_start}",
                                'examples': [],
                                'instances': 0
                            }
                        
                        theme_occurrences[theme_key]['instances'] += 1
                        theme_occurrences[theme_key]['examples'].append(f"{window_start}:{window_text[:50]}")
        
        # Convert to ThemeEntry objects
        themes = []
        for theme_key, data in theme_occurrences.items():
            theme_entry = ThemeEntry(
                theme=data['theme'],
                type=self._classify_theme_type(data['instances'], len(transcript)),
                instances=data['instances'],
                first_instance=data['first_instance'],
                last_instance=data['last_instance'],
                examples=data['examples'][:3]
            )
            themes.append(theme_entry)
        
        # Sort by instances
        themes.sort(key=lambda x: x.instances, reverse=True)
        
        return themes
    
    def classify_theme_type(self, instances: int, total: int) -> ThemeType:
        """Classify theme type based on occurrence frequency"""
        frequency = instances / total
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
        
        # Analyze each segment transition
        for i in range(1, len(transcript)):
            prev = transcript[i - 1]
            curr = transcript[i]
            
            prev_text = prev.get('text', '').lower()
            curr_text = curr.get('text', '').lower()
            
            # Detect shift markers
            shift_markers = [
                'but', 'however', 'actually', 'instead', 'really',
                'wait', 'oh', 'honestly', 'you know', 'I mean'
            ]
            
            prev_markers = sum(1 for m in shift_markers if m in prev_text)
            curr_markers = sum(1 for m in shift_markers if m in curr_text)
            
            # Detect topic change
            prev_topics = set(word for word in prev_text.split() if len(word) > 4)
            curr_topics = set(word for word in curr_text.split() if len(word) > 4)
            
            # Calculate overlap
            overlap = len(prev_topics.intersection(curr_topics)) / max(len(prev_topics), len(curr_topics))
            
            # Consider it a shift if low overlap and shift markers
            if overlap < 0.3 and (prev_markers > 1 or curr_markers > 1):
                prev_theme = self._infer_theme(prev_text)
                curr_theme = self._infer_theme(curr_text)
                
                shift = NarrativeShift(
                    timestamp=curr.get('time', datetime.now().strftime('%H:%M')),
                    previous_theme=prev_theme if prev_theme else "Unknown",
                    new_theme=curr_theme if curr_theme else "Unknown",
                    transition_type="Abrupt" if overlap < 0.1 else "Gradual",
                    intensity=min(100, 50 + (len(prev_topics - curr_topics) * 5))
                )
                shifts.append(shift)
        
        return shifts
    
    def identify_cognitive_distortions(self, transcript: List[Dict]) -> List[CognitiveDistortionInstance]:
        """Identify cognitive distortions in client speech"""
        distortions = []
        
        for entry in transcript:
            if 'text' not in entry:
                continue
            
            text = entry['text'].lower()
            
            for distortion, patterns in self.distortion_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text):
                        # Determine severity
                        intensity_markers = ['absolutely', 'completely', 'totally', 'utterly']
                        intensity_boost = sum(1 for m in intensity_markers if m in text)
                        
                        instance = CognitiveDistortionInstance(
                            timestamp=entry.get('time', datetime.now().strftime('%H:%M')),
                            distortion_type=distortion,
                            severity="High" if intensity_boost > 0 else "Moderate",
                            context=text[:100]
                        )
                        distortions.append(instance)
                        break  # Only record first match per distortion
        
        return distortions
    
    def _infer_theme(self, text: str) -> str:
        """Infer theme from text"""
        keywords = {
            'Work': ['work', 'job', 'career', 'office', 'boss', 'coworker'],
            'Relationships': ['partner', 'spouse', 'friend', 'family', 'dating'],
            'Health': ['health', 'doctor', 'hospital', 'symptom', 'pain'],
            'Family': ['parent', 'child', 'sibling', 'mother', 'father'],
            'Money': ['money', 'financial', 'budget', 'debt'],
            'Spirituality': ['faith', 'belief', 'god', 'purpose'],
            'Identity': ['who', 'person', 'identity', 'values']
        }
        
        for theme, keywords in keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return theme
        return "General"
    
    def generate_thematic_analysis(self, transcript: List[Dict]) -> Dict:
        """Generate comprehensive thematic analysis"""
        themes = self.identify_themes(transcript)
        shifts = self.identify_narrative_shifts(transcript)
        distortions = self.identify_cognitive_distortions(transcript)
        
        # Determine dominant themes
        dominant_themes = [t for t in themes if t.type == ThemeType.DOMINANT]
        recurring_themes = [t for t in themes if t.type == ThemeType.RECURRING]
        
        # Summarize distortions
        distortion_summary = {}
        for dist in distortions:
            dist_type = dist.distortion_type.value
            if dist_type not in distortion_summary:
                distortion_summary[dist_type] = {
                    'count': 0,
                    'severity': [],
                    'context': []
                }
            distortion_summary[dist_type]['count'] += 1
            distortion_summary[dist_type]['severity'].append(dist.severity)
            distortion_summary[dist_type]['context'].append(dist.context[:50])
        
        return {
            'themes': themes,
            'dominant_themes': dominant_themes,
            'recurring_themes': recurring_themes,
            'narrative_shifts': shifts,
            'cognitive_distortions': distortions,
            'distortion_summary': distortion_summary,
            'analysis_timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Example usage
    sample_transcript = [
        {'time': '09:00', 'text': 'I think I always mess everything up.'},
        {'time': '09:05', 'text': 'My boss never likes me.'},
        {'time': '09:10', 'text': 'If I fail at this job, I'll never succeed.'},
        {'time': '09:15', 'text': 'But I worked hard this time.'}
    ]
    
    extractor = ThematicExtractor()
    result = extractor.generate_thematic_analysis(sample_transcript)
    print("Thematic Analysis Complete")
    print(f"Themes: {[t.theme for t in result['themes']]}")
    print(f"Distortions: {[d.distortion_type.value for d in result['cognitive_distortions']]}")