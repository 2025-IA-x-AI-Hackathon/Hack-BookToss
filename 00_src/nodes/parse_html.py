"""
parse_html.py
-------------
DOM 직독(BeautifulSoup) 모드 전용 파서 노드

역할:
- 저장된 HTML 파일(SSR이든 SPA 렌더된 스냅샷이든)을 읽어서
  책 카드 블록들을 DOM 기반으로 직접 파싱한다.
- 최소 필수 필드:
  title, library, available
- 옵션 필드:
  author, call_number, cover_image
- 결과는 state에 `parsed_books`, `parse_success`, `parse_error`로 반환한다.

입력(state):
- `saved_html_paths` (권장) 또는 `saved_html_path` 또는 `html_path` 키에 파일 경로 문자열
- 선택: `place` (seocho/songpa 등)

출력(state):
- `parsed_books`: List[dict]
- `parse_success`: bool
- `parse_error`: Optional[str]

CLI:
- 단독 실행 테스트 가능:
  PYTHONPATH=00_src python -m nodes.parse_html  \
    --path 00_src/data/raw/2025-10-27/seocho_1761576345_results.html
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from pathlib import Path
import argparse
import re
import json
from datetime import datetime
import sys

# =========================
# 유틸
# =========================

STATUS_KEYWORDS = [
    "대출가능", "대출중", "대출 불가", "대출불가",
    "예약가능", "예약불가", "예약 중", "예약중",
    "반납예정일", "상호대차", "비치중"
]

LIBRARY_HINTS = [
    "도서관", "작은도서관", "분관", "자료관"
]

CALLNO_PAT = re.compile(r"청구기호\s*[:：]?\s*([^\n<>]+?)(?=\s*(?:<|$|위치출력|등록번호|ISBN))")
# 송파구 등: 청구기호 레이블 없이 숫자-한글 패턴 (예: "큰글자 848-칼292ㅅ", "813.6-김17ㅅ", "점자도서 808.9-사14사-56")
# 청구기호는 3-4자리 숫자로 시작하고, 반드시 한글이 포함되어야 함 (날짜 제외용)
CALLNO_DIRECT_PAT = re.compile(r"(?:큰글자|점자도서|전자책|일반도서)?\s*\d{3,4}[.\-][가-힣\d\-]+\b")

# 저자 추출 패턴
AUTHOR_PAT = re.compile(r"(?:저자|지은이|글쓴이|작가|글)\s*[:：]\s*(.+)")

def _clean(txt: Optional[str]) -> str:
    if not txt:
        return ""
    return re.sub(r"\s+", " ", txt).strip()

def _has_korean(s: str) -> bool:
    return bool(re.search(r"[가-힣]", s))

def _extract_call_number(block) -> Optional[str]:
    """
    청구기호를 추출한다.
    block: BeautifulSoup element (li 등)
    """
    # 방법 1: 송파구 스타일 - book_info info02 클래스의 span들에서 청구기호 패턴 찾기
    info02_tags = block.find_all(['div'], class_=lambda x: x and 'info02' in x.lower())
    for tag in info02_tags:
        for span in tag.find_all('span'):
            span_text = _clean(span.get_text())
            m = CALLNO_DIRECT_PAT.search(span_text)
            if m:
                return _clean(m.group(0))
    
    # 방법 2: 서초구 스타일 - ul > li:nth-child(3) > span에서 청구기호 찾기
    ul_tags = block.find_all('ul', class_=lambda x: not x or 'btns' not in x.lower() if x else True)
    for ul in ul_tags:
        li_items = ul.find_all('li', recursive=False)
        # 세번째 li 항목 확인 (0:제목, 1:저자, 2:출판사/연도/청구기호)
        if len(li_items) >= 3:
            third_li = li_items[2]
            for span in third_li.find_all('span'):
                span_text = _clean(span.get_text())
                m = CALLNO_DIRECT_PAT.search(span_text)
                if m:
                    return _clean(m.group(0))
    
    # 방법 3: 전체 텍스트에서 "청구기호:" 레이블이 있는 경우 (강남구 등)
    block_text = _clean(block.get_text(" "))
    m = CALLNO_PAT.search(block_text)
    if m:
        return _clean(m.group(1))
    
    # 방법 4: 레이블 없이 청구기호 패턴만 있는 경우 (fallback)
    m = CALLNO_DIRECT_PAT.search(block_text)
    if m:
        return _clean(m.group(0))
    
    return None

def _extract_author(block) -> Optional[str]:
    """
    저자/작가 정보를 추출한다.
    """
    # 방법 1: 송파구 스타일 - book_info info01 클래스 (저자 라벨 없이 직접 텍스트)
    info01_tags = block.find_all(['div'], class_=lambda x: x and 'info01' in x.lower())
    for tag in info01_tags:
        text = _clean(tag.get_text())
        # 너무 짧거나 긴 텍스트 제외
        if text and 2 <= len(text) <= 50 and _has_korean(text):
            # 숫자로 시작하거나 ISBN, 청구기호 등 메타데이터 제외
            if not re.match(r'^\d|ISBN|청구기호|발행|출판', text):
                # "글·그림", "지음" 등 불필요한 부분 제거
                author = re.sub(r'\s*(글·그림|그림|글쓴이|지음|저|著)\s*$', '', text)
                author = _clean(author)
                if author and _has_korean(author):
                    return author
    
    # 방법 2: 서초구 스타일 - ul > li:nth-child(2) > span (저자 라벨 없이 직접 텍스트)
    # 책 정보가 ul > li 리스트로 구성되어 있고, 두번째 li에 저자 정보가 들어있음
    ul_tags = block.find_all('ul', class_=lambda x: not x or 'btns' not in x.lower() if x else True)
    for ul in ul_tags:
        li_items = ul.find_all('li', recursive=False)
        # 두번째 li 항목이 있으면 확인 (0번째는 제목, 1번째는 저자)
        if len(li_items) >= 2:
            second_li = li_items[1]
            # li 안의 span을 찾되, href 속성이 javascript: 인 경우
            span = second_li.find('span', href=lambda x: x and 'javascript' in x if x else False)
            if span:
                text = _clean(span.get_text())
                # "글·그림", "지음" 등 포함된 텍스트를 정리
                if text and 2 <= len(text) <= 50 and _has_korean(text):
                    # 숫자로 시작하거나 메타데이터 제외
                    if not re.match(r'^\d|ISBN|청구기호|대출|도서관', text):
                        author = re.sub(r'\s*(글·그림|그림|글쓴이|지음|저|著)\s*$', '', text)
                        author = _clean(author)
                        if author and _has_korean(author):
                            return author
    
    # 방법 3: dd.author 또는 class에 author가 포함된 태그에서 span별로 찾기 (강남구 등)
    author_tags = block.find_all(['dd', 'div'], class_=lambda x: x and 'author' in x.lower())
    for tag in author_tags:
        # span 태그별로 개별 처리
        for span in tag.find_all('span'):
            span_text = _clean(span.get_text())
            m = AUTHOR_PAT.search(span_text)
            if m:
                author = _clean(m.group(1))
                # "글·그림", "지음" 등 불필요한 부분 제거
                author = re.sub(r'\s*(글·그림|그림|글쓴이|지음|저|著)\s*$', '', author)
                author = _clean(author)
                # 유효성 검증
                if author and len(author) <= 50 and _has_korean(author):
                    return author
    
    # 방법 4: block 전체 텍스트에서 찾기 (fallback)
    block_text = _clean(block.get_text(" "))
    m = AUTHOR_PAT.search(block_text)
    if m:
        author = _clean(m.group(1))
        # 발행자, 발행연도 등 앞에서 자르기
        author = re.split(r'\s+(?:발행자|발행연도|출판사|ISBN|등록번호|청구기호)', author)[0]
        # "글·그림", "지음" 등 불필요한 부분 제거
        author = re.sub(r'\s*(글·그림|그림|글쓴이|지음|저|著)\s*$', '', author)
        author = _clean(author)
        # 유효성 검증
        if author and len(author) <= 50 and _has_korean(author):
            return author
    
    return None

def _pick_library(candidates: List[str]) -> Optional[str]:
    # "…도서관/…작은도서관/…분관" 등 가장 길고 구체적인 마지막 항목을 선호
    # 단, 상태 키워드나 연도가 포함된 것은 제외
    libs = []
    for c in candidates:
        # 도서관 힌트가 포함되어 있어야 함
        if not any(h in c for h in LIBRARY_HINTS):
            continue
        # 상태 키워드나 연도가 포함된 것은 제외 (서초구 SPA 대응)
        if any(kw in c for kw in STATUS_KEYWORDS):
            continue
        # 너무 긴 것 제외 (출판사+연도+상태+도서관이 합쳐진 경우)
        if len(c) > 50:
            continue
        libs.append(c)
    
    if not libs:
        return None
    # 길이 우선, 동점이면 마지막
    libs = sorted(enumerate(libs), key=lambda x: (len(x[1]), x[0]))
    return libs[-1][1] if libs else None

def _status_to_available(status_raw: str) -> bool:
    s = status_raw or ""
    return "대출가능" in s

def _extract_title_from_block(block) -> Optional[str]:
    # 여러 후보 셀렉터를 순차 시도
    title_candidates = []
    for css in [
        ".tit", ".custom-tit", ".title", ".book_name .title", "dt.tit", ".bookDataWrap .tit",
        "h3", "h4", ".data .tit"
    ]:
        el = block.select_one(css)
        if el:
            t = _clean(el.get_text(" "))
            if t:
                # 앞에 붙은 번호 제거 (예: "1. 제목", "22. 제목" → "제목")
                t = re.sub(r"^\d+\.\s*", "", t)
                # "도서" 텍스트 제거 (예: "도서 1. 제목" → "1. 제목")
                t = re.sub(r"^도서\s*\d*\.\s*", "", t)
                t = re.sub(r"^도서\s+", "", t)
                title_candidates.append(t)

    # 이미지 alt도 종종 제목
    if not title_candidates:
        img = block.find("img", attrs={"alt": True})
        if img:
            t = _clean(img.get("alt"))
            if t:
                title_candidates.append(t)

    # 가장 긴 한글 포함 텍스트 선호
    title_candidates = [t for t in title_candidates if _has_korean(t)]
    if not title_candidates:
        return None
    title_candidates.sort(key=lambda x: len(x))
    return title_candidates[-1]

def _extract_status_from_block(block) -> Optional[str]:
    # 상태 키워드가 포함된 텍스트를 찾음 (부모 요소 포함)
    # 강남구는 부모 요소의 <b class="emp3">에 상태가 있음
    # 성북구는 block 안의 하위 요소에 <b> 태그가 있음
    search_scope = block
    # 부모도 포함해서 검색 범위 확장
    if block.parent and block.parent.name != '[document]':
        search_scope = block.parent
    
    txt = _clean(search_scope.get_text(" "))
    hits = [kw for kw in STATUS_KEYWORDS if kw in txt]
    if not hits:
        return None
    
    # 특정 태그에서 우선 검색 (더 정확함)
    # 단, "도서예약불가", "상호대차불가"는 제외
    for tag_class in ['emp3', 'emp2', 'emp1', 'status', 'state']:
        status_tag = search_scope.find(['b', 'span', 'em'], class_=tag_class)
        if status_tag:
            tag_text = _clean(status_tag.get_text())
            if tag_text and any(kw in tag_text for kw in STATUS_KEYWORDS):
                # 강남구: "도서예약불가", "상호대차불가" 제외
                if "도서예약불가" in tag_text or "상호대차불가" in tag_text or "무인예약불가" in tag_text:
                    continue
                # "대출가능[비치중]" → "대출가능" 추출
                if "대출가능" in tag_text:
                    return "대출가능"
                elif "대출중" in tag_text or "대출 중" in tag_text or "대출불가" in tag_text:
                    return "대출중"
                return tag_text
    
    # 추가: class 없는 <b>, <strong> 태그에서도 검색 (성북구 등)
    # 예: <p class="txt">자료상태 : <b>대출가능(비치자료)</b></p>
    # 중요: "대출가능/대출중/대출불가"를 우선적으로 찾고, 
    #      "도서예약불가/상호대차불가" 같은 부가 정보는 무시
    
    # 1단계: <b>, <strong> 태그에서 우선 검색 (자료상태의 핵심 정보)
    # block과 search_scope (부모) 모두에서 검색
    for search_area in [block, search_scope]:
        for tag_name in ['b', 'strong']:
            all_tags = search_area.find_all(tag_name)
            for tag in all_tags:
                tag_text = _clean(tag.get_text())
                if not tag_text:
                    continue
                
                # 강남구: "대출불가[대출중]" → 대괄호 안의 "대출중" 추출
                # 대괄호가 있으면 그 안의 텍스트를 우선 확인
                bracket_match = re.search(r'\[([^\]]+)\]', tag_text)
                if bracket_match:
                    bracket_content = bracket_match.group(1)
                    if "대출가능" in bracket_content:
                        return "대출가능"
                    elif "대출중" in bracket_content or "대출 중" in bracket_content:
                        return "대출중"
                    elif "대출불가" in bracket_content or "대출 불가" in bracket_content:
                        return "대출불가"
                    elif "예약중" in bracket_content:
                        # "대출예약중", "상호대차예약중" 등 → 대출불가
                        return "대출불가"
                    # 대괄호 안에 매칭되는 것이 없으면 대괄호 밖의 텍스트 확인
                    # (계속 진행)
                
                # 대괄호가 없거나 매칭 안되면 전체 텍스트에서 확인
                # "대출가능(비치자료)" → "대출가능" 추출
                if "대출가능" in tag_text:
                    return "대출가능"
                elif "대출중" in tag_text or "대출 중" in tag_text:
                    return "대출중"
                elif "대출불가" in tag_text or "대출 불가" in tag_text:
                    return "대출불가"
    
    # 2단계: <em>, <span> 태그에서 검색 (부가 정보)
    # 단, "도서예약불가" 같은 것은 우선순위가 낮으므로 나중에 반환
    primary_status = None
    secondary_status = None
    
    for tag_name in ['em', 'span']:
        all_tags = search_scope.find_all(tag_name)
        for tag in all_tags:
            tag_text = _clean(tag.get_text())
            if not tag_text or not any(kw in tag_text for kw in STATUS_KEYWORDS):
                continue
            
            # 강남구: "도서예약불가", "상호대차불가"는 무시 (부가 정보일 뿐)
            if "도서예약불가" in tag_text or "상호대차불가" in tag_text:
                continue
            
            if "대출가능" in tag_text:
                primary_status = "대출가능"
            elif "대출중" in tag_text or "대출 중" in tag_text:
                if not primary_status:
                    primary_status = "대출중"
            elif "대출불가" in tag_text or "대출 불가" in tag_text:
                if not primary_status:
                    primary_status = "대출불가"
            # 부가 정보 (우선순위 낮음)
            elif not primary_status and not secondary_status:
                if len(tag_text) < 30:
                    secondary_status = tag_text.split('(')[0].split('[')[0].strip()
    
    if primary_status:
        return primary_status
    if secondary_status:
        return secondary_status
    
    # 폴백: 전체 텍스트에서 검색
    # "도서예약불가", "상호대차불가"는 제외
    if "도서예약불가" not in txt and "상호대차불가" not in txt:
        if "대출가능" in hits:
            return "대출가능"
        for kw in ["대출중", "대출 불가", "대출불가", "비치중"]:
            if kw in txt:
                return kw
    return hits[0]

def _extract_library(block) -> Optional[str]:
    """
    em, span 등에서 library 정보를 추출한다.
    """
    parts = []
    for em in block.find_all(["em", "span"]):
        t = _clean(em.get_text(" "))
        if t:
            parts.append(t)

    # 도서관 후보
    return _pick_library(parts)

def _extract_cover_image(block) -> Optional[str]:
    """
    책 표지 이미지 URL 추출 (강남, 송파, 서초 모두 지원)
    """
    # block과 부모 요소 모두에서 이미지 찾기 (강남: 부모 li에 img가 있음)
    search_areas = [block]
    if block.parent and block.parent.name != '[document]':
        search_areas.append(block.parent)
    
    for area in search_areas:
        for img in area.find_all("img"):
            src = img.get("src", "")
            
            # 1. src가 http로 시작하는 외부 이미지 (강남, 서초)
            if src and src.startswith("http"):
                # "noimg" 같은 기본 이미지는 제외
                if "noimg" not in src.lower() and "no-image" not in src.lower():
                    return src
            
            # 2. 상대 경로 이미지도 수집 (송파 등)
            # 단, noimg는 제외
            if src and "noimg" not in src.lower():
                # 상대 경로를 절대 경로로 변환할 수 있도록 반환
                # (나중에 도서관별 base_url을 붙일 수 있음)
                if not src.startswith("http"):
                    # 일단 그대로 반환 (base_url은 나중에 추가 가능)
                    pass
    
    return None

def _parse_item_block(block) -> Optional[Dict[str, Any]]:
    """
    단일 카드/아이템 블록에서 도서 정보를 추출한다.
    """
    block_text = _clean(block.get_text(" "))

    title = _extract_title_from_block(block)
    status = _extract_status_from_block(block)
    library = _extract_library(block)

    # 옵션 필드
    author = _extract_author(block)
    call_number = _extract_call_number(block)
    cover_image = _extract_cover_image(block)

    # library 값 정제: "도서관: 글빛도서관" → "글빛도서관"
    if library:
        library = re.sub(r'^도서관\s*[:：]\s*', '', library).strip()
        library = re.sub(r'^작은도서관\s*[:：]\s*', '', library).strip()

    # available 계산
    available = _status_to_available(status or "")

    # 최소한 제목이 없으면 스킵 (노이즈 제거)
    if not title:
        return None

    return {
        "title": title,
        "author": author,
        "library": library,
        "available": available,
        "call_number": call_number,
        "cover_image": cover_image,
    }

def _find_item_blocks(soup: BeautifulSoup) -> List[Any]:
    """
    여러 사이트를 폭넓게 커버하기 위한 '넓은' 셀렉터 시도.
    """
    selectors = [
        "div.item.row",                # 서초구 스타일
        "div.bookArea",                # 송파 스타일
        "dl.bookDataWrap",             # DL 기반
        "ul.listWrap > li",            # 카드 리스트
        "li",                          # 최후 보루(노이즈 많음)
    ]
    seen = set()
    blocks = []
    for css in selectors:
        for el in soup.select(css):
            # 동일 엘리먼트 중복 방지
            key = id(el)
            if key in seen:
                continue
            seen.add(key)
            blocks.append(el)
        if blocks:
            # 상위 셀렉터에서 충분히 찾았으면 더 깊이 안 내려가도 됨
            break
    return blocks

def parse_html(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph 노드 진입점.
    다중 HTML 파일 지원: saved_html_paths 리스트가 있으면 모두 파싱하고 통합.
    """
    out = dict(state)
    
    # 다중 파일 경로 가져오기 (우선순위: saved_html_paths > saved_html_path > html_path)
    html_paths = out.get("saved_html_paths") or [out.get("saved_html_path") or out.get("html_path")]
    html_paths = [p for p in html_paths if p]  # None 제거
    
    if not html_paths:
        out["parse_success"] = False
        out["parse_error"] = "No html_path provided in state (expected 'saved_html_paths', 'saved_html_path' or 'html_path')."
        out["parsed_books"] = []
        return out

    all_parsed: List[Dict[str, Any]] = []
    errors = []
    
    # 각 HTML 파일을 순차적으로 파싱
    for idx, html_path in enumerate(html_paths, start=1):
        p = Path(html_path)
        if not p.exists():
            errors.append(f"[Page {idx}] HTML file not found: {p}")
            continue

        try:
            html = p.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")

            item_blocks = _find_item_blocks(soup)
            page_parsed: List[Dict[str, Any]] = []
            
            for blk in item_blocks:
                rec = _parse_item_block(blk)
                if not rec:
                    continue
                # 필수 필드 보정: 없는 건 None으로라도 확정
                rec.setdefault("title", None)
                rec.setdefault("library", None)
                rec.setdefault("available", False)
                
                page_parsed.append(rec)
            
            all_parsed.extend(page_parsed)
            print(f"[parse_html] 페이지 {idx} 파싱 완료: {len(page_parsed)}건 추출 ({p.name})")
            
        except Exception as e:
            errors.append(f"[Page {idx}] Parse error: {e}")
            continue

    # 중복 제거 (동일한 title + library 조합)
    seen_keys = set()
    unique_parsed = []
    duplicates = 0
    
    for rec in all_parsed:
        key = (rec.get("title"), rec.get("library"))
        if key not in seen_keys:
            seen_keys.add(key)
            unique_parsed.append(rec)
        else:
            duplicates += 1
    
    if duplicates > 0:
        print(f"[parse_html] 중복 제거: {duplicates}건 (최종 {len(unique_parsed)}건)")

    # 최소한 하나라도 있어야 성공으로 친다.
    out["parsed_books"] = unique_parsed
    out["parse_success"] = len(unique_parsed) > 0
    
    if errors:
        out["parse_error"] = " | ".join(errors)
    else:
        out["parse_error"] = None if out["parse_success"] else "No item blocks parsed (DOM mode)."

    # ── JSONL 저장 ──
    saved = []
    out_jsonl = state.get("out_jsonl") or out.get("out_jsonl")
    try:
        if out_jsonl:
            _dump_jsonl(out_jsonl, unique_parsed)
            saved.append(("jsonl", out_jsonl))
            print(f"[parse_html] ✅ JSONL 저장 완료: {out_jsonl} ({len(unique_parsed)}건)")
    except Exception as e:
        # 저장 중 오류는 parse_error에 덧붙여 기록하되, 파싱 결과 자체는 유지
        prev = out.get("parse_error")
        msg = f"SaveError({type(e).__name__}): {e}"
        out["parse_error"] = f"{prev} | {msg}" if prev else msg
        print(f"[parse_html] ❌ JSONL 저장 실패: {e}")
    out["saved"] = saved

    return out


def _dump_jsonl(path: str, parsed_books: List[Dict[str, Any]]) -> None:
    """Save parse result as JSON Lines (one object per line)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for rec in parsed_books:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# --------------------------
# CLI 테스트
# --------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOM 직독(BeautifulSoup) 파서 테스트")
    parser.add_argument("--path", required=True, help="HTML 파일 경로")
    parser.add_argument("--place", default=None, help="도서관 구 이름(선택)")
    parser.add_argument("--out-jsonl", default=None, help="전체 결과를 JSONL(행 단위)로 저장할 경로")
    args = parser.parse_args()

    state = {
        "html_path": args.path,
        "place": args.place,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
    }
    
    if args.out_jsonl:
        state["out_jsonl"] = args.out_jsonl
    
    out = parse_html(state)

    ok = bool(out.get("parse_success"))
    error = out.get("parse_error")
    parsed_books = out.get("parsed_books", [])

    # 콘솔에는 요약만 출력
    saved = out.get("saved", [])
    print(json.dumps({
        "ok": ok,
        "error": error,
        "count": len(parsed_books),
        "saved": saved,
        "samples": parsed_books[:3],  # 여전히 앞 3건만 표본 출력
    }, ensure_ascii=False, indent=2))
