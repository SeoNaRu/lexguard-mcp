# contract_risk_check

**MCP prompts/get name:** `contract_risk_check`

**설명:** 범용 계약·약관 위험 조항 점검. 답변 지시는 `COMMON_CONTRACT_REVIEW_INSTRUCTION` + `GENERIC_CONTRACT_REVIEW_ADDON` = `GENERIC_DOCUMENT_REVIEW_INSTRUCTION`(`document_issue_prompts.py`). 근로·용역 전용은 `labor_contract_review` 또는 `document_issue_tool`(근로 분류)을 사용합니다.

**인자**

- `contract_text` (필수): 계약서 또는 약관 전문
- `contract_type` (선택): 계약 유형

**유의:** 본 템플릿은 정보 탐색용이며 법적 자문을 대체하지 않습니다.
