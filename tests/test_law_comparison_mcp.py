"""
law_comparison_tool · CompareLawsRequest 검증 (API 키 불필요)
"""
import pytest
from pydantic import ValidationError

from src.models import CompareLawsRequest


def test_compare_laws_request_defaults():
    r = CompareLawsRequest(law_name="민법")
    assert r.compare_type == "신구법"


def test_compare_laws_request_all_types():
    for t in ("신구법", "연혁", "3단비교"):
        r = CompareLawsRequest(law_name="형법", compare_type=t)
        assert r.compare_type == t


def test_compare_laws_request_rejects_invalid_type():
    with pytest.raises(ValidationError):
        CompareLawsRequest(law_name="민법", compare_type="invalid")  # type: ignore[arg-type]
