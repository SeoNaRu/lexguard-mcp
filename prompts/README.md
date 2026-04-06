# MCP Prompts (정적 인덱스)

이 디렉터리는 마켓플레이스·문서 도구가 **프롬프트 제공 여부**를 스캔할 때 참고할 수 있도록, `prompts/get`과 동일한 이름의 템플릿을 둡니다.

런타임 동작은 서버의 JSON-RPC `prompts/list`, `prompts/get`이 authoritative입니다.

| 파일 | MCP 이름 |
|------|----------|
| legal_basis_answer.md | `legal_basis_answer` |
| precedent_summary.md | `precedent_summary` |
| contract_risk_check.md | `contract_risk_check` |
| labor_contract_review.md | `labor_contract_review` |
| legal_qa.md | `legal_qa` |
