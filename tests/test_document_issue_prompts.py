# -*- coding: utf-8 -*-
"""document_issue_prompts 회귀: 공통·addon 분리, 위험도 기준, 도구 설명 길이, manifest 동기화."""

import json
from pathlib import Path

import pytest

from src.utils.document_issue_prompts import (
    COMMON_CONTRACT_REVIEW_INSTRUCTION,
    DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT,
    DOCUMENT_ISSUE_TOOL_MANIFEST_ONE_LINE,
    GENERIC_CONTRACT_REVIEW_ADDON,
    GENERIC_DOCUMENT_REVIEW_INSTRUCTION,
    LABOR_CONTRACT_REVIEW_ADDON,
    LABOR_CONTRACT_REVIEW_INSTRUCTION,
    RISK_LEVEL_CRITERIA_COMMON,
    RISK_LEVEL_CRITERIA_GENERIC,
    RISK_LEVEL_CRITERIA_LABOR,
    get_document_issue_review_instruction,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_generic_is_common_plus_generic_addon():
    assert GENERIC_DOCUMENT_REVIEW_INSTRUCTION == COMMON_CONTRACT_REVIEW_INSTRUCTION + GENERIC_CONTRACT_REVIEW_ADDON
    assert "범용 계약서 검토 보강" in GENERIC_CONTRACT_REVIEW_ADDON
    assert "포트폴리오" in GENERIC_CONTRACT_REVIEW_ADDON


def test_get_document_issue_review_instruction_routes_labor():
    assert get_document_issue_review_instruction("labor") == LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert get_document_issue_review_instruction(None) == GENERIC_DOCUMENT_REVIEW_INSTRUCTION
    assert get_document_issue_review_instruction("other") == GENERIC_DOCUMENT_REVIEW_INSTRUCTION


def test_labor_is_common_plus_addon():
    assert LABOR_CONTRACT_REVIEW_INSTRUCTION == COMMON_CONTRACT_REVIEW_INSTRUCTION + LABOR_CONTRACT_REVIEW_ADDON


def test_labor_instruction_embeds_labor_risk_criteria():
    assert RISK_LEVEL_CRITERIA_LABOR in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "[위험도 판정 기준" in RISK_LEVEL_CRITERIA_COMMON
    assert RISK_LEVEL_CRITERIA_COMMON in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "임금체불" in RISK_LEVEL_CRITERIA_LABOR
    assert "인수인계" in RISK_LEVEL_CRITERIA_LABOR


def test_labor_instruction_enforces_six_labels_and_summary_headings():
    """B 타입: 조항별 6라벨·전체 총평 5라벨·디스클레이머 1문장 강제 — 공통·근로 동일 골격."""
    labels = (
        "[문제 조항]",
        "[법적 쟁점]",
        "[관련 법적 근거]",
        "[왜 문제인지]",
        "[위험도]",
        "[실무상 수정 방향]",
        "[전체 유효성 평가]",
        "[즉시 수정 권고 조항]",
        "[운용 방식 확인 필요 조항]",
        "[법적 근거가 비교적 명확한 조항]",
        "[최종 유의사항]",
    )
    for lab in (COMMON_CONTRACT_REVIEW_INSTRUCTION, LABOR_CONTRACT_REVIEW_INSTRUCTION):
        for label in labels:
            assert label in lab
        assert "동일·유사 유보 문장" in lab
        assert "첫 줄:" in lab or "첫 줄" in lab
    assert "기간제 및 단시간근로자 보호 등에 관한 법률」 제4조" in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "근로자퇴직급여 보장법」 제9조" in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "(가)" in LABOR_CONTRACT_REVIEW_INSTRUCTION and "(라)" in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "【1층 — 경업금지약정" in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "【2층 — 위약금" in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "내부 분류·작성용 표기" in COMMON_CONTRACT_REVIEW_INSTRUCTION
    assert "풀어쓴다" in COMMON_CONTRACT_REVIEW_INSTRUCTION
    assert "교육비·훈련비 반환 약정" in LABOR_CONTRACT_REVIEW_INSTRUCTION
    assert "한 단계 엄격히" in LABOR_CONTRACT_REVIEW_INSTRUCTION


def test_common_has_cross_cutting_review_points():
    assert "자동 갱신" in COMMON_CONTRACT_REVIEW_INSTRUCTION or "묵시 갱신" in COMMON_CONTRACT_REVIEW_INSTRUCTION
    assert "전속합의관할" in COMMON_CONTRACT_REVIEW_INSTRUCTION or "관할" in COMMON_CONTRACT_REVIEW_INSTRUCTION
    assert "지식재산" in COMMON_CONTRACT_REVIEW_INSTRUCTION
    assert "비용 전가" in COMMON_CONTRACT_REVIEW_INSTRUCTION or "실비" in COMMON_CONTRACT_REVIEW_INSTRUCTION


def test_generic_instruction_embeds_common_risk_criteria():
    assert RISK_LEVEL_CRITERIA_GENERIC in GENERIC_DOCUMENT_REVIEW_INSTRUCTION
    assert RISK_LEVEL_CRITERIA_GENERIC is RISK_LEVEL_CRITERIA_COMMON
    assert "[위험도 판정 기준" in GENERIC_DOCUMENT_REVIEW_INSTRUCTION
    assert "거래 관행" in RISK_LEVEL_CRITERIA_GENERIC


def test_document_issue_tool_description_text_sane_length():
    """전체 설명문이 비어 있거나 과도하게 짧아지는 회귀 방지."""
    text = DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT
    assert 80 <= len(text) <= 4000, f"unexpected length {len(text)}"
    assert "COMMON_CONTRACT_REVIEW_INSTRUCTION" in text
    assert "LABOR_CONTRACT_REVIEW_ADDON" in text


def test_manifest_document_issue_tool_description_matches_constant():
    """mcp/manifest.json 의 document_issue_tool 설명이 단일 출처 상수와 일치해야 함."""
    manifest_path = _repo_root() / "mcp" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    tools = data.get("tools") or []
    doc_tool = next((t for t in tools if t.get("name") == "document_issue_tool"), None)
    assert doc_tool is not None
    assert doc_tool.get("description") == DOCUMENT_ISSUE_TOOL_MANIFEST_ONE_LINE


def test_manifest_one_line_aligns_with_full_description_keywords():
    """한 줄 요약이 전체 설명문과 같은 주제를 가리키는지(키워드 정합)."""
    full = DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT
    one = DOCUMENT_ISSUE_TOOL_MANIFEST_ONE_LINE
    for kw in ("계약서", "addon", "조문"):
        assert kw in one
    assert "계약서" in full or "약관" in full
