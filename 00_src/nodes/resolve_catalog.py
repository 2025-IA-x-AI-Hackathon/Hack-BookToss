# 00_src/nodes/resolve_catalog.py
"""
resolve_catalog.py
------------------
입력: state(dict) 안의 place(str)
동작: catalog_index.yaml에서 place에 맞는 홈페이지 URL을 찾는다. (LLM 사용 X)
출력: {"place": <입력>, "catalog_home_url": <str|None>, "found": <bool>}

"""

from __future__ import annotations
import os, yaml
from typing import Dict, Any

CATALOG_INDEX_PATH = "00_src/configs/catalog_index.yaml"

def resolve_catalog(state: Dict[str, Any]) -> Dict[str, Any]:
    """place로 도서관 홈 URL을 찾아서 반환한다."""
    place = str(state.get("place", "")).strip()
    if not place:
        return {**state, "catalog_home_url": None, "found": False, "reason": "empty place"}

    # YAML 로드
    if not os.path.exists(CATALOG_INDEX_PATH):
        return {**state, "catalog_home_url": None, "found": False, "reason": "catalog_index.yaml not found"}

    with open(CATALOG_INDEX_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # place 값을 그대로 키로 사용하여 YAML에서 찾음
    entry = data.get(place)

    if not entry:
        return {**state, "catalog_home_url": None, "found": False, "reason": f"no entry for {place}"}

    home = entry.get("homepage")
    if not home:
        return {**state, "catalog_home_url": None, "found": False, "reason": f"no homepage in entry for {place}"}

    # place_key를 더 이상 강제하지 않는다. 디버깅 편의를 위해 index_key만 남긴다.
    return {**state, "catalog_home_url": home, "found": True, "index_key": place}