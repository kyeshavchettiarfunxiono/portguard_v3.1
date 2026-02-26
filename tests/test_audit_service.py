import re
from datetime import datetime

from services.audit_service import AuditService


def test_generate_reference_format_is_enterprise_safe():
    ref = AuditService.generate_reference(datetime(2026, 2, 23, 12, 0, 0))
    assert re.fullmatch(r"AUD-20260223-[A-F0-9]{8}", ref)


def test_generate_reference_uniqueness():
    ref1 = AuditService.generate_reference()
    ref2 = AuditService.generate_reference()
    assert ref1 != ref2


def test_safe_level_defaults_to_info_for_unknown_values():
    assert AuditService._safe_level("random") == "INFO"
    assert AuditService._safe_level("error") == "ERROR"
