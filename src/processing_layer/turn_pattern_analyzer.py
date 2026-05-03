import time
from typing import List, Dict, Optional

class TurnPatternAnalyzer:
    def __init__(self, threshold_seconds: float = 2.0):
        self.threshold_seconds = threshold_seconds
        self.patterns = {
            'pauses': 0,
            'overlaps': 0,
            'silence_gaps': 0,
            'rapid_responses': 0
        }
        self.interaction_timing = []

    def analyze_turns(self, transcript: List[Dict]) -> Dict:
        """
        Analyze the timing and pattern of speaker turns.

        Args:
        - transcript (List[Dict]): Transcription data with timestamps and speaker information

        Returns:
        - A dictionary containing the analysis of turn patterns
        """
        # Reset state so the same instance can be reused across sessions
        self.patterns = {'pauses': 0, 'overlaps': 0, 'silence_gaps': 0, 'rapid_responses': 0}
        self.interaction_timing = []

        if not transcript:
            return self._empty_results()

        # Sort by timestamp if necessary
        transcript = sorted(transcript, key=lambda x: x.get('timestamp', 0))

        # Analyze turn patterns
        previous_timestamp = None
        current_timestamp = None
        time_diff = 0.0

        for entry in transcript:
            current_timestamp = entry.get('timestamp', 0)

            # Calculate time difference from previous turn
            if previous_timestamp is not None:
                time_diff = current_timestamp - previous_timestamp
                if time_diff > self.threshold_seconds:
                    self.patterns['pauses'] += 1
                elif time_diff < 0:
                    self.patterns['overlaps'] += 1
                elif time_diff < 0.5:
                    self.patterns['rapid_responses'] += 1
                else:
                    self.patterns['silence_gaps'] += 1

            previous_timestamp = current_timestamp

            # Store the interaction timing data
            self.interaction_timing.append({
                'timestamp': current_timestamp,
                'time_diff': time_diff
            })

        return self._format_results()

    def _format_results(self) -> Dict:
        """
        Format the analysis results into a dictionary.
        
        Returns:
        - A dictionary containing the formatted analysis results
        """
        return {
            'pauses': self.patterns['pauses'],
            'overlaps': self.patterns['overlaps'],
            'silence_gaps': self.patterns['silence_gaps'],
            'rapid_responses': self.patterns['rapid_responses'],
            'total_turns': len(self.interaction_timing),
            'avg_time_diff': round(sum(t['time_diff'] for t in self.interaction_timing) / max(1, len(self.interaction_timing)), 2)
        }

    def _empty_results(self) -> Dict:
        """
        Return an empty results dictionary.
        
        Returns:
        - A dictionary containing empty results
        """
        return {
            'pauses': 0,
            'overlaps': 0,
            'silence_gaps': 0,
            'rapid_responses': 0,
            'total_turns': 0,
            'avg_time_diff': 0.0
        }