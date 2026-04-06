"""
테스트 공통 설정 및 픽스처

API 키 없이 동작하는 순수 로직 테스트가 기본.
실제 API 호출 테스트는 LAW_API_KEY 환경변수가 있을 때만 실행.
"""
import os
import pytest
import asyncio


# ---------------------------------------------------------------------------
# 이벤트 루프
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# 샘플 데이터
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_queries():
    return {
        "labor_worker": "프리랜서인데 근로자성 인정된 판례 있나요?",
        "labor_termination": "최근 3년 부당해고 판례 알려줘",
        "personal_info": "개인정보 유출됐는데 법적으로 어떻게 되나요?",
        "tax": "종합소득세 부과 처분에 이의를 제기하고 싶어요",
        "real_estate": "전세 보증금 반환 거부 당했습니다",
        "constitutional": "헌법재판소 위헌 결정 찾아줘",
        "ambiguous": "법",
        "law_article": "형법 제250조 제1항",
        "time_recent_3y": "최근 3년 판례",
        "time_after_2022": "2022년 이후 판례",
        "time_range": "2020년부터 2023년까지 판례",
        "precedent_number": "대법원 2019다12345",
    }


@pytest.fixture
def sample_contract_text():
    return """
제1조 (계약기간)
본 계약의 기간은 2024년 1월 1일부터 2024년 12월 31일까지로 한다.

제5조 (손해배상)
갑의 요청으로 업무를 중단하는 경우, 을은 계약금의 300%를 위약금으로 지급한다.

제7조 (전속 계약)
을은 계약 기간 중 갑의 경쟁사와 어떠한 형태의 계약도 체결할 수 없다.

제10조 (관할법원)
본 계약과 관련된 분쟁은 갑의 소재지 법원을 전속 관할로 한다.
"""


@pytest.fixture
def has_api_key():
    """API 키 존재 여부 확인"""
    key = os.environ.get("LAW_API_KEY", "") or os.environ.get("LAWGOKR_OC", "")
    return bool(key and key.strip() and key not in {"your_api_key", "test", "dummy"})


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_api: API 키가 필요한 통합 테스트 (LAW_API_KEY 환경변수)"
    )
    config.addinivalue_line(
        "markers", "requires_eflaw_e2e: eflawjosub 실네트워크 스모크 (LEXGUARD_RUN_EFLAW_E2E=1)"
    )


def pytest_collection_modifyitems(config, items):
    """requires_eflaw_e2e: LEXGUARD_RUN_EFLAW_E2E!=1 이면 스킵"""
    if os.environ.get("LEXGUARD_RUN_EFLAW_E2E") == "1":
        return
    skip_e2e = pytest.mark.skip(reason="LEXGUARD_RUN_EFLAW_E2E=1 일 때만 실행")
    for item in items:
        if "requires_eflaw_e2e" in [m.name for m in item.iter_markers()]:
            item.add_marker(skip_e2e)
