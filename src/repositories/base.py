"""
Base Repository - 공통 유틸리티 및 상수
"""
import os
import logging
from cachetools import TTLCache
from typing import Optional
import re

# Logger
logger = logging.getLogger("lexguard-mcp")
level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
logger.setLevel(level)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
logger.propagate = True

# Cache settings
search_cache = TTLCache(maxsize=200, ttl=1800)  # 검색 결과 30분 캐시
failure_cache = TTLCache(maxsize=200, ttl=300)  # 실패 요청 5분 캐시

# 국가법령정보센터 API 기본 URL
LAW_API_BASE_URL = "https://www.law.go.kr/DRF/lawService.do"
LAW_API_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"  # 법령 검색용


class BaseLawRepository:
    """법령 Repository의 기본 클래스 - 공통 유틸리티 메서드"""
    
    @staticmethod
    def get_api_key(arguments: Optional[dict] = None) -> str:
        """
        API 키를 가져옵니다.
        Priority: 1) arguments.env, 2) environment variables (.env)
        """
        api_key = ""
        
        # Priority 1: Get from arguments.env
        if isinstance(arguments, dict) and "env" in arguments:
            env = arguments["env"]
            if isinstance(env, dict) and "LAW_API_KEY" in env:
                api_key = env["LAW_API_KEY"]
                logger.debug("API key from arguments.env")
                return api_key
        
        # Priority 2: Get from .env file
        api_key = os.environ.get("LAW_API_KEY", "")
        if api_key:
            logger.debug("API key from .env file")
        
        return api_key
    
    @staticmethod
    def normalize_search_query(query: str) -> str:
        """검색어를 정규화합니다."""
        normalized = query.strip()
        normalized = " ".join(normalized.split())
        return normalized
    
    @staticmethod
    def parse_article_number(article_str: str) -> str:
        """
        조/항/호 번호를 6자리 숫자로 변환합니다.
        예: '제1조' -> '000100', '제10조의2' -> '001002', '제2항' -> '000200'
        
        Args:
            article_str: 조/항/호 번호 문자열 (예: '제1조', '제2항', '제10호의2')
            
        Returns:
            6자리 숫자 문자열 (예: '000100')
        """
        if not article_str:
            return "000000"
        
        # 숫자 추출
        numbers = re.findall(r'\d+', article_str)
        if not numbers:
            return "000000"
        
        main_num = int(numbers[0])
        
        # '의' 뒤의 숫자 확인 (예: '제10조의2')
        if '의' in article_str and len(numbers) > 1:
            sub_num = int(numbers[1])
            # 6자리: 앞 4자리는 조 번호, 뒤 2자리는 '의' 뒤 숫자
            return f"{main_num:04d}{sub_num:02d}"
        else:
            # 6자리: 조 번호만
            return f"{main_num:06d}"
    
    @staticmethod
    def parse_mok(mok_str: str) -> str:
        """
        목 문자를 한글 인코딩하여 반환합니다.
        예: '가' -> '가', '다' -> '다'
        
        Args:
            mok_str: 목 문자 (예: '가', '나', '다')
            
        Returns:
            인코딩된 목 문자
        """
        if not mok_str:
            return ""
        
        # 한글 목 문자만 추출 (가-하)
        mok_char = mok_str.strip()[0] if mok_str.strip() else ""
        if '가' <= mok_char <= '하':
            return mok_char
        return ""

