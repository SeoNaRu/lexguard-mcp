"""
LocalOrdinanceRepository — org/sborg 코드 매핑 + 에러 응답 일관성 검증.

PR #16에서 도입된 _ORG_CODE_MAP / _SBORG_CODE_MAP 사전에 대한 회귀 방지 테스트.
검색 호출 흐름의 에러 응답에 error_code='INVALID_INPUT'이 포함되는지도 검증.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.repositories.local_ordinance_repository import (
    LocalOrdinanceRepository,
    _ORG_CODE_MAP,
    _SBORG_CODE_MAP,
    _resolve_org_code,
    _resolve_sborg_code,
)


def make_mock_response(body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = json.dumps(body, ensure_ascii=False)
    mock_resp.json = MagicMock(return_value=body)
    mock_resp.url = "https://www.law.go.kr/DRF/lawSearch.do"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ---------------------------------------------------------------------------
# _resolve_org_code 단위
# ---------------------------------------------------------------------------


def test_org_full_name_resolves():
    assert _resolve_org_code("서울특별시") == "6110000"
    assert _resolve_org_code("부산광역시") == "6260000"
    assert _resolve_org_code("제주특별자치도") == "6500000"


def test_org_short_form_resolves_to_same_code():
    """약식 명칭(서울/부산/제주)도 풀네임과 동일 코드."""
    assert _resolve_org_code("서울") == _resolve_org_code("서울특별시") == "6110000"
    assert _resolve_org_code("부산") == _resolve_org_code("부산광역시") == "6260000"
    assert _resolve_org_code("경기") == _resolve_org_code("경기도") == "6410000"


def test_org_si_variant_resolves():
    """광역시/특별자치시 약칭에 '시' 붙은 변형도 처리."""
    assert _resolve_org_code("서울시") == "6110000"
    assert _resolve_org_code("부산시") == "6260000"
    assert _resolve_org_code("세종시") == "5690000"


def test_org_unknown_returns_none():
    assert _resolve_org_code("화성") is None  # 시 이름이라 광역 매핑 없음
    assert _resolve_org_code("존재하지않는지역") is None
    assert _resolve_org_code("") is None


def test_org_numeric_code_passthrough():
    """이미 숫자 코드를 넣으면 그대로 통과 (사전 우회)."""
    assert _resolve_org_code("6110000") == "6110000"
    assert _resolve_org_code("9999999") == "9999999"  # 사전에 없어도 숫자면 통과


def test_org_code_consistency_count():
    """광역 17개 모두 매핑되어 있는지 (시도 변형 포함)."""
    seoul_codes = [code for name, code in _ORG_CODE_MAP.items() if "서울" in name]
    busan_codes = [code for name, code in _ORG_CODE_MAP.items() if "부산" in name]
    assert all(c == "6110000" for c in seoul_codes)
    assert all(c == "6260000" for c in busan_codes)
    # 광역 17개 (서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주)
    unique_codes = set(_ORG_CODE_MAP.values())
    assert len(unique_codes) == 17, f"광역 코드는 17개여야: {sorted(unique_codes)}"


# ---------------------------------------------------------------------------
# _resolve_sborg_code 단위 — 동명 구 충돌 방지 핵심
# ---------------------------------------------------------------------------


def test_sborg_seoul_jung_gu():
    """서울 중구는 3010000."""
    assert _resolve_sborg_code("6110000", "중구") == "3010000"


def test_sborg_busan_jung_gu_different_from_seoul():
    """부산 중구는 3250000. 같은 '중구'라도 광역에 따라 다른 코드."""
    busan_jung = _resolve_sborg_code("6260000", "중구")
    seoul_jung = _resolve_sborg_code("6110000", "중구")
    assert busan_jung == "3250000"
    assert seoul_jung != busan_jung, "동명 구가 광역마다 다른 코드여야 함"


def test_sborg_daegu_jung_gu_separate():
    """대구 중구도 별도 코드."""
    daegu_jung = _resolve_sborg_code("6270000", "중구")
    assert daegu_jung == "3410000"
    assert daegu_jung not in (_resolve_sborg_code("6110000", "중구"), _resolve_sborg_code("6260000", "중구"))


def test_sborg_unknown_district_returns_none():
    assert _resolve_sborg_code("6110000", "없는구") is None


def test_sborg_unknown_org_returns_none():
    """광역 코드 자체가 사전에 없으면 None."""
    assert _resolve_sborg_code("9999999", "구로구") is None


def test_sborg_numeric_code_passthrough():
    """sborg 숫자 코드 직접 입력 시 그대로 통과."""
    assert _resolve_sborg_code("6110000", "3160000") == "3160000"


def test_sborg_seoul_districts_all_unique():
    """서울 25개 구가 모두 고유한 sborg 코드."""
    seoul_sborgs = _SBORG_CODE_MAP.get("6110000", {})
    codes = list(seoul_sborgs.values())
    assert len(codes) == len(set(codes)), "서울 구들의 sborg 코드는 모두 고유해야"
    assert len(seoul_sborgs) >= 25  # 서울은 25개 구


# ---------------------------------------------------------------------------
# 통합 — error 응답에 error_code 일관성
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsupported_local_government_returns_error_code():
    """미지원 광역 → error_code='INVALID_INPUT' 포함."""
    repo = LocalOrdinanceRepository()
    result = await repo.search_local_ordinance(
        query="청소년",
        local_government="존재하지않는지역",
        arguments={"env": {"LAW_API_KEY": "testkey123"}},
    )
    assert result.get("error_code") == "INVALID_INPUT"
    assert "지원하지 않는 지자체" in result.get("error", "")
    assert "recovery_guide" in result


@pytest.mark.asyncio
async def test_unsupported_sub_local_government_returns_error_code():
    """광역은 매핑되는데 시·군·구가 매핑 안 됨 → error_code='INVALID_INPUT'."""
    repo = LocalOrdinanceRepository()
    result = await repo.search_local_ordinance(
        query="청소년",
        local_government="서울",
        sub_local_government="없는구",
        arguments={"env": {"LAW_API_KEY": "testkey123"}},
    )
    assert result.get("error_code") == "INVALID_INPUT"
    assert "시·군·구" in result.get("error", "")


@pytest.mark.asyncio
async def test_sub_without_local_government_returns_error_code():
    """sub_local_government만 단독으로 → error_code='INVALID_INPUT'."""
    repo = LocalOrdinanceRepository()
    result = await repo.search_local_ordinance(
        query="청소년",
        local_government=None,
        sub_local_government="구로구",
        arguments={"env": {"LAW_API_KEY": "testkey123"}},
    )
    assert result.get("error_code") == "INVALID_INPUT"
    assert "local_government" in result.get("error", "")


@pytest.mark.asyncio
async def test_valid_org_and_sborg_attaches_codes_to_params():
    """정상 케이스: org/sborg 파라미터가 API 호출에 정확히 들어가는지."""
    fixture = {"OrdinSearch": {"totalCnt": "0"}}
    repo = LocalOrdinanceRepository()
    captured_params = {}

    async def fake_aget(url, params=None, timeout=None):
        captured_params.update(params or {})
        return make_mock_response(fixture)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        await repo.search_local_ordinance(
            query="청소년",
            local_government="서울",
            sub_local_government="구로구",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert captured_params.get("org") == "6110000"
    assert captured_params.get("sborg") == "3160000"
