"""AI-based transcript analysis using knowledge base instructions."""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

_JSON_INSTRUCTION = "\n\nRespond with valid JSON only — no markdown fences, no explanatory text."


def _fmt(transcript: List[Dict]) -> str:
    return "\n".join(
        f"[{i}] {t.get('speaker', 'unknown').upper()}: {t.get('text', '')}"
        for i, t in enumerate(transcript, 1)
    )


class AIAnalyzer:
    def __init__(self, provider, kb_manager):
        self.provider = provider
        self.kb = kb_manager

    def analyze_emotions(self, transcript: List[Dict]) -> Dict:
        inst = self.kb.get_instruction("sentiment")
        if not inst:
            return {}
        system = inst["prompt"] + _JSON_INSTRUCTION
        user = f"""Analyze this therapy session for emotional content.

TRANSCRIPT:
{_fmt(transcript)}

Return this exact JSON structure:
{{
  "emotion_points": [
    {{"timestamp": "1", "emotion": "Anxious|Depressed|Frustrated|Hopeful|Happy|Angry|Worried|Confused|Calm|Embarrassed", "intensity": 45.0, "context": "brief context", "triggers": ["word"]}}
  ],
  "summary": {{
    "overall_sentiment": "dominant emotion name",
    "average_intensity": 45.0,
    "emotional_stability": "Stable|Moderately Stable|Unstable|Volatile",
    "emotion_distribution": {{"Anxious": 3, "Hopeful": 1}},
    "key_shifts": []
  }},
  "significant_shifts": [
    {{"from_emotion": "Anxious", "to_emotion": "Hopeful", "magnitude": 30.0, "to_time": "turn 6"}}
  ]
}}"""
        try:
            return self.provider.complete_json(system, user) or {}
        except Exception as e:
            logger.error(f"AI emotion analysis: {e}")
            return {}

    def analyze_themes(self, transcript: List[Dict]) -> Dict:
        inst = self.kb.get_instruction("themes")
        if not inst:
            return {}
        client_turns = [t for t in transcript if "client" in t.get("speaker", "").lower()]
        system = inst["prompt"] + _JSON_INSTRUCTION
        user = f"""Analyze this session for themes and cognitive distortions.

FULL TRANSCRIPT:
{_fmt(transcript)}

CLIENT SPEECH ONLY:
{_fmt(client_turns)}

Return this exact JSON structure:
{{
  "themes": [{{"theme": "Work|Relationships|Health|Family|Money|Spirituality|Identity", "frequency": 2, "percentage": 0.4}}],
  "dominant_themes": [{{"theme": "Work", "frequency": 3, "percentage": 0.6}}],
  "recurring_themes": [{{"theme": "Identity", "instances": 2, "percentage": 0.3}}],
  "narrative_shifts": [{{"turn": 4, "description": "topic changed from work to family"}}],
  "cognitive_distortions": [
    {{"distortion_type": "Catastrophizing|Overgeneralization|Mind Reading|Emotional Reasoning|All-or-Nothing Thinking|Magnification/Minimization|Labeling|Personalization|Should Statements|Control Issues",
      "severity": "Mild|Moderate|Severe", "example": "exact quote", "turn": 3}}
  ],
  "distortion_summary": {{}}
}}"""
        try:
            return self.provider.complete_json(system, user) or {}
        except Exception as e:
            logger.error(f"AI theme analysis: {e}")
            return {}

    def analyze_dynamics(self, transcript: List[Dict]) -> Dict:
        inst = self.kb.get_instruction("dynamics")
        if not inst:
            return {}
        system = inst["prompt"] + _JSON_INSTRUCTION
        user = f"""Analyze the relational dynamics in this therapy session.

TRANSCRIPT:
{_fmt(transcript)}

Return this exact JSON structure:
{{
  "speaker_profiles": {{
    "therapist": {{"style": "Direct|Passive|Aggressive|Passive-Aggressive|Assertive|Ambivalent|Defensive", "intensity": 60.0, "word_count": 80, "sample_phrases": ["example phrase"]}},
    "client": {{"style": "Passive", "intensity": 70.0, "word_count": 120, "sample_phrases": ["example phrase"]}}
  }},
  "relational_events": [
    {{"event_type": "Positive Alliance|Negative Alliance|Conflict|Empathy|Transference", "context": "description of the moment", "turn": 2}}
  ],
  "therapeutic_alliance": {{
    "timestamp": "session",
    "rating": "Strong|Moderate|Weak|Very Weak",
    "components": {{"agreement": 70, "emotional_bond": 65, "collaboration": 75}}
  }},
  "communication_breakdowns": [],
  "dominant_dynamic": "collaborative exploration"
}}"""
        try:
            return self.provider.complete_json(system, user) or {}
        except Exception as e:
            logger.error(f"AI dynamics analysis: {e}")
            return {}

    def generate_report_sections(
        self, transcript: List[Dict], session_id: str, patient_id: str,
        sentiment: Dict, thematic: Dict, relational: Dict
    ) -> Dict:
        inst = self.kb.get_instruction("clinical_report")
        if not inst:
            return {}

        emotion_summary = sentiment.get("summary", {})
        themes_list = [t.get("theme", "") for t in thematic.get("dominant_themes", [])[:3]]
        distortions = [d.get("distortion_type", "") for d in thematic.get("cognitive_distortions", [])[:3]]
        alliance = relational.get("therapeutic_alliance", {}).get("rating", "Unknown")

        system = inst["prompt"] + _JSON_INSTRUCTION
        user = f"""Generate a comprehensive clinical report for session {session_id}.

TRANSCRIPT:
{_fmt(transcript)}

ANALYSIS CONTEXT:
- Dominant emotion: {emotion_summary.get('overall_sentiment', 'Unknown')}, stability: {emotion_summary.get('emotional_stability', 'Unknown')}
- Main themes: {', '.join(themes_list) or 'None identified'}
- Cognitive distortions: {', '.join(distortions) or 'None identified'}
- Therapeutic alliance: {alliance}

Return this exact JSON structure:
{{
  "executive_summary": {{
    "overall_tone_trajectory": "narrative describing how session tone evolved",
    "key_takeaways": ["specific takeaway 1", "specific takeaway 2", "specific takeaway 3"],
    "priority_focus_area": "most important clinical focus",
    "session_duration": "standard"
  }},
  "thematic_analysis": {{
    "dominant_themes": ["theme 1", "theme 2"],
    "underlying_themes": ["theme - recurs N times"],
    "pattern_detection": ["observed pattern"],
    "cognitive_distortions": ["distortion type identified"]
  }},
  "emotional_mapping": {{
    "key_shifts": ["At turn X: shift from Y to Z (magnitude N)"],
    "emotional_trajectory": [],
    "predictors": ["pattern that tends to precede emotional shifts"],
    "stability_assessment": "assessment of emotional regulation"
  }},
  "clinical_hypothesis": {{
    "potential_interventions": ["named technique 1", "named technique 2"],
    "therapeutic_approaches": ["CBT", "Motivational Interviewing"],
    "journaling_prompts": ["open-ended prompt 1", "open-ended prompt 2", "open-ended prompt 3"],
    "follow_up_focus": "specific next session focus"
  }},
  "relational_dynamics": {{
    "therapeutic_alliance_rating": "{alliance}",
    "communication_patterns": {{}},
    "power_dynamics": {{}},
    "areas_of_strength": ["specific strength 1", "specific strength 2"],
    "areas_for_improvement": ["specific area 1"]
  }},
  "recommendations": {{
    "immediate_actions": ["actionable item 1", "actionable item 2"],
    "next_session_focus": "specific and actionable focus area",
    "monitoring_points": ["what to watch for 1", "what to watch for 2"],
    "red_flags": []
  }}
}}"""
        try:
            return self.provider.complete_json(system, user) or {}
        except Exception as e:
            logger.error(f"AI report generation: {e}")
            return {}
