"""
AxisQueryBuilder 순수 로직 테스트 (API 키 불필요)
"""
import pytest
from src.utils.axis_query_builder import AxisQueryBuilder


@pytest.fixture
def builder():
    return AxisQueryBuilder()


class TestBuildAxisQueries:
    def test_returns_expected_keys(self, builder):
        result = builder.build_axis_queries("프리랜서 근로자성 다툼이 있습니다")
        assert "legal_axis" in result
        assert "fact_axis" in result
        assert "query_plan" in result
        assert result["original_query"] == "프리랜서 근로자성 다툼이 있습니다"

    def test_empty_query_structure(self, builder):
        result = builder.build_axis_queries("")
        assert isinstance(result["legal_axis"], list)
        assert isinstance(result["fact_axis"], list)
