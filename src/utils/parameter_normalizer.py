"""
파라미터 정규화 유틸리티
LLM이 다양한 형식으로 입력한 파라미터를 정규화합니다.
"""
import re
from typing import Optional


def normalize_article_number(article_number: Optional[str]) -> Optional[str]:
    """
    조 번호를 정규화합니다.
    
    지원 형식:
    - "1" → "제1조"
    - "1조" → "제1조"
    - "제1조" → "제1조" (그대로)
    - "10" → "제10조"
    - "제10조의2" → "제10조의2" (그대로)
    
    Args:
        article_number: 조 번호 문자열
        
    Returns:
        정규화된 조 번호 문자열 (예: "제1조")
    """
    if not article_number:
        return None
    
    article_number = article_number.strip()
    
    # 이미 "제"로 시작하고 "조"로 끝나면 그대로 반환
    if article_number.startswith("제") and article_number.endswith("조"):
        return article_number
    
    # 숫자만 있으면 "제{숫자}조" 형식으로 변환
    if article_number.isdigit():
        return f"제{article_number}조"
    
    # "조"로 끝나지만 "제"가 없으면 "제" 추가
    if article_number.endswith("조") and not article_number.startswith("제"):
        return f"제{article_number}"
    
    # 숫자로 시작하고 "조"가 없으면 "제{숫자}조" 형식으로 변환
    match = re.match(r'^(\d+)', article_number)
    if match:
        number = match.group(1)
        # "의" 뒤의 숫자가 있는지 확인
        if '의' in article_number:
            # "10의2" → "제10조의2"
            sub_match = re.search(r'의\s*(\d+)', article_number)
            if sub_match:
                sub_number = sub_match.group(1)
                return f"제{number}조의{sub_number}"
        return f"제{number}조"
    
    # 그 외는 그대로 반환
    return article_number


def normalize_hang(hang: Optional[str]) -> Optional[str]:
    """
    항 번호를 정규화합니다.
    
    지원 형식:
    - "1" → "제1항"
    - "1항" → "제1항"
    - "제1항" → "제1항" (그대로)
    
    Args:
        hang: 항 번호 문자열
        
    Returns:
        정규화된 항 번호 문자열 (예: "제1항")
    """
    if not hang:
        return None
    
    hang = hang.strip()
    
    # 이미 "제"로 시작하고 "항"으로 끝나면 그대로 반환
    if hang.startswith("제") and hang.endswith("항"):
        return hang
    
    # 숫자만 있으면 "제{숫자}항" 형식으로 변환
    if hang.isdigit():
        return f"제{hang}항"
    
    # "항"으로 끝나지만 "제"가 없으면 "제" 추가
    if hang.endswith("항") and not hang.startswith("제"):
        return f"제{hang}"
    
    # 숫자로 시작하고 "항"이 없으면 "제{숫자}항" 형식으로 변환
    match = re.match(r'^(\d+)', hang)
    if match:
        number = match.group(1)
        return f"제{number}항"
    
    # 그 외는 그대로 반환
    return hang


def normalize_ho(ho: Optional[str]) -> Optional[str]:
    """
    호 번호를 정규화합니다.
    
    지원 형식:
    - "1" → "제1호"
    - "1호" → "제1호"
    - "제1호" → "제1호" (그대로)
    - "제10호의2" → "제10호의2" (그대로)
    
    Args:
        ho: 호 번호 문자열
        
    Returns:
        정규화된 호 번호 문자열 (예: "제1호")
    """
    if not ho:
        return None
    
    ho = ho.strip()
    
    # 이미 "제"로 시작하고 "호"로 끝나면 그대로 반환
    if ho.startswith("제") and ho.endswith("호"):
        return ho
    
    # 숫자만 있으면 "제{숫자}호" 형식으로 변환
    if ho.isdigit():
        return f"제{ho}호"
    
    # "호"로 끝나지만 "제"가 없으면 "제" 추가
    if ho.endswith("호") and not ho.startswith("제"):
        return f"제{ho}"
    
    # 숫자로 시작하고 "호"가 없으면 "제{숫자}호" 형식으로 변환
    match = re.match(r'^(\d+)', ho)
    if match:
        number = match.group(1)
        # "의" 뒤의 숫자가 있는지 확인
        if '의' in ho:
            # "10의2" → "제10호의2"
            sub_match = re.search(r'의\s*(\d+)', ho)
            if sub_match:
                sub_number = sub_match.group(1)
                return f"제{number}호의{sub_number}"
        return f"제{number}호"
    
    # 그 외는 그대로 반환
    return ho


def normalize_mok(mok: Optional[str]) -> Optional[str]:
    """
    목 문자를 정규화합니다.
    
    지원 형식:
    - "가" → "가" (그대로)
    - "가목" → "가"
    - "나" → "나" (그대로)
    
    Args:
        mok: 목 문자 문자열
        
    Returns:
        정규화된 목 문자 (예: "가")
    """
    if not mok:
        return None
    
    mok = mok.strip()
    
    # "목"으로 끝나면 제거
    if mok.endswith("목"):
        mok = mok[:-1]
    
    # 한글 목 문자만 추출 (가-하)
    if len(mok) > 0 and '가' <= mok[0] <= '하':
        return mok[0]
    
    # 그 외는 그대로 반환
    return mok

