#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 에러 메시지 확인
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("LAW_API_KEY") or os.environ.get("LAWGOKR_OC")

# 판례 검색 샘플 URL
test_url = f"http://www.law.go.kr/DRF/lawSearch.do?OC={api_key}&target=prec&type=JSON&query=담보권"

print(f"Testing URL: {test_url}")
print("=" * 80)

response = requests.get(test_url, timeout=10)
content_type = response.headers.get('Content-Type', '')

print(f"Status Code: {response.status_code}")
print(f"Content-Type: {content_type}")
print("=" * 80)
print("Response Content:")
print(response.text[:2000])  # 처음 2000자만 출력

