from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from typing import List
import logging
import re

logger = logging.getLogger(__name__)


class HKIDRecognizer(PatternRecognizer):
    """Custom recogniser for Hong Kong Identity Card numbers (A123456(7) pattern)."""
    PATTERNS = [
        Pattern('HKID', r'[A-Z]{1,2}[0-9]{6}\([0-9A]\)', 0.8),
        Pattern('HKID_short', r'[A-Z][0-9]{6}', 0.4),
    ]

    def __init__(self):
        super().__init__(supported_entity='HKID', patterns=self.PATTERNS)


class PresidioService:
    """PII detection and anonymisation for banking-grade AI pipelines."""

    # Entities to detect and mask
    TARGET_ENTITIES = [
        'PERSON', 'PHONE_NUMBER', 'EMAIL_ADDRESS',
        'CREDIT_CARD', 'IBAN_CODE', 'LOCATION',
        'DATE_TIME', 'URL', 'HKID',
    ]

    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.analyzer.registry.add_recognizer(HKIDRecognizer())
        self.anonymizer = AnonymizerEngine()
        logger.info('Presidio PII service initialised')

    def analyze(self, text: str) -> list:
        """Detect PII entities in text. Returns list of RecognizerResult."""
        try:
            return self.analyzer.analyze(
                text=text,
                language='en',
                entities=self.TARGET_ENTITIES,
            )
        except Exception as e:
            logger.warning(f'Presidio analyze failed: {e}')
            return []

    def anonymize(self, text: str) -> str:
        """
        Mask PII in text, replacing with <TYPE> placeholders.
        Example: 'Contact Li Wei at +852-9876-5432'
              -> 'Contact <PERSON> at <PHONE_NUMBER>'
        """
        try:
            results = self.analyze(text)
            if not results:
                return text
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    'DEFAULT': OperatorConfig('replace', {'new_value': '<REDACTED>'}),
                    'PERSON': OperatorConfig('replace', {'new_value': '<PERSON>'}),
                    'PHONE_NUMBER': OperatorConfig('replace', {'new_value': '<PHONE_NUMBER>'}),
                    'EMAIL_ADDRESS': OperatorConfig('replace', {'new_value': '<EMAIL_ADDRESS>'}),
                    'CREDIT_CARD': OperatorConfig('replace', {'new_value': '<CREDIT_CARD>'}),
                    'IBAN_CODE': OperatorConfig('replace', {'new_value': '<IBAN_CODE>'}),
                    'HKID': OperatorConfig('replace', {'new_value': '<HKID>'}),
                }
            )
            return anonymized.text
        except Exception as e:
            logger.warning(f'Presidio anonymize failed: {e}. Returning original.')
            return text

    def has_pii(self, text: str) -> bool:
        """Quick check: does this text contain any PII? Used for audit logging."""
        return len(self.analyze(text)) > 0

    def get_pii_summary(self, text: str) -> dict:
        """Return a summary of what PII was found (for audit logging)."""
        results = self.analyze(text)
        from collections import Counter
        counts = Counter(r.entity_type for r in results)
        return dict(counts)


# Module-level singleton — initialised once, reused across requests
presidio = PresidioService()
