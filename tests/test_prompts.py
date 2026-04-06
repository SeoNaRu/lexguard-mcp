"""
MCP Prompts 엔드포인트 테스트

prompts/list, prompts/get의 응답 구조와 내용을 검증.
"""
from src.routes.mcp_routes import _build_prompts_list, _get_prompt


EXPECTED_PROMPT_NAMES = {
    "legal_basis_answer",
    "precedent_summary",
    "contract_risk_check",
    "labor_contract_review",
    "legal_qa",
}


# ---------------------------------------------------------------------------
# prompts/list
# ---------------------------------------------------------------------------

class TestPromptsList:
    def test_returns_list(self):
        result = _build_prompts_list()
        assert isinstance(result, list)

    def test_correct_count(self):
        result = _build_prompts_list()
        assert len(result) == len(EXPECTED_PROMPT_NAMES)

    def test_all_expected_names_present(self):
        result = _build_prompts_list()
        names = {p["name"] for p in result}
        assert names == EXPECTED_PROMPT_NAMES

    def test_each_prompt_has_required_fields(self):
        result = _build_prompts_list()
        for prompt in result:
            assert "name" in prompt, f"name 필드 없음: {prompt}"
            assert "description" in prompt, f"description 필드 없음: {prompt['name']}"
            assert "arguments" in prompt, f"arguments 필드 없음: {prompt['name']}"

    def test_description_not_empty(self):
        result = _build_prompts_list()
        for prompt in result:
            assert prompt["description"].strip(), f"description 비어있음: {prompt['name']}"

    def test_arguments_are_list(self):
        result = _build_prompts_list()
        for prompt in result:
            assert isinstance(prompt["arguments"], list), \
                f"arguments가 리스트 아님: {prompt['name']}"

    def test_arguments_have_name_and_required(self):
        result = _build_prompts_list()
        for prompt in result:
            for arg in prompt["arguments"]:
                assert "name" in arg, f"argument에 name 없음: {prompt['name']}"
                assert "required" in arg, f"argument에 required 없음: {prompt['name']}"

    def test_legal_basis_answer_has_required_question_arg(self):
        result = _build_prompts_list()
        prompt = next(p for p in result if p["name"] == "legal_basis_answer")
        required_args = [a for a in prompt["arguments"] if a["required"]]
        names = [a["name"] for a in required_args]
        assert "question" in names

    def test_contract_risk_check_has_required_contract_text(self):
        result = _build_prompts_list()
        prompt = next(p for p in result if p["name"] == "contract_risk_check")
        required_args = [a for a in prompt["arguments"] if a["required"]]
        names = [a["name"] for a in required_args]
        assert "contract_text" in names

    def test_precedent_summary_has_optional_court_arg(self):
        result = _build_prompts_list()
        prompt = next(p for p in result if p["name"] == "precedent_summary")
        optional_args = [a for a in prompt["arguments"] if not a["required"]]
        names = [a["name"] for a in optional_args]
        assert "court" in names


# ---------------------------------------------------------------------------
# prompts/get
# ---------------------------------------------------------------------------

class TestPromptsGet:
    def test_unknown_prompt_returns_none(self):
        result = _get_prompt("nonexistent_prompt", {})
        assert result is None

    def test_empty_name_returns_none(self):
        result = _get_prompt("", {})
        assert result is None

    def test_legal_basis_answer_basic(self):
        result = _get_prompt("legal_basis_answer", {"question": "부당해고 요건은?"})
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) >= 1

    def test_legal_basis_answer_question_in_message(self):
        question = "퇴직금 계산 방법은?"
        result = _get_prompt("legal_basis_answer", {"question": question})
        text = result["messages"][0]["content"]["text"]
        assert question in text

    def test_legal_basis_answer_empty_args(self):
        result = _get_prompt("legal_basis_answer", {})
        assert result is not None
        assert "messages" in result

    def test_precedent_summary_with_topic(self):
        result = _get_prompt("precedent_summary", {"topic": "부당해고"})
        assert result is not None
        text = result["messages"][0]["content"]["text"]
        assert "부당해고" in text

    def test_precedent_summary_with_court(self):
        result = _get_prompt("precedent_summary", {"topic": "손해배상", "court": "대법원"})
        text = result["messages"][0]["content"]["text"]
        assert "대법원" in text

    def test_precedent_summary_without_court(self):
        result = _get_prompt("precedent_summary", {"topic": "손해배상"})
        text = result["messages"][0]["content"]["text"]
        # court 생략 시 court 관련 텍스트 없어야 함
        assert "대상 법원" not in text

    def test_contract_risk_check_with_text(self):
        contract = "제5조 위약금은 계약금의 500%로 한다."
        result = _get_prompt("contract_risk_check", {"contract_text": contract})
        assert result is not None
        text = result["messages"][0]["content"]["text"]
        assert contract in text

    def test_contract_risk_check_with_type(self):
        result = _get_prompt("contract_risk_check", {
            "contract_text": "계약서 내용",
            "contract_type": "프리랜서 계약서"
        })
        text = result["messages"][0]["content"]["text"]
        assert "프리랜서 계약서" in text

    def test_legal_qa_with_situation(self):
        situation = "퇴직 후 퇴직금을 받지 못했습니다"
        result = _get_prompt("legal_qa", {"situation": situation})
        assert result is not None
        text = result["messages"][0]["content"]["text"]
        assert situation in text

    def test_legal_qa_with_domain(self):
        result = _get_prompt("legal_qa", {
            "situation": "급여 미지급",
            "domain": "노동"
        })
        text = result["messages"][0]["content"]["text"]
        assert "노동" in text

    def test_all_prompts_messages_have_role_and_content(self):
        for name in EXPECTED_PROMPT_NAMES:
            result = _get_prompt(name, {"question": "테스트", "topic": "테스트",
                                         "contract_text": "테스트", "situation": "테스트"})
            assert result is not None, f"{name} 프롬프트가 None 반환"
            for msg in result["messages"]:
                assert "role" in msg, f"{name}: message에 role 없음"
                assert "content" in msg, f"{name}: message에 content 없음"
                assert "type" in msg["content"], f"{name}: content에 type 없음"
                assert "text" in msg["content"], f"{name}: content에 text 없음"

    def test_all_prompts_have_disclaimer(self):
        """모든 프롬프트에 판단 유보 문장 포함 확인"""
        args_map = {
            "legal_basis_answer": {"question": "테스트 질문"},
            "precedent_summary": {"topic": "손해배상"},
            "contract_risk_check": {"contract_text": "제1조 계약"},
            "labor_contract_review": {"contract_text": "제1조 시험"},
            "legal_qa": {"situation": "테스트 상황"},
        }
        disclaimer_keywords = ["법적 판단을 대신하지 않", "법적 자문을 대신하지 않"]
        for name, args in args_map.items():
            result = _get_prompt(name, args)
            text = result["messages"][0]["content"]["text"]
            has_disclaimer = any(kw in text for kw in disclaimer_keywords)
            assert has_disclaimer, f"{name}: 판단 유보 문장 없음"
