"""
응답 포맷터 - API 응답을 구조화된 객체로 변환
apis 폴더의 response_fields를 기반으로 구조화
"""
import json
from typing import Dict, Any, Optional, List


def add_metadata(formatted: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    """
    응답에 메타데이터 추가 (Phase 3 개선)
    
    Args:
        formatted: 포맷팅된 응답
        tool_name: 툴 이름
    
    Returns:
        메타데이터가 추가된 응답
    """
    meta = {}
    
    # clarification_needed 응답 처리
    if formatted.get("clarification_needed"):
        meta["response_type"] = "clarification_needed"
        meta["fields"] = ["clarification_needed", "query", "possible_intents", "suggestion"]
        meta["parsing_hint"] = "results.possible_intents 배열에 가능한 의도 후보가 있습니다. results.suggestion을 참고하여 사용자에게 질문하세요."
        formatted["_meta"] = meta
        return formatted
    
    # 툴별 응답 타입 결정
    response_type_map = {
        "search_law_tool": "law_list",
        "get_law_tool": "law_detail",
        "search_precedent_tool": "precedent_list",
        "get_precedent_tool": "precedent_detail",
        "search_law_interpretation_tool": "interpretation_list",
        "get_law_interpretation_tool": "interpretation_detail",
        "search_administrative_appeal_tool": "administrative_appeal_list",
        "get_administrative_appeal_tool": "administrative_appeal_detail",
        "search_committee_decision_tool": "committee_decision_list",
        "get_committee_decision_tool": "committee_decision_detail",
        "search_constitutional_decision_tool": "constitutional_decision_list",
        "get_constitutional_decision_tool": "constitutional_decision_detail",
        "search_special_administrative_appeal_tool": "special_appeal_list",
        "get_special_administrative_appeal_tool": "special_appeal_detail",
        "compare_laws_tool": "law_comparison",
        "search_local_ordinance_tool": "ordinance_list",
        "search_administrative_rule_tool": "rule_list",
        "smart_search_tool": "integrated_search",
        "situation_guidance_tool": "situation_guidance",
        "document_issue_tool": "document_issue"
    }
    
    meta["response_type"] = response_type_map.get(tool_name, "unknown")
    
    # 주요 필드 목록 추출
    fields = []
    if formatted.get("success"):
        # 성공 응답의 주요 필드
        for key in formatted.keys():
            if key not in ["success", "api_url", "_meta"]:
                fields.append(key)
        # 법적 근거 블록은 최상단 고정
        if "legal_basis_block" in fields:
            fields.remove("legal_basis_block")
            fields.insert(0, "legal_basis_block")
    else:
        # 에러 응답의 주요 필드
        fields = ["error", "recovery_guide"]
    
    meta["fields"] = fields[:10]  # 최대 10개 필드만
    
    # 파싱 힌트 생성
    parsing_hints = {
        "law_list": "results.laws 배열에 법령 목록이 있습니다.",
        "law_detail": "results.detail 또는 results.article에 법령 상세 정보가 있습니다.",
        "precedent_list": "results.precedents 배열에 판례 목록이 있습니다.",
        "precedent_detail": "results.precedent에 판례 상세 정보가 있습니다.",
        "interpretation_list": "results.interpretations 배열에 법령해석 목록이 있습니다.",
        "interpretation_detail": "results.interpretation에 법령해석 상세 정보가 있습니다.",
        "administrative_appeal_list": "results.appeals 배열에 행정심판 목록이 있습니다.",
        "administrative_appeal_detail": "results.appeal에 행정심판 상세 정보가 있습니다.",
        "committee_decision_list": "results.decisions 배열에 위원회 결정문 목록이 있습니다.",
        "committee_decision_detail": "results.decision에 위원회 결정문 상세 정보가 있습니다.",
        "constitutional_decision_list": "results.decisions 배열에 헌재결정 목록이 있습니다.",
        "constitutional_decision_detail": "results.decision에 헌재결정 상세 정보가 있습니다.",
        "special_appeal_list": "results.appeals 배열에 특별행정심판 목록이 있습니다.",
        "special_appeal_detail": "results.appeal에 특별행정심판 상세 정보가 있습니다.",
        "law_comparison": "results.comparison에 법령 비교 결과가 있습니다.",
        "ordinance_list": "results.ordinances 배열에 자치법규 목록이 있습니다.",
        "rule_list": "results.rules 배열에 행정규칙 목록이 있습니다.",
        "integrated_search": "results.results 객체에 검색 타입별 결과가 있습니다. results.detected_intents로 감지된 의도를 확인하세요.",
        "situation_guidance": "results.guidance 배열에 단계별 가이드가 있습니다. results.laws, results.precedents, results.interpretations에 관련 법적 정보가 있습니다.",
        "document_issue": "results.document_analysis에 조항별 이슈와 근거 조회 힌트가 있습니다.",
        "clarification_needed": "results.possible_intents 배열에 가능한 의도 후보가 있습니다. results.suggestion을 참고하여 사용자에게 질문하세요."
    }
    
    meta["parsing_hint"] = parsing_hints.get(meta["response_type"], "응답 구조를 확인하세요.")
    
    # 특수 케이스 처리
    if tool_name == "get_law_tool":
        if formatted.get("article"):
            meta["parsing_hint"] = "results.article.content에 조문 내용이 있습니다."
        elif formatted.get("articles"):
            meta["parsing_hint"] = "results.articles 배열에 조문 목록이 있습니다."
    
    if tool_name == "smart_search_tool":
        if formatted.get("results"):
            result_types = list(formatted.get("results", {}).keys())
            if result_types:
                meta["parsing_hint"] = f"results.results 객체에 {', '.join(result_types)} 타입의 검색 결과가 있습니다."
    
    formatted["_meta"] = meta
    return formatted


def format_search_response(result: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    """
    검색 결과를 구조화된 객체로 포맷팅
    
    Args:
        result: Repository에서 반환한 원본 결과
        tool_name: 툴 이름 (응답 구조 결정용)
    
    Returns:
        구조화된 응답 객체
    """
    if "error" in result:
        return {
            "success": False,
            "error": result["error"],
            "recovery_guide": result.get("recovery_guide"),
            "note": result.get("note"),
            "api_url": result.get("api_url")
        }
    
    # 툴별 구조화
    if tool_name == "search_law_tool":
        return {
            "success": True,
            "query": result.get("query"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 10),
            "total": result.get("total", 0),
            "laws": result.get("laws", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "get_law_tool":
        return {
            "success": True,
            "law_name": result.get("law_name"),
            "law_id": result.get("law_id"),
            "mode": result.get("mode", "detail"),
            "detail": result.get("detail"),
            "articles": result.get("articles"),
            "article": result.get("article"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_precedent_tool":
        return {
            "success": True,
            "query": result.get("query"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "precedents": result.get("precedents", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "get_precedent_tool":
        return {
            "success": True,
            "precedent_id": result.get("precedent_id"),
            "case_number": result.get("case_number"),
            "precedent": result.get("precedent"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_law_interpretation_tool":
        return {
            "success": True,
            "query": result.get("query"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "interpretations": result.get("interpretations", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "get_law_interpretation_tool":
        return {
            "success": True,
            "interpretation_id": result.get("interpretation_id"),
            "interpretation": result.get("interpretation"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_administrative_appeal_tool":
        return {
            "success": True,
            "query": result.get("query"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "appeals": result.get("appeals", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "get_administrative_appeal_tool":
        return {
            "success": True,
            "appeal_id": result.get("appeal_id"),
            "appeal": result.get("appeal"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_committee_decision_tool":
        return {
            "success": True,
            "committee_type": result.get("committee_type"),
            "query": result.get("query"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "decisions": result.get("decisions", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "get_committee_decision_tool":
        return {
            "success": True,
            "committee_type": result.get("committee_type"),
            "decision_id": result.get("decision_id"),
            "decision": result.get("decision"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_constitutional_decision_tool":
        return {
            "success": True,
            "query": result.get("query"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "decisions": result.get("decisions", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "get_constitutional_decision_tool":
        return {
            "success": True,
            "decision_id": result.get("decision_id"),
            "decision": result.get("decision"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_special_administrative_appeal_tool":
        return {
            "success": True,
            "tribunal_type": result.get("tribunal_type"),
            "query": result.get("query"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "appeals": result.get("appeals", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "get_special_administrative_appeal_tool":
        return {
            "success": True,
            "tribunal_type": result.get("tribunal_type"),
            "appeal_id": result.get("appeal_id"),
            "appeal": result.get("appeal"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "compare_laws_tool":
        return {
            "success": True,
            "law_name": result.get("law_name"),
            "compare_type": result.get("compare_type"),
            "comparison": result.get("comparison"),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_local_ordinance_tool":
        return {
            "success": True,
            "query": result.get("query"),
            "local_government": result.get("local_government"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "ordinances": result.get("ordinances", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "search_administrative_rule_tool":
        return {
            "success": True,
            "query": result.get("query"),
            "agency": result.get("agency"),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "total": result.get("total", 0),
            "rules": result.get("rules", []),
            "api_url": result.get("api_url")
        }
    
    elif tool_name == "smart_search_tool":
        # clarification_needed 응답 처리 (Phase 3 개선)
        if result.get("clarification_needed"):
            return {
                "success": False,
                "clarification_needed": True,
                "query": result.get("query"),
                "possible_intents": result.get("possible_intents", []),
                "suggestion": result.get("suggestion", "")
            }
        
        legal_basis_block = {
            "summary": result.get("legal_basis_summary"),
            "citations": result.get("citations", []),
            "fallback": result.get("fallback_legal_basis"),
            "missing_reason": result.get("missing_reason")
        }
        formatted = {
            "success": result.get("success", True),
            "success_transport": result.get("success_transport", True),
            "success_search": result.get("success_search", result.get("success", True)),
            "query": result.get("query"),
            "detected_intents": result.get("detected_intents", []),
            "results": result.get("results", {}),
            "total_types": result.get("total_types", 0),
            "sources_count": result.get("sources_count"),
            "missing_reason": result.get("missing_reason"),
            "legal_basis_summary": result.get("legal_basis_summary"),
            "legal_basis_block": legal_basis_block,
            "citations": result.get("citations", []),
            "one_line_answer": result.get("one_line_answer"),
            "next_questions": result.get("next_questions", []),
            "fallback_legal_basis": result.get("fallback_legal_basis"),
            "legal_basis_block_text": result.get("legal_basis_block_text"),
            "response_policy": result.get("response_policy"),
            "errors": result.get("errors")
        }
        # 부분 실패 처리 필드 추가 (Phase 2 개선)
        if "partial_success" in result:
            formatted["partial_success"] = result["partial_success"]
        if "successful_types" in result:
            formatted["successful_types"] = result["successful_types"]
        if "failed_types" in result:
            formatted["failed_types"] = result["failed_types"]
        if "note" in result:
            formatted["note"] = result["note"]
        return formatted
    
    elif tool_name == "situation_guidance_tool":
        legal_basis_block = {
            "summary": result.get("legal_basis_summary"),
            "citations": result.get("citations", []),
            "fallback": result.get("fallback_legal_basis"),
            "missing_reason": result.get("missing_reason")
        }
        return {
            "success": result.get("success", True),
            "success_transport": result.get("success_transport", True),
            "success_search": result.get("success_search", result.get("success", True)),
            "has_legal_basis": result.get("has_legal_basis"),
            "missing_reason": result.get("missing_reason"),
            "situation": result.get("situation"),
            "detected_domains": result.get("detected_domains", []),
            "laws": result.get("laws", {}),
            "precedents": result.get("precedents", {}),
            "interpretations": result.get("interpretations", {}),
            "administrative_appeals": result.get("administrative_appeals", {}),
            "sources_count": result.get("sources_count"),
            "legal_basis_summary": result.get("legal_basis_summary"),
            "legal_basis_block": legal_basis_block,
            "citations": result.get("citations", []),
            "one_line_answer": result.get("one_line_answer"),
            "fallback_legal_basis": result.get("fallback_legal_basis"),
            "legal_basis_block_text": result.get("legal_basis_block_text"),
            "document_analysis": result.get("document_analysis"),
            "errors": result.get("errors"),
            "response_policy": result.get("response_policy"),
            "guidance": result.get("guidance", []),
            "summary": result.get("summary")
        }
    
    elif tool_name == "document_issue_tool":
        def _citation_title(item: Any) -> Optional[str]:
            if isinstance(item, dict):
                return (
                    item.get("title")
                    or item.get("name")
                    or item.get("case_number")
                    or item.get("caseNumber")
                    or item.get("article")
                    or item.get("article_number")
                    or item.get("id")
                )
            if isinstance(item, str):
                return item
            return None

        raw_answer = result.get("answer") if isinstance(result, dict) else {}
        raw_risks = raw_answer.get("risk_findings", []) if isinstance(raw_answer, dict) else []
        trimmed_risks = []
        for item in raw_risks[:3]:
            if not isinstance(item, dict):
                continue
            citations = []
            for c in item.get("citations", []) or []:
                title = _citation_title(c)
                if title:
                    citations.append(str(title))
            trimmed_risks.append({
                "clause": item.get("clause"),
                "why": item.get("why"),
                "citations": citations[:2]
            })

        citations_raw = []
        if isinstance(result.get("legal_basis_block"), dict):
            citations_raw = result.get("legal_basis_block", {}).get("citations", []) or []
        if not citations_raw:
            citations_raw = result.get("citations", []) or []
        citations = []
        for c in citations_raw:
            title = _citation_title(c)
            if title:
                citations.append(str(title))
        citations = list(dict.fromkeys(citations))[:5]

        return {
            "success": result.get("success", True),
            "success_transport": result.get("success_transport", True),
            "success_search": result.get("success_search", result.get("success", True)),
            "auto_search": result.get("auto_search"),
            "analysis_success": result.get("analysis_success"),
            "has_legal_basis": result.get("has_legal_basis"),
            "missing_reason": result.get("missing_reason"),
            "document_analysis": result.get("document_analysis"),
            "answer": {"risk_findings": trimmed_risks},
            "citations": citations,
            "legal_basis_block_text": result.get("legal_basis_block_text"),
            "retry_plan": result.get("retry_plan"),
            "response_policy": result.get("response_policy")
        }
    
    # 기본: 원본 반환 (구조가 유동적인 경우)
    return result


def format_mcp_response(result: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    """
    MCP 응답 포맷으로 변환 (content 배열 포함)
    
    Args:
        result: Repository에서 반환한 원본 결과
        tool_name: 툴 이름
    
    Returns:
        MCP 표준 포맷: {"content": [{"type": "text", "text": "..."}], "isError": bool}
    """
    # 구조화된 응답 생성
    formatted = format_search_response(result, tool_name)
    
    # 메타데이터 추가 (Phase 3 개선)
    formatted = add_metadata(formatted, tool_name)
    
    # JSON 문자열로 변환
    formatted_json = json.dumps(formatted, ensure_ascii=False)

    contents = []
    
    # A 타입 형식 리마인더 추가 (legal_qa_tool, document_issue_tool에만)
    if tool_name in ["legal_qa_tool", "document_issue_tool"]:
        if tool_name == "legal_qa_tool":
            template_reminder = """답변 형식 (A 타입, 반드시 준수):
1) 한 줄 방향 제시 (예: 문제가 될 가능성이 있는 사안입니다)
2) 체크리스트 3개 이하
3) 관련 법령/판례 방향만 언급
4) 판단 유보 문장
5) 추가 정보 요청
금지: 이모지, 타이틀, 조문 전체 인용, 단정적 결론"""
        else:  # document_issue_tool
            template_reminder = """답변 형식 (A 타입, 반드시 준수):
1) 한 줄 평가
2) 주요 쟁점 조항 나열 (제○조: 문제점 2-3개)
3) 관련 법령/판례 방향만 언급
4) 판단 유보 문장
5) 추가 정보 요청
금지: 이모지, 타이틀, 심각도 표시, 조문 전체 인용, 단정적 조언"""
        
        contents.append({
            "type": "text",
            "text": template_reminder
        })
    
    if tool_name == "document_issue_tool":
        auto_search = formatted.get("auto_search")
        success_search = formatted.get("success_search")
        missing_reason = formatted.get("missing_reason")
        if auto_search and not success_search:
            if missing_reason == "API_ERROR_HTML":
                notice = "⚠️ 법령/판례 API가 HTML 안내 페이지를 반환하여 근거를 불러오지 못했습니다."
            elif missing_reason == "API_ERROR_AUTH":
                notice = "⚠️ 법령/판례 API 키 설정이 필요합니다. LAW_API_KEY 또는 LAWGOKR_OC를 확인하세요."
            elif missing_reason == "API_ERROR_TIMEOUT":
                notice = "⚠️ 법령/판례 API 호출이 타임아웃되었습니다. 잠시 후 재시도하세요."
            else:
                notice = "⚠️ 법적 근거 검색에 실패했습니다. 잠시 후 다시 시도하세요."
            contents.append({
                "type": "text",
                "text": notice
            })
    contents.append({
        "type": "text",
        "text": formatted_json
    })
    
    # 에러 여부 확인
    is_error = not formatted.get("success", True) or "error" in formatted
    
    return {
        "content": contents,
        "structuredContent": formatted,
        "isError": is_error
    }

