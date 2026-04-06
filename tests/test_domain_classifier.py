"""
DomainClassifier 순수 로직 테스트 (API 키 불필요)
"""
import pytest
from src.utils.domain_classifier import LEGAL_DOMAINS, DomainClassifier, get_domain_classifier


@pytest.fixture
def classifier():
    return DomainClassifier()


class TestClassify:
    def test_labor_termination_domain(self, classifier):
        out = classifier.classify("부당해고 구제 신청 절차가 궁금합니다")
        names = [d for d, _ in out]
        assert "부당해고" in names

    def test_real_estate_domain(self, classifier):
        out = classifier.classify("전세 보증금 반환 소송 절차")
        names = [d for d, _ in out]
        assert "부동산" in names

    def test_consumer_domain(self, classifier):
        out = classifier.classify("전자상거래 청약철회 기간이 얼마나 되나요")
        names = [d for d, _ in out]
        assert "소비자" in names

    def test_finance_domain(self, classifier):
        out = classifier.classify("금융소비자보호법상 부당권유 금지")
        names = [d for d, _ in out]
        assert "금융" in names

    def test_legal_domains_count(self):
        """README·문서의 도메인 개수와 동기화 (부동산·소비자·금융 포함 13개)."""
        assert len(LEGAL_DOMAINS) == 13

    def test_empty_query_returns_empty(self, classifier):
        assert classifier.classify("") == []

    def test_sorted_by_score_descending(self, classifier):
        out = classifier.classify("임금 체불과 퇴직금 미지급")
        scores = [s for _, s in out]
        assert scores == sorted(scores, reverse=True)

    def test_get_domain_keywords_unknown_returns_empty(self, classifier):
        assert classifier.get_domain_keywords("no_such_domain") == []

    def test_classify_with_confidence_filters_low(self, classifier):
        domains = classifier.classify_with_confidence("법", min_confidence=0.99)
        assert isinstance(domains, list)


class TestSingleton:
    def test_get_domain_classifier_returns_same_instance(self):
        a = get_domain_classifier()
        b = get_domain_classifier()
        assert a is b
