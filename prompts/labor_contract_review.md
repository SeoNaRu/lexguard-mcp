# labor_contract_review

**MCP prompts/get name:** `labor_contract_review`

**설명:** 근로·용역 계약서를 `document_issue_tool`의 B 타입(고밀도) 지시와 같은 구조로 검토하도록 유도합니다.

**인자**

- `contract_text` (필수): 계약서 전문

**구현 참고**

- 근로 검토: `COMMON_CONTRACT_REVIEW_INSTRUCTION` + `LABOR_CONTRACT_REVIEW_ADDON` = `LABOR_CONTRACT_REVIEW_INSTRUCTION` (`document_issue_prompts.py`). 범용 계약: `COMMON_CONTRACT_REVIEW_INSTRUCTION` + `GENERIC_CONTRACT_REVIEW_ADDON` = `GENERIC_DOCUMENT_REVIEW_INSTRUCTION`. 도구 설명문: `DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT`.
- MCP `document_issue_tool` + `document_type_code == "labor"`일 때 위와 동일한 합성 지시문이 리마인더로 붙습니다.
