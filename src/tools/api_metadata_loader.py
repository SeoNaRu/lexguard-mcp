"""
API 메타데이터 로더
api_crawler 폴더의 JSON 파일들을 읽어서 구조화된 메타데이터를 제공
"""
import json
import os
from typing import Dict, List, Optional
from pathlib import Path

# 프로젝트 루트 기준으로 api_crawler 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
API_CRAWLER_DIR = PROJECT_ROOT / "api_crawler"
API_INDEX_FILE = API_CRAWLER_DIR / "api_index.json"
APIS_DIR = API_CRAWLER_DIR / "apis"


class APIMetadataLoader:
    """API 메타데이터를 로드하고 관리하는 클래스"""
    
    def __init__(self):
        self._index_cache: Optional[Dict] = None
        self._api_details_cache: Dict[str, Dict] = {}
    
    def load_index(self) -> Dict:
        """api_index.json을 로드합니다"""
        if self._index_cache is not None:
            return self._index_cache
        
        if not API_INDEX_FILE.exists():
            raise FileNotFoundError(f"API 인덱스 파일을 찾을 수 없습니다: {API_INDEX_FILE}")
        
        with open(API_INDEX_FILE, 'r', encoding='utf-8') as f:
            self._index_cache = json.load(f)
        
        return self._index_cache
    
    def load_api_detail(self, api_id: int) -> Optional[Dict]:
        """특정 API의 상세 정보를 로드합니다"""
        index = self.load_index()
        
        # 인덱스에서 API 찾기
        api_info = None
        for api in index.get("apis", []):
            if api.get("id") == api_id:
                api_info = api
                break
        
        if not api_info:
            return None
        
        # 캐시 확인
        file_name = api_info.get("file")
        if file_name in self._api_details_cache:
            return self._api_details_cache[file_name]
        
        # 파일 로드
        api_file = APIS_DIR / file_name
        if not api_file.exists():
            return None
        
        with open(api_file, 'r', encoding='utf-8') as f:
            api_detail = json.load(f)
        
        # 메타데이터 추가
        api_detail["_metadata"] = {
            "id": api_info.get("id"),
            "file": file_name,
            "param_count": api_info.get("param_count", 0),
            "response_field_count": api_info.get("response_field_count", 0),
            "request_url": api_info.get("request_url"),
        }
        
        # 캐시에 저장
        self._api_details_cache[file_name] = api_detail
        
        return api_detail
    
    def get_all_apis(self) -> List[Dict]:
        """모든 API 목록을 반환합니다"""
        index = self.load_index()
        return index.get("apis", [])
    
    def get_api_by_name(self, api_name: str) -> Optional[Dict]:
        """API 이름으로 API 정보를 찾습니다"""
        apis = self.get_all_apis()
        for api in apis:
            if api.get("api_name") == api_name:
                return api
        return None
    
    def get_apis_by_category(self, category: str = None) -> List[Dict]:
        """카테고리별로 API를 필터링합니다"""
        apis = self.get_all_apis()
        if not category:
            return apis
        return [api for api in apis if api.get("category") == category]
    
    def search_apis(self, keyword: str) -> List[Dict]:
        """키워드로 API를 검색합니다"""
        apis = self.get_all_apis()
        keyword_lower = keyword.lower()
        return [
            api for api in apis
            if keyword_lower in api.get("api_name", "").lower()
            or keyword_lower in api.get("request_url", "").lower()
        ]


# 싱글톤 인스턴스
_metadata_loader: Optional[APIMetadataLoader] = None


def get_metadata_loader() -> APIMetadataLoader:
    """APIMetadataLoader 싱글톤 인스턴스를 반환합니다"""
    global _metadata_loader
    if _metadata_loader is None:
        _metadata_loader = APIMetadataLoader()
    return _metadata_loader

