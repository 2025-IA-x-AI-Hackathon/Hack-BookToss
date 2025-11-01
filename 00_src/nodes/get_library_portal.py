# 00_src/nodes/get_library_portal.py

from __future__ import annotations
import os, yaml
from typing import Dict, Any

CATALOG_INDEX_PATH = "00_src/configs/catalog_index.yaml"

def get_library_portal(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    입력: state(dict) 내 place(str)
    동작: catalog_index.yaml에서 입력된 place에 해당하는 도서관 홈페이지 URL을 찾는다.
    출력: {"catalog_home_url": <str|None>, "found": <bool>, "reason": <str|None>, "index_key": <str|None>}
    """
    # place 값 추출 및 공백 제거
    place = str(state.get("place", "")).strip()
    if not place:
        # place 입력이 비었을 때
        return {**state, "catalog_home_url": None, "found": False, "reason": "empty place"}

    # catalog_index.yaml 존재 확인
    if not os.path.exists(CATALOG_INDEX_PATH):
        # YAML 파일이 없을 때
        return {**state, "catalog_home_url": None, "found": False, "reason": "catalog_index.yaml not found"}

    # YAML 파일 로드
    with open(CATALOG_INDEX_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # place로 엔트리 탐색
    entry = data.get(place)
    if not entry:
        # 해당 place 엔트리 없음
        return {**state, "catalog_home_url": None, "found": False, "reason": f"no entry for {place}"}

    # 홈페이지 URL 추출
    home = entry.get("homepage")
    if not home:
        # homepage 필드 없음
        return {**state, "catalog_home_url": None, "found": False, "reason": f"no homepage in entry for {place}"}

    # 정상적으로 찾은 경우 반환 (index_key는 place와 동일)
    return {**state, "catalog_home_url": home, "found": True, "index_key": place}

