"""
search_book.py
--------------
브라우저 자동화로 도서관 사이트에서 책 검색 수행 (단계 1: 단일 페이지)

입력: state(dict) - catalog_home_url, title 포함
동작: browser-use를 사용해 도서관 사이트에서 검색하고 첫 페이지 HTML 저장
출력: state에 saved_html_path 추가
"""

from __future__ import annotations
import os
from typing import Any, Dict, List
import urllib.parse as _urlparse  # 도메인 추출용
from datetime import datetime

# Agent 모드용 라이브러리 (로컬 브라우저 직접 제어)
try:
    from browser_use import Agent, ChatOpenAI, Browser  # type: ignore
except Exception:
    Agent = None  # type: ignore
    ChatOpenAI = None  # type: ignore
    Browser = None  # type: ignore

# .env 자동 로드(있으면)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Quick SPA readiness keywords for Korean library sites
SPA_READY_KEYWORDS = ["검색결과", "소장", "대출", "상세보기"]

def _build_browser_use_task(catalog_home_url: str, title: str) -> str:
    """DOM 신호 기반: 보이면 즉시 진행, 보이지 않으면 충분히 대기 후 종료."""
    # 제거됨: hint: Dict[str, Any], backoff: List[int] - 사용되지 않는 파라미터
    return f"""
1) navigate to "{catalog_home_url}"
2) if a VISIBLE search input exists (placeholder/aria-label/label text includes: 검색|도서|자료), DO NOT WAIT: focus it immediately.
   else wait up to 10s for SPA to load; if still hidden, STOP with no_results. DO NOT REFRESH.
3) type "{title}" and press Enter. if not submitted, click the search/돋보기 button ONCE (no repeats).
4) if URL changed OR the page contains any of [검색결과, 소장, 대출, 건], STOP immediately with success (done).
5) NEVER repeat the same action twice. at most 2 attempts TOTAL. do not open new tabs. do not save HTML.
"""

def search_book(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    도서관 사이트에서 책을 검색하고 첫 페이지 HTML을 저장합니다.
    
    Args:
        state: 상태 딕셔너리 (catalog_home_url, title, place 포함)
        
    Returns:
        업데이트된 state 딕셔너리 (saved_html_path, page_url 등 추가)
    """
    # 핵심 입력
    home = str(state.get("catalog_home_url", "")).strip()
    title = str(state.get("title", "")).strip()
    place = str(state.get("place", "")).strip()
    if not place:
        place = state["place"] = "unknown"
    if not home or not title:
        return {**state, "ok": False, "search_error": "catalog_home_url 또는 title이 없습니다", "page_url": None}

    # 텔레메트리 비활성(불필요 백오프 방지) - 모든 변수 강제 설정
    os.environ["POSTHOG_DISABLED"] = "1"
    os.environ["ANONYMIZED_TELEMETRY"] = "false"
    os.environ["TELEMETRY_DISABLED"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"

    # 브라우저 제한: 홈 URL에서 도메인 추출
    def _derive_allowed_from_home(url: str) -> List[str]:
        try:
            netloc = _urlparse.urlparse(url).netloc
            if netloc and "." in netloc:
                base = netloc.split(":")[0]
                parts = base.split(".")
                if len(parts) >= 2:
                    return [base, f"*.{'.'.join(parts[-2:])}"]
                return [base]
        except Exception:
            pass
        return ["*.go.kr", "*.or.kr"]  # fallback
    
    allowed = state.get("allowed_domains") or _derive_allowed_from_home(home)

    # 브라우저 생성
    browser = None
    if Browser is not None:
        try:
            browser = Browser(
                headless=False,
                allowed_domains=allowed,
                window_size={"width": 1280, "height": 900},
                keep_alive=True,
                minimum_wait_page_load_time=0.5, # 페이지 로딩 대기 시간
                wait_for_network_idle_page_load_time=0.8, # 네트워크 아이들 대기 시간
                wait_between_actions=0.2, # 액션 간 대기 시간
                highlight_elements=False,
            )
            print(f"[search_book] Browser 생성 완료")
        except Exception as e:
            print(f"[search_book] ❌ Browser 생성 실패: {e}")
            browser = None

    # LLM (소형 모델)
    if Agent is None or ChatOpenAI is None:
        return {**state, "ok": False, "search_error": "browser_use Agent 미설치", "page_url": None}
    
    llm = ChatOpenAI(model=state.get("llm_model", "gpt-4o-mini"))

    # Agent 태스크 생성
    task = _build_browser_use_task(home, title)
    agent = Agent(task=task, llm=llm, browser=browser) if browser else Agent(task=task, llm=llm)

    import asyncio
    try:
        # asyncio 내에서 검색 실행 및 HTML 추출
        async def run_and_extract():
            history = await agent.run(max_steps=int(state.get("max_steps", 8)))
            
            # SPA 로딩 완료 대기: 네트워크 아이들 + 본문 키워드 등장 대기(최대 10s)
            try:
                await browser.wait_for_network_idle(timeout=10000)
            except Exception:
                await asyncio.sleep(1.5)

            # 추가: 본문에 라이브러리 결과 키워드가 나타날 때까지 폴링(최대 10s)
            ready = False
            for _ in range(20):  # 20 * 0.5s = 10s
                try:
                    eval_result = await browser.cdp_client.send.Runtime.evaluate(
                        params={
                            "expression": "document.body ? document.body.innerText : ''",
                            "returnByValue": True
                        },
                        session_id=browser.agent_focus.session_id
                    )
                    body_text = (eval_result.get("result", {}) or {}).get("value", "") or ""
                    if any(k in body_text for k in SPA_READY_KEYWORDS):
                        ready = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.5)

            print(f"[search_book] SPA 로딩 대기 완료 ({'성공' if ready else '타임아웃'})")
            
            # 추가 대기: 검색 결과 데이터가 완전히 로드될 시간 확보 (5초)
            if ready:
                print(f"[search_book] 검색 결과 데이터 로딩 대기 중... (5초)")
                await asyncio.sleep(5)
            
            # CDP endpoint & page_url 추출
            page_url = None
            cdp = None
            
            if browser:
                try:
                    cdp = browser.cdp_url
                    print(f"[search_book] CDP: {cdp}")
                except Exception as e:
                    print(f"[search_book] CDP 추출 실패: {e}")
                
                try:
                    page_url = await browser.get_current_page_url()
                    print(f"[search_book] URL: {page_url}")
                except Exception as e:
                    print(f"[search_book] URL 추출 실패: {e}")
            
            # HTML 추출 및 저장
            saved_path = None
            html_size = 0
            
            if browser and hasattr(browser, 'cdp_client') and browser.cdp_client:
                try:
                    print(f"[search_book] HTML 추출 시작...")
                    result = await browser.cdp_client.send.Runtime.evaluate(
                        params={
                            "expression": "document.documentElement.outerHTML",
                            "returnByValue": True
                        },
                        session_id=browser.agent_focus.session_id
                    )
                    html_content = result.get("result", {}).get("value", "")
                    
                    if html_content:
                        # 저장 경로 생성
                        today = datetime.now().strftime("%Y-%m-%d")
                        timestamp = int(datetime.now().timestamp())
                        dir_path = f"00_src/data/raw/{today}"
                        os.makedirs(dir_path, exist_ok=True)
                        
                        filename = f"{place}_{timestamp}_results.html"
                        saved_path = os.path.join(dir_path, filename)
                        
                        # 파일 저장
                        with open(saved_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                        
                        # 메타데이터 사이드카 저장(.meta.json)
                        try:
                            meta = {
                                "place": place,
                                "page_url": page_url,
                                "captured_at": datetime.now().isoformat(timespec="seconds"),
                                "cdp_endpoint": cdp
                            }
                            with open(saved_path + ".meta.json", "w", encoding="utf-8") as mf:
                                import json as _json
                                mf.write(_json.dumps(meta, ensure_ascii=False))
                        except Exception as _e:
                            print(f"[search_book] 메타 저장 경고: {_e}")
                        
                        html_size = len(html_content)
                        print(f"[search_book] ✅ HTML 저장 완료: {saved_path} ({html_size:,} bytes)")
                    else:
                        print(f"[search_book] ⚠️ HTML 내용이 비어있음")
                        
                except Exception as e:
                    print(f"[search_book] ❌ HTML 추출/저장 실패: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 브라우저 종료 (async 컨텍스트 내부에서)
            if browser:
                try:
                    print(f"[search_book] 브라우저 종료 중...")
                    await browser.stop()
                    print(f"[search_book] ✅ 브라우저 종료 완료")
                except Exception as e:
                    print(f"[search_book] ⚠️ 브라우저 종료 경고: {e}")
            
            return history, page_url, cdp, saved_path, html_size
        
        # asyncio 실행
        history, page_url, cdp_endpoint, saved_html_path, html_size = asyncio.run(run_and_extract())
        
        return {
            **state, 
            "ok": True, 
            "page_url": page_url, 
            "cdp_endpoint": cdp_endpoint, 
            "saved_html_path": saved_html_path,
            "html_size": html_size,
            "place": place
        }
    except Exception as e:
        print(f"[search_book] ❌ 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            **state, 
            "ok": False, 
            "search_error": str(e),
            "page_url": None
        }
