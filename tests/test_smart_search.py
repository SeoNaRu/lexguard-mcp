"""
SmartSearchService 단위 테스트

API 호출 없이 순수 로직(의도 분석, 시간 조건 파싱, 파라미터 추출)을 검증.
"""
import pytest
from datetime import datetime
from src.services.smart_search_service import SmartSearchService


@pytest.fixture
def service():
    return SmartSearchService()


# ---------------------------------------------------------------------------
# analyze_intent — 의도 분류
# ---------------------------------------------------------------------------

class TestAnalyzeIntent:
    def test_returns_list(self, service):
        result = service.analyze_intent("프리랜서 근로자성 판례")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_result_is_tuple_of_str_float(self, service):
        result = service.analyze_intent("부당해고 판례")
        for item in result:
            assert isinstance(item, tuple)
            assert isinstance(item[0], str)
            assert isinstance(item[1], float)

    def test_confidence_between_0_and_1(self, service):
        result = service.analyze_intent("개인정보 유출 법령")
        for _, conf in result:
            assert 0.0 <= conf <= 1.0

    def test_labor_worker_intent(self, service):
        result = service.analyze_intent("프리랜서 근로자성 사용종속관계")
        intents = [r[0] for r in result]
        assert "labor_worker_status" in intents

    def test_labor_termination_intent(self, service):
        result = service.analyze_intent("부당해고 판례 알려줘")
        intents = [r[0] for r in result]
        assert "labor_termination" in intents

    def test_labor_wage_intent(self, service):
        result = service.analyze_intent("임금체불 퇴직금 계산")
        intents = [r[0] for r in result]
        assert "labor_wage" in intents

    def test_precedent_intent(self, service):
        result = service.analyze_intent("대법원 판례 손해배상")
        intents = [r[0] for r in result]
        assert "precedent" in intents

    def test_constitutional_intent(self, service):
        result = service.analyze_intent("헌법재판소 위헌 결정")
        intents = [r[0] for r in result]
        assert "constitutional" in intents

    def test_interpretation_intent(self, service):
        result = service.analyze_intent("법령해석 법제처 의견")
        intents = [r[0] for r in result]
        assert "interpretation" in intents

    def test_administrative_appeal_intent(self, service):
        result = service.analyze_intent("행정심판 재결례")
        intents = [r[0] for r in result]
        assert "administrative_appeal" in intents

    def test_ordinance_intent(self, service):
        result = service.analyze_intent("서울시 조례 확인하고 싶어요")
        intents = [r[0] for r in result]
        assert "ordinance" in intents

    def test_empty_query_returns_default(self, service):
        result = service.analyze_intent("")
        assert len(result) > 0
        assert result[0][0] == "law"

    def test_ambiguous_query_returns_default(self, service):
        result = service.analyze_intent("도움")
        assert len(result) > 0

    def test_multi_intent_detection(self, service):
        """법령 + 판례 동시 감지"""
        result = service.analyze_intent("형법 제250조와 관련 판례")
        intents = [r[0] for r in result]
        assert len(intents) >= 1


# ---------------------------------------------------------------------------
# parse_time_condition — 시간 조건 파싱
# ---------------------------------------------------------------------------

class TestParseTimeCondition:
    def test_no_time_condition_returns_none(self, service):
        result = service.parse_time_condition("부당해고 판례")
        assert result is None

    def test_recent_n_years(self, service):
        result = service.parse_time_condition("최근 3년 판례")
        assert result is not None
        assert "date_from" in result
        assert "date_to" in result

    def test_recent_n_years_format(self, service):
        result = service.parse_time_condition("최근 5년 판례")
        assert len(result["date_from"]) == 8
        assert len(result["date_to"]) == 8
        assert result["date_from"].isdigit()
        assert result["date_to"].isdigit()

    def test_recent_n_years_range(self, service):
        result = service.parse_time_condition("최근 3년 판례")
        today = datetime.now()
        year_from = int(result["date_from"][:4])
        year_to = int(result["date_to"][:4])
        assert year_to == today.year
        assert year_from == today.year - 3

    @pytest.mark.parametrize(
        "query",
        [
            "최근 3개년 부당해고 판례",
            "최근 2년동안 부당해고 판례",
            "최근 3년간 부당해고 판례",
        ],
    )
    def test_recent_year_variants(self, service, query):
        result = service.parse_time_condition(query)
        assert result is not None
        assert len(result["date_from"]) == 8
        assert len(result["date_to"]) == 8

    def test_after_year(self, service):
        result = service.parse_time_condition("2022년 이후 판례")
        assert result is not None
        assert result["date_from"].startswith("2022")

    def test_year_range(self, service):
        result = service.parse_time_condition("2020년부터 2023년까지 판례")
        assert result is not None
        assert result["date_from"].startswith("2020")
        assert result["date_to"].startswith("2023")

    def test_latest_keyword(self, service):
        result = service.parse_time_condition("최신 판례")
        assert result is not None
        today = datetime.now()
        year_to = int(result["date_to"][:4])
        assert year_to == today.year

    def test_recent_keyword(self, service):
        result = service.parse_time_condition("요즘 판례 알려줘")
        assert result is not None

    def test_date_from_before_date_to(self, service):
        for query in ["최근 3년 판례", "2021년 이후 판례", "최신 판례"]:
            result = service.parse_time_condition(query)
            if result:
                assert result["date_from"] <= result["date_to"], \
                    f"date_from > date_to: {query}"


class TestStripTimeCondition:
    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("최근 3년 부당해고 판례", "부당해고 판례"),
            ("최근 3개년 부당해고 판례", "부당해고 판례"),
            ("최근 2년동안 부당해고 판례", "부당해고 판례"),
            ("최근 3년간 부당해고 판례", "부당해고 판례"),
            ("2022년 이후 부당해고 판례", "부당해고 판례"),
            ("2020년부터 2023년까지 부당해고 판례", "부당해고 판례"),
        ],
    )
    def test_strips_supported_time_phrases(self, service, query, expected):
        assert service.strip_time_condition(query) == expected


class TestCleanPrecedentQuery:
    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("최근 3년 부당해고 판례", "부당해고"),
            ("최근 3개년 부당해고 판례", "부당해고"),
            ("최근 2년동안 부당해고 판례", "부당해고"),
            ("최근 3년간 부당해고 판례", "부당해고"),
            ("부당해고 판례", "부당해고"),
            ("부당해고 관련 판례", "부당해고"),
            ("부당해고 판례 검색", "부당해고"),
            ("부당해고 유사 사례", "부당해고"),
            ("부당해고 유사 판례", "부당해고"),
            ("부당해고 관련 사례", "부당해고"),
            ("부당해고 유사 재판 사례", "부당해고"),
            ("부당해고 관련", "부당해고"),
            ("부당해고 기록", "부당해고"),
            ("부당해고 유사 기록", "부당해고"),
            ("부당해고 참고 사례", "부당해고"),
            ("부당해고 참고 판례", "부당해고"),
        ],
    )
    def test_removes_precedent_markers(self, service, query, expected):
        assert service.clean_precedent_query(query) == expected


class TestFetchSearchType:
    @pytest.mark.asyncio
    async def test_precedent_uses_time_condition_and_fallback(self, service, monkeypatch):
        captured = {}

        async def fake_search_precedent_with_fallback(
            query, page, per_page, court, date_from, date_to, arguments
        ):
            captured.update(
                {
                    "query": query,
                    "page": page,
                    "per_page": per_page,
                    "court": court,
                    "date_from": date_from,
                    "date_to": date_to,
                    "arguments": arguments,
                }
            )
            return {"total": 1, "precedents": [{"caseNm": "테스트"}]}

        async def fail_search_precedent(*args, **kwargs):
            raise AssertionError("search_precedent should not be used for precedent smart search")

        monkeypatch.setattr(
            service.precedent_repo,
            "search_precedent_with_fallback",
            fake_search_precedent_with_fallback,
        )
        monkeypatch.setattr(service.precedent_repo, "search_precedent", fail_search_precedent)

        search_type, result = await service._fetch_search_type(
            "precedent",
            {"date_from": "20230101", "date_to": "20251231"},
            "최근 3년 부당해고 판례",
            "부당해고 판례",
            3,
            {"oc": "demo"},
        )

        assert search_type == "precedent"
        assert result["total"] == 1
        assert captured == {
            "query": "부당해고",
            "page": 1,
            "per_page": 3,
            "court": None,
            "date_from": "20230101",
            "date_to": "20251231",
            "arguments": {"oc": "demo"},
        }

    @pytest.mark.asyncio
    async def test_precedent_without_time_uses_cleaned_direct_query(self, service, monkeypatch):
        captured = {}

        async def fake_search_precedent(query, page, per_page, court, date_from, date_to, arguments):
            captured.update(
                {
                    "query": query,
                    "page": page,
                    "per_page": per_page,
                    "court": court,
                    "date_from": date_from,
                    "date_to": date_to,
                    "arguments": arguments,
                }
            )
            return {"total": 1, "precedents": [{"caseNm": "테스트"}]}

        async def fail_search_precedent_with_fallback(*args, **kwargs):
            raise AssertionError("search_precedent_with_fallback should not be used without time condition")

        monkeypatch.setattr(service.precedent_repo, "search_precedent", fake_search_precedent)
        monkeypatch.setattr(
            service.precedent_repo,
            "search_precedent_with_fallback",
            fail_search_precedent_with_fallback,
        )

        search_type, result = await service._fetch_search_type(
            "precedent",
            {},
            "부당해고 판례",
            "부당해고 판례",
            3,
            {"oc": "demo"},
        )

        assert search_type == "precedent"
        assert result["total"] == 1
        assert captured == {
            "query": "부당해고",
            "page": 1,
            "per_page": 3,
            "court": None,
            "date_from": None,
            "date_to": None,
            "arguments": {"oc": "demo"},
        }


# ---------------------------------------------------------------------------
# extract_parameters — 파라미터 추출
# ---------------------------------------------------------------------------

class TestExtractParameters:
    def test_returns_dict(self, service):
        result = service.extract_parameters("형법 판례", "law")
        assert isinstance(result, dict)

    def test_query_always_present(self, service):
        result = service.extract_parameters("형법 판례", "law")
        assert "query" in result

    def test_extracts_law_name(self, service):
        result = service.extract_parameters("근로기준법 제23조", "law")
        assert "law_name" in result
        assert "근로기준법" in result["law_name"]

    def test_extracts_article_number(self, service):
        result = service.extract_parameters("형법 제250조 판례", "law")
        assert "article_number" in result

    def test_extracts_hang_number(self, service):
        result = service.extract_parameters("형법 제250조 제1항", "law")
        assert "hang" in result

    def test_extracts_ho_number(self, service):
        result = service.extract_parameters("개인정보보호법 제2조 제1항 제1호", "law")
        assert "ho" in result

    def test_extracts_mok_character(self, service):
        result = service.extract_parameters("개인정보보호법 제2조 가목", "law")
        assert "mok" in result

    def test_committee_type_for_personal_info(self, service):
        result = service.extract_parameters("개인정보보호위원회 결정", "committee")
        assert "committee_type" in result
        assert "개인정보보호위원회" in result["committee_type"]

    def test_local_gov_seoul(self, service):
        result = service.extract_parameters("서울시 조례", "ordinance")
        assert "local_government" in result
        assert "서울" in result["local_government"]

    def test_agency_labor(self, service):
        result = service.extract_parameters("고용노동부 해석", "interpretation")
        assert "agency" in result
        assert "고용노동부" in result["agency"]


# ---------------------------------------------------------------------------
# plan_queries — 다단계 쿼리 계획
# ---------------------------------------------------------------------------

class TestPlanQueries:
    def test_returns_list(self, service):
        result = service.plan_queries("근로자성 판단", "labor_worker_status")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_labor_worker_freelancer_keywords(self, service):
        result = service.plan_queries("프리랜서 근로자 인정", "labor_worker_status")
        all_text = " ".join(result)
        assert "근로자" in all_text or "프리랜서" in all_text

    def test_labor_termination_keywords(self, service):
        result = service.plan_queries("부당해고", "labor_termination")
        all_text = " ".join(result)
        assert "해고" in all_text

    def test_labor_wage_retirement_keywords(self, service):
        result = service.plan_queries("퇴직금 계산", "labor_wage")
        all_text = " ".join(result)
        assert "퇴직금" in all_text

    def test_labor_wage_overdue_keywords(self, service):
        result = service.plan_queries("임금체불 신고", "labor_wage")
        all_text = " ".join(result)
        assert "임금" in all_text or "체불" in all_text

    def test_unknown_intent_returns_original_query(self, service):
        query = "헌법재판소 위헌 결정"
        result = service.plan_queries(query, "constitutional")
        assert query in result
