"""
Relational Dynamics Mapping Module
Analyzes therapeutic alliance, communication patterns, and inter-speaker dynamics
"""

import re
import dataclasses
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

class CommunicationStyle(Enum):
    DIRECT = "Direct"
    PASSIVE = "Passive"
    AGGRESSIVE = "Aggressive"
    PASSIVE_AGGRESSIVE = "Passive-Aggressive"
    ASSERTIVE = "Assertive"
    AMBIVALENT = "Ambivalent"
    DEFENSIVE = "Defensive"

class InterpersonalDynamic(Enum):
    SUPPORTIVE = "Supportive"
    CONFLICTUAL = "Conflictual"
    COLLABORATIVE = "Collaborative"
    DISCONNECTED = "Disconnected"
    TRANSFERENTIAL = "Transferential"
    COUNTERTRANSFERENTIAL = "Counter-Transference"
    AUTHORITY_CHALLENGE = "Authority Challenge"

@dataclass
class CommunicationPoint:
    timestamp: str
    speaker: str
    style: CommunicationStyle
    intensity: float
    context: str = ""

@dataclass
class RelationalEvent:
    timestamp: str
    event_type: str
    speakers: List[str]
    intensity: float
    context: str
    clinical_significance: str = ""

@dataclass
class TherapeuticAlliance:
    timestamp: str
    rating: str
    components: Dict[str, float]

class RelationalDynamicsMapper:
    """Maps and analyzes relational dynamics in clinical sessions"""
    
    def __init__(self):
        # Communication style patterns
        self.style_indicators = {
            CommunicationStyle.DIRECT: [
                r'\b(direct|straightforward|honest|clear)\b',
                r'\b(to the point|cut to the chase)\b',
                r'\b(no beating around the bush)\b'
            ],
            CommunicationStyle.PASSIVE: [
                r'\b(apologetic|hesitant|timid)\b',
                r'\b(too quiet|won\'t say)\b',
                r'\b(afraid to|don\'t want to)\b'
            ],
            CommunicationStyle.AGGRESSIVE: [
                r'\b(angry|attack|destroy)\b',
                r'\b(never mind|whatever|doesn\'t matter)\b',
                r'\b(who are you to)\b'
            ],
            CommunicationStyle.PASSIVE_AGGRESSIVE: [
                r'\b(sarcastic|mocking|bitter)\b',
                r'\b(should\'ve|could\'ve|would\'ve)\b',
                r'\b(oh well|never mind|forget it)\b'
            ],
            CommunicationStyle.ASSERTIVE: [
                r'\b(firm but respectful|clear boundaries)\b',
                r'\b(honest but kind|truthful)\b',
                r'\b(need to say|important to)\b'
            ],
            CommunicationStyle.AMBIVALENT: [
                r'\b(maybe|maybe|I don\'t know)\b',
                r'\b(on one hand/on the other)\b',
                r'\b(conflicting|competing)\b'
            ],
            CommunicationStyle.DEFENSIVE: [
                r'\b(why me|unfair|impossible)\b',
                r'\b(couldn\'t|couldn\'t|wouldn\'t)\b',
                r'\b(there are|there is no)\b'
            ]
        }
        
        # Relational event patterns
        self.event_patterns = {
            'Positive Alliance': [
                r'\b(trust|safe|understood|validated)\b',
                r'\b(collaborative|working together|partnership)\b',
                r'\b(grateful|helpful|appreciate)\b'
            ],
            'Negative Alliance': [
                r'\b(mistrust|don\'t trust|not listening)\b',
                r'\b(resentment|feeling ignored|dismissed)\b',
                r'\b(unhelpful|wasted time)\b'
            ],
            'Conflict': [
                r'\b(agree to disagree|disagreement|difference)\b',
                r'\b(annoying|irritating|triggered)\b',
                r'\b(fighting|argument|fighting)\b'
            ],
            'Empathy': [
                r'\b(I understand|I hear you|makes sense)\b',
                r'\b(that sounds hard|that must be tough)\b',
                r'\b(what\'s more|I\'m here for you)\b'
            ],
            'Transference': [
                r'\b(like my mom/father|reminds me of)\b',
                r'\b(idealized|feels like)\b',
                r'\b(disappointing|abusive parent)\b'
            ]
        }
    
    def analyze_session_dynamics(self, transcript: List[Dict]) -> Dict:
        """
        Analyze session for relational dynamics and communication patterns
        """
        if not transcript:
            return {}
        
        # Analyze each speaker's communication style
        speaker_styles = self._map_speaker_communication(transcript)
        
        # Detect relational events
        events = self._detect_relational_events(transcript)
        
        # Assess therapeutic alliance
        alliance_assessment = self._assess_alliance(transcript)
        
        # Identify communication breakdowns
        breakdowns = self._identify_breakdowns(transcript)
        
        return {
            'speaker_profiles': speaker_styles,
            'relational_events': [dataclasses.asdict(e) for e in events],
            'therapeutic_alliance': dataclasses.asdict(alliance_assessment),
            'communication_breakdowns': breakdowns,
            'dominant_dynamic': self._determine_dominant_dynamic(transcript)
        }
    
    def _map_speaker_communication(self, transcript: List[Dict]) -> Dict[str, Dict]:
        """Map communication style for each speaker"""
        speakers = set(entry.get('speaker', 'Unknown') for entry in transcript)
        speaker_profiles = {}
        
        for speaker in speakers:
            speaker_texts = [entry['text'] for entry in transcript if entry.get('speaker') == speaker]
            text = " ".join(speaker_texts).lower()
            
            # Match communication style
            max_score = 0
            best_style = CommunicationStyle.AMBIVALENT  # Default
            
            for style, patterns in self.style_indicators.items():
                score = sum(1 for pattern in patterns if re.search(pattern, text))
                if score > max_score:
                    max_score = score
                    best_style = style
            
            # Calculate intensity
            text_length = len(text)
            intensity = min(100, (max_score / max(1, text_length/50)) * 100)
            
            speaker_profiles[speaker] = {
                'style': best_style.value,
                'intensity': intensity,
                'word_count': len(text.split()),
                'sample_phrases': [entry for entry in speaker_texts[:3]]
            }
        
        return speaker_profiles
    
    def _detect_relational_events(self, transcript: List[Dict]) -> List[RelationalEvent]:
        """Detect significant relational events"""
        events = []
        
        for i in range(len(transcript) - 1):
            prev = transcript[i]
            curr = transcript[i + 1]
            
            prev_text = prev.get('text', '').lower()
            curr_text = curr.get('text', '').lower()
            
            # Check for event patterns
            event_type = None
            intensity = 0
            
            for event_name, patterns in self.event_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, prev_text) or re.search(pattern, curr_text):
                        event_type = event_name
                        intensity = 20  # Base intensity
                        break
            
            # Check for direct address (relational markers)
            direct_address_count = len(re.findall(r'\b(you|we|us|our)\b', prev_text + curr_text))
            intensity += direct_address_count * 5
            
            # Check for emotion words
            emotion_words = ['feeling', 'feel', 'emotion', 'emotionally']
            intensity += sum(1 for word in emotion_words if word in prev_text + curr_text) * 10
            
            if event_type or intensity > 30:
                event = RelationalEvent(
                    timestamp=curr.get('time', datetime.now().strftime('%H:%M')),
                    event_type=event_type or "General Interaction",
                    speakers=[prev.get('speaker', 'Unknown'), curr.get('speaker', 'Unknown')],
                    intensity=intensity,
                    context=prev_text[:50] + " " + curr_text[:50]
                )
                events.append(event)
        
        return events
    
    def _assess_alliance(self, transcript: List[Dict]) -> TherapeuticAlliance:
        """Assess therapeutic alliance quality"""
        # Count alliance indicators
        positive_markers = sum(
            1 for entry in transcript 
            if any(marker in entry.get('text', '').lower() 
                   for marker in ['trust', 'helpful', 'understood', 'safe', 'grateful'])
        )
        
        negative_markers = sum(
            1 for entry in transcript 
            if any(marker in entry.get('text', '').lower() 
                   for marker in ['mistrust', 'annoying', 'unhelpful', 'frustrated', 'resented'])
        )
        
        total_interactions = len(transcript)
        alliance_score = ((positive_markers - negative_markers) / max(1, total_interactions)) * 100
        alliance_score = max(0, min(100, alliance_score))  # Clamp between 0-100
        
        if alliance_score >= 70:
            rating = "Strong"
        elif alliance_score >= 40:
            rating = "Moderate"
        elif alliance_score >= 20:
            rating = "Weak"
        else:
            rating = "Very Weak"
        
        # Assess components
        components = {
            'agreement': min(100, alliance_score * 0.8),
            'emotional_bond': min(100, alliance_score * 0.7),
            'collaboration': min(100, alliance_score * 0.9)
        }
        
        return TherapeuticAlliance(
            timestamp=datetime.now().isoformat(),
            rating=rating,
            components=components
        )
    
    def _identify_breakdowns(self, transcript: List[Dict]) -> List[Dict]:
        """Identify communication breakdowns"""
        breakdowns = []
        
        for i in range(1, len(transcript)):
            prev = transcript[i - 1]
            curr = transcript[i]
            
            prev_text = prev.get('text', '').lower()
            curr_text = curr.get('text', '').lower()
            
            # Check for breakdown markers
            breakdown_markers = [
                r'\b(whatever|never mind|I don\'t care|go ahead)\b',
                r'\b(yes yes yes|no no no)\b',
                r'\b(ugh|oh my|damn|hell)\b',
                r'\b(he said she said|he said she said)\b',
                r'\b(i\'m tired of|I\'m done)\b'
            ]
            
            if any(marker in prev_text + curr_text for marker in breakdown_markers):
                breakdowns.append({
                    'timestamp': curr.get('time', datetime.now().strftime('%H:%M')),
                    'type': 'Communication Breakdown',
                    'context': f"{prev.get('speaker', 'Unknown')} said: {prev_text[:50]}... {curr.get('speaker', 'Unknown')} responded: {curr_text[:50]}"
                })
        
        return breakdowns
    
    def _determine_dominant_dynamic(self, transcript: List[Dict]) -> str:
        """Determine the dominant relational dynamic"""
        event_counts = {}
        for event in self._detect_relational_events(transcript):
            event_type = event.event_type
            if event_type in ['Transference', 'Counter-Transference']:
                continue  # Skip special dynamics for dominant
            if event_type not in event_counts:
                event_counts[event_type] = 0
            event_counts[event_type] += 1
        
        if not event_counts:
            return "Neutral/Standard"

        return max(event_counts, key=event_counts.get)

class SpeakerInteractionAnalyzer:
    """Analyzes speaker interactions and turn-taking patterns"""
    
    def __init__(self):
        self.ideal_turn_ratio = 0.6  # Therapist should talk 60%
        self.ideal_response_time = 2.0  # seconds (placeholder)
    
    def analyze_turn_patterns(self, transcript: List[Dict]) -> Dict:
        """Analyze turn-taking patterns between therapist and client"""
        therapist_turns = 0
        client_turns = 0
        therapist_word_count = 0
        client_word_count = 0
        
        for entry in transcript:
            speaker = entry.get('speaker', 'Unknown')
            text = entry.get('text', '')
            
            is_therapist = speaker.lower() in ['therapist', 'therapist:', 'doctor', 'Dr.', 'you (therapist)']
            
            if is_therapist:
                therapist_turns += 1
                therapist_word_count += len(text.split())
            else:
                client_turns += 1
                client_word_count += len(text.split())
        
        total_turns = therapist_turns + client_turns
        therapist_ratio = therapist_turns / max(1, total_turns)
        
        return {
            'therapist_turns': therapist_turns,
            'client_turns': client_turns,
            'therapist_ratio': round(therapist_ratio, 2),
            'therapist_words': therapist_word_count,
            'client_words': client_word_count,
            'client_words_per_therapist_turn': round(client_word_count / max(1, therapist_turns), 2),
            'imbalance': "Therapist-Dominant" if therapist_ratio > 0.8 else 
                        "Client-Dominant" if therapist_ratio < 0.4 else "Balanced"
        }
    
    def analyze_response_patterns(self, transcript: List[Dict]) -> Dict:
        """Analyze response patterns and feedback loops"""
        direct_responses = 0
        reflective_responses = 0
        questioning_responses = 0
        silence_periods = 0
        
        last_speaker = None
        silence_count = 0
        
        for entry in transcript:
            speaker = entry.get('speaker', '')
            text = entry.get('text', '')
            
            if not speaker:
                silence_count += 1
                continue
            
            if last_speaker != speaker:
                silence_count = 0
            
            last_speaker = speaker
            
            # Classify response type
            if text and len(text.strip()) > 0:
                if re.search(r'\b(you feel|sounds like|it seems)\b', text):
                    reflective_responses += 1
                elif text.startswith(('?', 'what', 'how', 'why')):
                    questioning_responses += 1
                elif text.strip().lower() in ['uh', 'um', 'mm hmm']:
                    direct_responses += 1
                elif not any(word in text.lower() for word in ['yeah', 'yes', 'no']):
                    reflective_responses += 1
        
        return {
            'direct_responses': direct_responses,
            'reflective_responses': reflective_responses,
            'questioning_responses': questioning_responses,
            'silence_periods': silence_count,
            'feedback_quality': self._assess_feedback_quality(
                reflective_responses, questioning_responses, direct_responses
            )
        }
    
    def _assess_feedback_quality(self, reflective: int, questioning: int, direct: int) -> str:
        """Assess feedback quality"""
        total = max(1, reflective + questioning + direct)
        reflective_ratio = reflective / total
        
        if reflective_ratio > 0.6 and questioning > 2:
            return "High Quality"
        elif reflective_ratio > 0.4:
            return "Moderate Quality"
        elif direct > reflective:
            return "Low Quality - Too Direct"
        else:
            return "Low Quality - Too Passive"

if __name__ == "__main__":
    # Example usage
    sample_transcript = [
        {'time': '09:00', 'speaker': 'client', 'text': 'I feel unheard sometimes.'},
        {'time': '09:02', 'speaker': 'therapist', 'text': 'I understand you want to be heard.'},
        {'time': '09:05', 'speaker': 'client', 'text': 'But I feel dismissed.'},
        {'time': '09:08', 'speaker': 'therapist', 'text': 'That\'s really important to me.'}
    ]
    
    mapper = RelationalDynamicsMapper()
    dynamics = mapper.analyze_session_dynamics(sample_transcript)
    print("Relational Dynamics Analysis Complete")
    print(f"Alliance Rating: {dynamics['therapeutic_alliance'].rating}")
    print(f"Dominant Dynamic: {dynamics['dominant_dynamic']}")