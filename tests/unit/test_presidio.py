from src.security.presidio_service import PresidioService


def test_person_detection():
    svc = PresidioService()
    text = 'The finding owner is Alice Chen from Risk Management.'
    anonymized = svc.anonymize(text)
    assert 'Alice Chen' not in anonymized
    assert '<PERSON>' in anonymized


def test_phone_detection():
    svc = PresidioService()
    text = 'Call the auditor at +852-9876-5432'
    anonymized = svc.anonymize(text)
    assert '+852-9876-5432' not in anonymized


def test_no_pii_passthrough():
    svc = PresidioService()
    text = 'The AML threshold review was completed in Q3 2025.'
    anonymized = svc.anonymize(text)
    assert 'AML threshold review' in anonymized


def test_has_pii_flag():
    svc = PresidioService()
    assert svc.has_pii('Contact john@bnpp.com') == True
    assert svc.has_pii('Finding HK-2024-001 is critical') == False
