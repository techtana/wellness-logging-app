"""Ingestion Layer - Transcript parsing and standardization"""
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json


class Speaker(Enum):
    THERAPIST = "therapist"
    CLIENT = "client"
    OTHER = "other"


@dataclass
class TranscriptEntry:
    """Standardized transcript entry structure"""
    timestamp: float
    speaker: Speaker
    text: str
    duration: Optional[float] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'speaker': self.speaker.value,
            'text': self.text,
            'duration': self.duration,
            'confidence': self.confidence
        }


class TranscriptParser:
    """Parse various transcript formats into standardized structure"""

    @staticmethod
    def parse_dict_list(transcript: List[Dict]) -> List[TranscriptEntry]:
        """Parse list of dictionaries with flexible key naming"""
        entries = []
        for entry in transcript:
            speaker_value = entry.get('speaker') or entry.get('Speaker') or entry.get('role') or 'other'
            timestamp = entry.get('timestamp') or entry.get('time') or entry.get('Timestamp') or 0
            text = entry.get('text') or entry.get('Text') or entry.get('content') or ''

            try:
                speaker = Speaker(speaker_value.lower())
            except (ValueError, AttributeError):
                speaker = Speaker.OTHER

            if isinstance(timestamp, str):
                try:
                    timestamp = float(timestamp)
                except ValueError:
                    timestamp = 0

            entries.append(TranscriptEntry(
                timestamp=float(timestamp),
                speaker=speaker,
                text=str(text).strip(),
                duration=entry.get('duration'),
                confidence=entry.get('confidence', 1.0)
            ))

        return entries

    @staticmethod
    def parse_json_string(json_str: str) -> List[TranscriptEntry]:
        """Parse JSON string transcript"""
        data = json.loads(json_str)
        if isinstance(data, list):
            return TranscriptParser.parse_dict_list(data)
        elif isinstance(data, dict):
            transcript = data.get('transcript') or data.get('entries') or []
            return TranscriptParser.parse_dict_list(transcript)
        else:
            raise ValueError("Invalid JSON format for transcript")

    @staticmethod
    def parse_structured_format(transcript_data: Dict) -> List[TranscriptEntry]:
        """Parse structured transcript with metadata"""
        entries = []
        transcript_entries = transcript_data.get('entries') or transcript_data.get('transcript') or []

        for entry in transcript_entries:
            entries.append(TranscriptEntry(
                timestamp=entry.get('timestamp', 0),
                speaker=Speaker(entry.get('speaker', 'other').lower()),
                text=entry.get('text', ''),
                duration=entry.get('duration'),
                confidence=entry.get('confidence', 1.0)
            ))
        return entries


class DataStandardizer:
    """Standardize transcript data and clean/normalize text"""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for analysis"""
        return ' '.join(text.split()).lower()

    @staticmethod
    def standardize_entries(entries: List[TranscriptEntry]) -> List[TranscriptEntry]:
        """Apply standardization to all entries"""
        return [
            TranscriptEntry(
                timestamp=entry.timestamp,
                speaker=entry.speaker,
                text=DataStandardizer.normalize_text(entry.text),
                duration=entry.duration,
                confidence=entry.confidence
            )
            for entry in entries
        ]

    @staticmethod
    def validate_transcript(entries: List[TranscriptEntry]) -> tuple:
        """Validate transcript quality"""
        errors = []

        if not entries:
            errors.append("Transcript is empty")
            return False, errors

        speakers = set(e.speaker for e in entries)
        if len(speakers) < 2:
            errors.append("Transcript should have at least 2 speakers")

        total_text = sum(len(e.text) for e in entries)
        if total_text < 50:
            errors.append("Transcript content is too short for meaningful analysis")

        return len(errors) == 0, errors


def standardize_input(transcript_data) -> List[TranscriptEntry]:
    """Main standardization entry point"""
    if isinstance(transcript_data, str):
        entries = TranscriptParser.parse_json_string(transcript_data)
    elif isinstance(transcript_data, list):
        entries = TranscriptParser.parse_dict_list(transcript_data)
    elif isinstance(transcript_data, dict):
        entries = TranscriptParser.parse_structured_format(transcript_data)
    else:
        raise ValueError("Invalid transcript format")

    entries = DataStandardizer.standardize_entries(entries)

    is_valid, errors = DataStandardizer.validate_transcript(entries)
    if not is_valid:
        raise ValueError(f"Transcript validation failed: {'; '.join(errors)}")

    return entries
