"""SmartSearchService 개별 조회 메서드 믹스인.

SmartSearchService 에서 사용하는 13개 lookup 메서드를 분리합니다.
이 믹스인은 SmartSearchService 인스턴스 속성
  (precedent_repo, interpretation_repo, ordinance_repo, rule_repo,
   appeal_repo, constitutional_repo, committee_repo, special_appeal_repo,
   history_repo, misc_repo, form_repo, link_repo, _apply_rerank_lists)
이 있다고 가정합니다.
"""
from typing import Optional

from ..repositories.committee_decision_repository import COMMITTEE_TARGET_MAP
from ..repositories.special_administrative_appeal_repository import TRIBUNAL_TARGET_MAP


class LookupMethodsMixin:
    """개별 데이터 소스를 대상으로 한 thin lookup 메서드 13개."""

    # ------------------------------------------------------------------ #
    # 기본 lookup (8개) — legal_qa_tool 외 전용 MCP 도구용
    # ------------------------------------------------------------------ #

    async def precedent_lookup(
        self,
        keyword: Optional[str] = None,
        case_number: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None,
    ) -> dict:
        """판례만 검색 (사건번호 또는 키워드). 통합 legal_qa_tool과 구분해 에이전트가 선택하기 쉽게 함."""
        q = (case_number or "").strip() or (keyword or "").strip()
        if not q:
            return {
                "error_code": "INVALID_INPUT",
                "error": "사건번호 또는 검색 키워드 중 하나는 필요합니다.",
                "recovery_guide": "case_number(예: 2023다12345) 또는 keyword를 입력하세요.",
            }
        result = await self.precedent_repo.search_precedent(
            q, page, per_page, court, date_from, date_to, arguments,
        )
        if isinstance(result, dict):
            self._apply_rerank_lists(q, result)
        return result

    async def interpretation_lookup(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        agency: Optional[str] = None,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령해석만 검색."""
        qq = (query or "").strip()
        if not qq:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어가 비어 있습니다.",
                "recovery_guide": "법령해석 검색어(키워드)를 입력하세요.",
            }
        result = await self.interpretation_repo.search_law_interpretation(
            qq, page, per_page, agency, arguments,
        )
        if isinstance(result, dict):
            self._apply_rerank_lists(qq, result)
        return result

    async def local_ordinance_lookup(
        self,
        query: Optional[str] = None,
        local_government: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """자치법규(조례 등)만 검색."""
        q = (query or "").strip() or None
        lg = (local_government or "").strip() or None
        if not q and not lg:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어 또는 지자체명 중 하나 이상이 필요합니다.",
                "recovery_guide": "조례 키워드 query 또는 local_government(예: 서울시)를 입력하세요.",
            }
        return await self.ordinance_repo.search_local_ordinance(q, lg, page, per_page, arguments)

    async def administrative_rule_lookup(
        self,
        query: Optional[str] = None,
        agency: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """행정규칙만 검색."""
        q = (query or "").strip() or None
        ag = (agency or "").strip() or None
        if not q and not ag:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어 또는 부처명 중 하나 이상이 필요합니다.",
                "recovery_guide": "행정규칙 키워드 query 또는 agency(예: 고용노동부)를 입력하세요.",
            }
        return await self.rule_repo.search_administrative_rule(q, ag, page, per_page, arguments)

    async def administrative_appeal_lookup(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None,
    ) -> dict:
        """행정심판 재결만 검색."""
        qq = (query or "").strip()
        if not qq:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어가 비어 있습니다.",
                "recovery_guide": "행정심판 재결 검색어를 입력하세요.",
            }
        result = await self.appeal_repo.search_administrative_appeal(
            qq, page, per_page, date_from, date_to, arguments,
        )
        if isinstance(result, dict):
            self._apply_rerank_lists(qq, result)
        return result

    async def constitutional_decision_lookup(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None,
    ) -> dict:
        """헌법재판소 결정만 검색."""
        qq = (query or "").strip()
        if not qq:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어가 비어 있습니다.",
                "recovery_guide": "헌재결정 검색어(키워드 또는 사건번호 형태)를 입력하세요.",
            }
        result = await self.constitutional_repo.search_constitutional_decision(
            qq, page, per_page, date_from, date_to, arguments,
        )
        if isinstance(result, dict):
            self._apply_rerank_lists(qq, result)
        return result

    async def committee_decision_lookup(
        self,
        committee_type: str,
        query: str,
        page: int = 1,
        per_page: int = 10,
        arguments: Optional[dict] = None,
    ) -> dict:
        """위원회 결정문만 검색."""
        ct = (committee_type or "").strip()
        if ct not in COMMITTEE_TARGET_MAP:
            return {
                "error_code": "INVALID_COMMITTEE",
                "error": f"지원하지 않는 위원회 종류입니다: {committee_type}",
                "recovery_guide": "지원: " + ", ".join(sorted(COMMITTEE_TARGET_MAP.keys())),
                "supported_committees": list(COMMITTEE_TARGET_MAP.keys()),
            }
        qq = (query or "").strip()
        if not qq:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어가 비어 있습니다.",
                "recovery_guide": "결정문 검색어를 입력하세요.",
            }
        result = await self.committee_repo.search_committee_decision(ct, qq, page, per_page, arguments)
        if isinstance(result, dict):
            self._apply_rerank_lists(qq, result)
        return result

    async def special_administrative_appeal_lookup(
        self,
        tribunal_type: str,
        query: str,
        page: int = 1,
        per_page: int = 10,
        arguments: Optional[dict] = None,
    ) -> dict:
        """특별행정심판원 재결만 검색."""
        tt = (tribunal_type or "").strip()
        if tt not in TRIBUNAL_TARGET_MAP:
            return {
                "error_code": "INVALID_TRIBUNAL",
                "error": f"지원하지 않는 심판원입니다: {tribunal_type}",
                "recovery_guide": "지원: " + ", ".join(sorted(TRIBUNAL_TARGET_MAP.keys())),
                "supported_tribunals": list(TRIBUNAL_TARGET_MAP.keys()),
            }
        qq = (query or "").strip()
        if not qq:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어가 비어 있습니다.",
                "recovery_guide": "재결 검색어를 입력하세요.",
            }
        result = await self.special_appeal_repo.search_special_administrative_appeal(
            tt, qq, page, per_page, arguments,
        )
        if isinstance(result, dict):
            self._apply_rerank_lists(qq, result)
        return result

    # ------------------------------------------------------------------ #
    # 확장 lookup (5개) — ministry·history·info·form·link
    # ------------------------------------------------------------------ #

    async def ministry_interpretation_lookup(
        self,
        query: Optional[str] = None,
        agency: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """특정 부처의 법령해석을 검색합니다."""
        q = (query or "").strip() or None
        ag = (agency or "").strip() or None
        if not q and not ag:
            return {
                "error_code": "INVALID_INPUT",
                "error": "검색어(query) 또는 부처명(agency) 중 하나 이상이 필요합니다.",
                "recovery_guide": "예: query='퇴직금', agency='고용노동부'",
                "supported_agencies": list(self.interpretation_repo.AGENCY_TARGET_MAP.keys()),
            }
        result = await self.interpretation_repo.search_law_interpretation(q, page, per_page, ag, arguments)
        if isinstance(result, dict) and q:
            self._apply_rerank_lists(q, result)
        return result

    async def law_history_lookup(
        self,
        search_type: str = "law_change",
        query: Optional[str] = None,
        law_id: Optional[str] = None,
        article_number: Optional[str] = None,
        date: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령 변경이력 또는 조문 개정이력을 조회합니다."""
        valid_types = {"law_change", "article_change", "article_detail"}
        if search_type not in valid_types:
            return {
                "error_code": "INVALID_INPUT",
                "error": f"지원하지 않는 search_type: {search_type}",
                "recovery_guide": "search_type은 law_change / article_change / article_detail 중 하나여야 합니다.",
            }
        if search_type == "article_detail":
            if not law_id:
                return {
                    "error_code": "INVALID_INPUT",
                    "error": "article_detail 조회 시 law_id가 필요합니다.",
                    "recovery_guide": "law_id(법령 ID)를 입력하세요.",
                }
            return await self.history_repo.get_article_change_history(law_id, article_number, arguments)
        if search_type == "article_change":
            return await self.history_repo.search_article_change_history(
                query, law_id, date, page, per_page, arguments
            )
        # default: law_change
        return await self.history_repo.search_law_change_history(query, law_id, date, page, per_page, arguments)

    async def law_info_lookup(
        self,
        info_type: str = "english_law",
        query: Optional[str] = None,
        item_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """영문법령·조약·체계도·한눈보기·약칭 등 부가 정보를 조회합니다."""
        valid_types = {"english_law", "treaty", "structure", "oneview", "abbreviation", "deleted"}
        if info_type not in valid_types:
            return {
                "error_code": "INVALID_INPUT",
                "error": f"지원하지 않는 info_type: {info_type}",
                "recovery_guide": "info_type은 english_law / treaty / structure / oneview / abbreviation / deleted 중 하나여야 합니다.",
            }
        if info_type == "english_law":
            if item_id:
                return await self.misc_repo.get_english_law(item_id, arguments)
            return await self.misc_repo.search_english_law(query, page, per_page, arguments)
        elif info_type == "treaty":
            if item_id:
                return await self.misc_repo.get_treaty(item_id, arguments)
            return await self.misc_repo.search_treaty(query, page, per_page, arguments)
        elif info_type == "structure":
            if item_id:
                return await self.misc_repo.get_law_structure(item_id, arguments)
            return await self.misc_repo.search_law_structure(query, page, per_page, arguments)
        elif info_type == "oneview":
            if item_id:
                return await self.misc_repo.get_oneview(item_id, arguments)
            return await self.misc_repo.search_oneview(query, page, per_page, arguments)
        elif info_type == "abbreviation":
            return await self.misc_repo.search_law_abbreviation(query, page, per_page, arguments)
        else:  # deleted
            return await self.misc_repo.search_deleted_history(query, page, per_page, arguments)

    async def law_form_lookup(
        self,
        form_type: str = "law",
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """별표서식을 검색합니다."""
        valid_types = {"law", "admin_rule", "ordinance"}
        if form_type not in valid_types:
            return {
                "error_code": "INVALID_INPUT",
                "error": f"지원하지 않는 form_type: {form_type}",
                "recovery_guide": "form_type은 law / admin_rule / ordinance 중 하나여야 합니다.",
            }
        if form_type == "law":
            return await self.form_repo.search_law_forms(query, page, per_page, arguments)
        elif form_type == "admin_rule":
            return await self.form_repo.search_admin_rule_forms(query, page, per_page, arguments)
        else:  # ordinance
            return await self.form_repo.search_ordinance_forms(query, page, per_page, arguments)

    async def law_link_lookup(
        self,
        link_type: str = "law_to_ordinance",
        query: Optional[str] = None,
        law_id: Optional[str] = None,
        department: Optional[str] = None,
        region_code: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령-자치법규 연계 정보를 조회합니다."""
        valid_types = {
            "law_to_ordinance", "ordinance_articles", "by_department",
            "linked_ordinance", "law_linked_ordinance", "by_region",
        }
        if link_type not in valid_types:
            return {
                "error_code": "INVALID_INPUT",
                "error": f"지원하지 않는 link_type: {link_type}",
                "recovery_guide": "법령 및 자치법규 연계 조회 유형을 올바르게 입력하세요.",
            }
        if link_type == "law_to_ordinance":
            return await self.link_repo.search_law_ordinance_link(query, law_id, page, per_page, arguments)
        elif link_type == "ordinance_articles":
            return await self.link_repo.search_linked_ordinance_articles(query, law_id, page, per_page, arguments)
        elif link_type == "by_department":
            return await self.link_repo.search_link_by_department(query, department, page, per_page, arguments)
        elif link_type == "linked_ordinance":
            return await self.link_repo.search_linked_ordinance(query, page, per_page, arguments)
        elif link_type == "law_linked_ordinance":
            return await self.link_repo.search_law_linked_ordinance(query, law_id, page, per_page, arguments)
        else:  # by_region
            return await self.link_repo.search_link_by_region(query, region_code, page, per_page, arguments)
