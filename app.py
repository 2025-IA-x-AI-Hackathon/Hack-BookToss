import streamlit as st
import os
import sys
import json
from typing import List, Dict, Optional, Tuple
import requests
from dotenv import load_dotenv
from math import radians, sin, cos, sqrt, atan2
import urllib

# ============================================================================
# 설정 및 상수
# ============================================================================

load_dotenv()

KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
ALLOWED_REGION_TO_PLACE = {
            "강남구": "gangnam",
            "서초구": "seocho",
            "송파구": "songpa"
        }

LIBRARY_ADDRESS_MAP = {
    "도곡정보문화도서관": "서울특별시 강남구 도곡로18길 57",
    "개포하늘꿈도서관": "서울특별시 강남구 개포로110길 54",
    "논현도서관": "서울특별시 강남구 학동로43길 17",
    "논현문화마루도서관": "서울특별시 강남구 논현로131길 40",
    "논현문화마루도서관 (별관)": "서울특별시 강남구 학동로 169",
    "대치1동작은도서관": "서울특별시 강남구 남부순환로391길 19",
    "대치도서관": "서울특별시 강남구 삼성로 212",
    "못골도서관": "서울특별시 강남구 자곡로 116",
    "못골한옥어린이도서관": "서울특별시 강남구 자곡로7길 3",
    "삼성도서관": "서울특별시 강남구 봉은사로 616",
    "세곡도서관": "서울특별시 강남구 밤고개로 286",
    "세곡마루도서관": "서울특별시 강남구 헌릉로590길 68",
    "역삼2동작은도서관": "서울특별시 강남구 언주로 314",
    "역삼도서관": "서울특별시 강남구 역삼로7길 16",
    "역삼푸른솔도서관": "서울특별시 강남구 테헤란로8길 36",
    "열린도서관": "서울특별시 강남구 일원로 115",
    "일원라온영어구립도서관": "서울특별시 강남구 영동대로 22",
    "정다운도서관": "서울특별시 강남구 학동로67길 11",
    "즐거운도서관": "서울특별시 강남구 도곡로77길 23",
    "청담도서관": "서울특별시 강남구 압구정로79길 26",
    "행복한도서관": "서울특별시 강남구 영동대로65길 24",
    "개포4동주민도서관": "서울특별시 강남구 개포로38길 12",
    "도곡2동주민도서관": "서울특별시 강남구 남부순환로378길 34-9",
    "신사동주민도서관": "서울특별시 강남구 압구정로 128",
    "압구정동주민도서관": "서울특별시 강남구 압구정로 151",
    "일원본동주민도서관": "서울특별시 강남구 광평로 126",
    "개포1동주민도서관": "서울특별시 강남구 선릉로 35",

    "서초구립반포도서관": "서울특별시 서초구 고무래로 34",
    "서초구립내곡도서관": "서울특별시 서초구 청계산로7길 9-20",
    "서초구립양재도서관": "서울특별시 서초구 양재천로 33",
    "서초청소년도서관": "서울특별시 서초구 효령로77길 37",
    "방배숲환경도서관": "서울특별시 서초구 서초대로 160-7",
    "서이도서관": "서초구 서초대로70길 51",
    "잠원도서관": "서울특별시 서초구 나루터로 38",
    "방배도서관": "서울특별시 서초구 방배로 40",
    "서초그림책도서관": "서울특별시 서초구 명달로 150",
    "서초1동작은도서관": "서울특별시 서초구 사임당로 89",
    "서초3동작은도서관": "서울특별시 서초구 반포대로 58",
    "서초4동작은도서관": "서울특별시 서초구 서운로26길 3",
    "반포1동작은도서관": "서울특별시 서초구 사평대로 273",
    "반포2동작은도서관": "서울특별시 서초구 신반포로 127",
    "반포3동작은도서관": "서울특별시 서초구 신반포로23길 78",
    "반포4동작은도서관": "서울특별시 서초구 사평대로28길 70",
    "방배본동작은도서관": "서울특별시 서초구 동광로19길 38",
    "방배1동작은도서관": "서울특별시 서초구 효령로29길 43",
    "방배2동작은도서관": "서울특별시 서초구 청두곶길 36",
    "방배4동작은도서관": "서울특별시 서초구 방배로 173",
    "양재1동작은도서관": "서울특별시 서초구 바우뫼로 41",
    "양재2동작은도서관": "서울특별시 서초구 강남대로12길 44",
    "서초구전자도서관": "서울특별시 서초구 고무래로 34",

    "송파글마루도서관": "서울특별시 송파구 충민로 120",
    "송파어린이도서관": "서울특별시 송파구 올림픽로 105",
    "송파위례도서관": "서울특별시 송파구 위례광장로 210",
    "거마도서관": "서울특별시 송파구 거마로2길 19",
    "돌마리도서관": "서울특별시 송파구 백제고분로37길 16",
    "소나무언덕1호도서관": "서울특별시 송파구 올림픽로47길 9",
    "소나무언덕2호도서관": "서울특별시 송파구 석촌호수로 155",
    "소나무언덕3호도서관": "서울특별시 송파구 성내천로 319",
    "소나무언덕4호도서관": "서울특별시 송파구 송이로 34",
    "소나무언덕잠실본동도서관": "서울특별시 송파구 탄천동로 205",
    "송파어린이영어도서관": "서울특별시 송파구 오금로 1",
    "가락몰도서관": "서울특별시 송파구 양재대로 932",
    "풍납1동바람드리작은도서관": "서울특별시 송파구 풍성로5길 16",
    "거여1동다독다독작은도서관": "서울특별시 송파구 오금로53길 32",
    "거여2동향나무골작은도서관": "서울특별시 송파구 거마로2길 19",
    "마천1동새마을작은도서관": "서울특별시 송파구 마천로 303",
    "마천2동글수레작은도서관": "서울특별시 송파구 마천로 287",
    "방이1동조롱박작은도서관": "서울특별시 송파구 위례성대로16길 22",
    "방이2동새마을작은도서관": "서울특별시 송파구 올림픽로34길 5-13",
    "오륜동오륜작은도서관": "서울특별시 송파구 양재대로 1232",
    "오금동오동나무작은도서관": "서울특별시 송파구 중대로25길 5",
    "송파1동새마을작은도서관": "서울특별시 송파구 백제고분로 392",
    "송파2동송이골작은도서관": "서울특별시 송파구 송이로 32",
    "석촌동꿈다락작은도서관": "서울특별시 송파구 백제고분로37길 16",
    "삼전동삼학사작은도서관": "서울특별시 송파구 백제고분로 236",
    "가락본동글향기작은도서관": "서울특별시 송파구 송파대로28길 39",
    "가락2동로즈마리작은도서관": "서울특별시 송파구 중대로20길 6",
    "문정1동느티나무작은도서관": "서울특별시 송파구 동남로 116",
    "문정2동숯내작은도서관": "서울특별시 송파구 중대로 16",
    "장지동새마을작은도서관": "서울특별시 송파구 새말로19길 6",
    "잠실본동새내꿈작은도서관": "서울특별시 송파구 백제고분로 145",
    "잠실3동파랑새작은도서관": "서울특별시 송파구 잠실로 51-31",
    "잠실4동새마을작은도서관": "서울특별시 송파구 올림픽로35길 16",
    "잠실6동장미마을작은도서관": "서울특별시 송파구 올림픽로35길 120",
    "잠실7동부렴마을작은도서관": "서울특별시 송파구 올림픽로 44"
}

TIMEOUT = 5   # API 요청 타임아웃 (초)
TOP_N_MAP = 1  # 지도에 표시할 도서관 개수

# ============================================================================
# 페이지 설정
# ============================================================================

st.set_page_config(
    page_title="Book Toss - 도서관 검색",
    page_icon="📚",
)

# 커스텀 CSS
st.markdown("""
    <style>
        .main-header {
            text-align: center;
            padding: 2rem 0 1rem 0;
        }
        .main-title {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            font-size: 1.2rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .search-card {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            margin-bottom: 2rem;
        }
        .result-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
        }
        .info-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }
        .stButton>button {
            width: 100%;
            background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            vertical-align: top;
            padding: 0.5rem;
            border-radius: 10px;
            border: none;
            font-size: 1.1rem;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(102,126,234,0.3);
        }
        .library-item {
            background: rgb(190 190 190 / 20%);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.6rem;
        }
        .library-item.available {
            background: rgb(204 204 255/ 40%);
        }
        .distance-badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 0.3rem 0.8rem;
            margin: 0 0.3rem;
            vertical-align: 3px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .status-badge {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .status-available {
            background: #d4edda;
            color: #155724;
        }
        .status-unavailable {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# 유틸리티 함수
# ============================================================================

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 거리 계산 (Haversine 공식, km 단위)"""
    R = 6371  # 지구 반지름 (km)

    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c


def format_duration(seconds: Optional[int]) -> str:
    """초 단위 시간을 한국어로 읽기 좋은 문자열로 변환"""
    if seconds is None:
        return "정보 없음"
    minutes = max(1, (int(seconds) + 59) // 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}시간 {minutes}분" if minutes else f"{hours}시간"
    return f"{minutes}분"


def format_distance(route_distance_m: Optional[float], fallback_distance_km: float) -> str:
    """경로 거리(미터)와 직선거리(km)를 기반으로 표시 문자열 생성"""
    if route_distance_m:
        if route_distance_m >= 1000:
            return f"{route_distance_m / 1000:.1f} km"
        return f"{int(route_distance_m)} m"
    return f"{fallback_distance_km:.2f} km"


def parse_jsonl(jsonl_text: str) -> List[Dict]:
    """JSONL 텍스트를 파싱"""
    results = []
    for line in jsonl_text.strip().split('\n'):
        if line.strip():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results


def get_coordinates(address: str) -> Optional[Tuple[float, float, str]]:
    """주소를 좌표로 변환"""
    try:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        params = {"query": address}
        response = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        documents = data.get("documents", [])
        
        if not documents:
            return None
            
        doc = documents[0]
        lng = float(doc["x"])
        lat = float(doc["y"])
        if doc.get("address") is not None:
            region = doc["address"].get("region_2depth_name", "")
        else:
            region = doc.get("road_address", {}).get("region_2depth_name", "")
        
        if not region:
            return None
        
        return (lng, lat, region)
    except Exception as e:
        st.error(f"좌표 변환 중 오류: {e}")
        return None

def get_library_with_distance(library_name: str, user_lat: float, user_lng: float) -> Optional[Dict]:
    """도서관 정보 및 거리 계산"""
    if library_name not in LIBRARY_ADDRESS_MAP:
        return None
    
    address = LIBRARY_ADDRESS_MAP[library_name]
    coords = get_coordinates(address)
    
    if not coords:
        return None
    
    lib_lng, lib_lat, _ = coords
    straight_distance_km = calculate_distance(user_lat, user_lng, lib_lat, lib_lng)

    route_info = route_points(user_lng, user_lat, lib_lng, lib_lat)
    polyline_points = None
    route_duration = None
    route_distance_m = None

    if route_info:
        polyline_points, route_duration, route_distance_m = route_info

    distance_km = (route_distance_m / 1000) if route_distance_m else straight_distance_km

    return {
        "name": library_name,
        "address": address,
        "lat": lib_lat,
        "lng": lib_lng,
        "distance": distance_km,
        "duration": route_duration,
        "route_distance_m": route_distance_m,
        "polyline_points": polyline_points,
        "straight_distance": straight_distance_km,
    }


def process_book_results(
    jsonl_data: str, user_lat: float, user_lng: float
) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """도서 검색 결과 처리 및 도서관별 거리 계산 (첫 번째 표지 이미지 포함)"""
    results = parse_jsonl(jsonl_data)
    first_cover_image = next(
        (item.get("cover_image") for item in results if item.get("cover_image")), None
    )

    # 도서관별로 그룹화 (available=true만)
    available_libraries = {}
    for item in results:
        if item.get("available", False):
            lib_name = item["library"]
            if lib_name not in available_libraries:
                available_libraries[lib_name] = []
            available_libraries[lib_name].append(item)

    # 도서관 좌표 및 거리 계산
    library_coords = []
    for lib_name in available_libraries.keys():
        lib_info = get_library_with_distance(lib_name, user_lat, user_lng)
        if lib_info:
            lib_info["books"] = available_libraries[lib_name]
            library_coords.append(lib_info)
    
    # 거리순 정렬
    library_coords.sort(key=lambda x: x["distance"])

    # 지도용 (상위 N개)
    map_libraries = library_coords[:TOP_N_MAP]
    
    return map_libraries, library_coords, first_cover_image

def route_points(start_lng, start_lat, end_lng, end_lat):
    """카카오 길찾기 API로 이동 경로 및 소요 시간/거리 조회"""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{start_lng},{start_lat}",
        "destination": f"{end_lng},{end_lat}"
    }

    def _show_route_warning():
        if not st.session_state.get("_route_warning_shown"):
            st.warning("길찾기 정보를 불러오지 못해 직선거리로 대체합니다.")
            st.session_state["_route_warning_shown"] = True

    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        res.raise_for_status()
    except requests.RequestException as exc:
        _show_route_warning()
        print(f"[route_points] request error: {exc}")
        return None

    data = res.json()
    routes = data.get("routes", [])

    if not routes:
        _show_route_warning()
        return None

    route = routes[0]
    result_code = route.get("result_code", 0)
    if result_code != 0:
        _show_route_warning()
        return None

    summary = route.get("summary", {})

    # 도로 좌표 추출
    coords = []
    for section in route.get("sections", []):
        for road in section.get("roads", []):
            coords.extend(road.get("vertexes", []))

    if not coords:
        _show_route_warning()
        return None

    # vertexes는 [x1, y1, x2, y2, ...] 형태이므로 2개씩 묶기
    path = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]

    # 자바스크립트 코드로 경로 표시
    polyline_points = ",\n".join(
        [f"new kakao.maps.LatLng({y}, {x})" for x, y in path]
    )

    duration = summary.get("duration")
    distance = summary.get("distance")

    return polyline_points, duration, distance

def generate_map_html(user_lat: float, user_lng: float, 
                     library_coords: List[Dict], book_name: str) -> str:
    """카카오맵 HTML 생성"""

    user_html = f"""
        <div class="user"">
            <div>내 위치</div>
        </div>
        """

    markers_js = f"""
        var userLatLng = new kakao.maps.LatLng({user_lat}, {user_lng});
        var userMarker = new kakao.maps.Marker({{
            position: userLatLng,
            map: map,
            image: new kakao.maps.MarkerImage(
                "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png",
                new kakao.maps.Size(24, 35)
            )
        }});
        bounds.extend(userLatLng);

        var userOverlay = new kakao.maps.CustomOverlay({{
            content: `{user_html}`,
            map: null,
            position: userMarker.getPosition()
        }});

        userOverlay.setMap(map);
        
        var overlays = [];
    """
    
    for idx, lib in enumerate(library_coords):

        duration_text = format_duration(lib.get("duration"))
        distance_text = format_distance(
            lib.get("route_distance_m"),
            lib.get("straight_distance", lib["distance"])
        )

        info_html = f"""
        <div class="wrap">
            <div class="info">
                <div class="title">
                    {lib['name']}
                    <div class="close" onclick="closeOverlay({idx})" title="닫기"></div>
                </div>
                <div class="body">
                    <div class="desc">
                        <div class="ellipsis">📍 {lib['address']}</div>
                        <div>🚘 이동시간: {duration_text}</div>
                        <div>📏 이동거리: {distance_text}</div>
                        <div>⤴️ <a href='https://map.kakao.com/link/from/내위치,{user_lat},{user_lng}/to/{lib['name']},{lib['lat']},{lib['lng']}' target='_blank' class='link'>길찾기</a></div>
                    </div>
                </div>
            </div>
        </div>
        """

        polyline_js = ""
        if lib.get("polyline_points"):
            polyline_js = f"""
                var linePath = [
                    {lib['polyline_points']}
                ];

                var polyline = new kakao.maps.Polyline({{
                    path: linePath,
                    strokeWeight: 5,
                    strokeColor: '#0078ff',
                    strokeOpacity: 0.9,
                    strokeStyle: 'solid'
                }});
                polyline.setMap(map);
            """
        
        markers_js += f"""
            (function(index) {{
                var libLatLng = new kakao.maps.LatLng({lib['lat']}, {lib['lng']});
                var marker = new kakao.maps.Marker({{
                    position: libLatLng,
                    map: map
                }});

                // 경로 라인
                {polyline_js}
                
                var overlay = new kakao.maps.CustomOverlay({{
                    content: `{info_html}`,
                    map: null,
                    position: marker.getPosition()
                }});
                
                overlays[index] = overlay;
                overlay.setMap(map);

                kakao.maps.event.addListener(marker, 'click', function() {{
                    overlay.setMap(map);
                }});
                
                bounds.extend(libLatLng);
                
                var level = map.getLevel();
                var offset;
                if (level <= 3) offset = 0.001;
                else if (level <= 5) offset = 0.002;
                else if (level <= 7) offset = 0.005;
                else if (level <= 9) offset = 0.007;
                else offset = 0.01;

                bounds.extend(new kakao.maps.LatLng(libLatLng.getLat() + offset, libLatLng.getLng() + offset));
                bounds.extend(new kakao.maps.LatLng(libLatLng.getLat() + offset, libLatLng.getLng() - offset));
            }})({idx});
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <style>
            .wrap {{
                position: absolute;
                left: 0;
                bottom: 50px;
                width: 250px;
                margin-left: -125px;
                text-align: left;
                font-size: 13px;
                font-family: 'Malgun Gothic', sans-serif;
                line-height: 1.5;
            }}
            .info {{
                width: 250px;
                background: #fff;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                overflow: hidden;
            }}
            .user {{
                border-radius: 10px;
                background: #fff;
                width: fit-content;
                padding: 5px 8px;
                margin-bottom: 110px;
                text-align: center;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Malgun Gothic', sans-serif;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                line-height: 1.5;
            }}
            .title {{
                position: relative;
                padding: 10px 35px 10px 15px;
                background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-size: 15px;
                font-weight: 600;
            }}
            .close {{
                position: absolute;
                top: 12px;
                right: 12px;
                width: 16px;
                height: 16px;
                background: url('https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/overlay_close.png') no-repeat;
                background-size: 100%;
                cursor: pointer;
                filter: brightness(0) invert(1);
            }}
            .body {{
                padding: 12px 15px;
            }}
            .desc {{
                display: flex;
                flex-direction: column;
                gap: 6px;
            }}
            .link {{
                color: #667eea;
                text-decoration: none;
                font-weight: 500;
            }}
            .link:hover {{
                text-decoration: underline;
            }}
            .info:after {{
                content: '';
                position: absolute;
                left: 50%;
                bottom: -12px;
                margin-left: -11px;
                width: 22px;
                height: 12px;
                background: url('https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/vertex_white.png');
            }}
        </style>
        <script type="text/javascript"
            src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_API_KEY}&libraries=services">
        </script>
    </head>
    <body style="margin:0px">
        <div id="map" style="width:100%;height:550px;border-radius:10px;"></div>
        <script>
            var mapContainer = document.getElementById('map');
            var mapOption = {{
                center: new kakao.maps.LatLng({user_lat}, {user_lng}),
                level: 6
            }};
            var map = new kakao.maps.Map(mapContainer, mapOption);
            var zoomControl = new kakao.maps.ZoomControl();
            map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);
            var bounds = new kakao.maps.LatLngBounds();
            {markers_js}
            
            function closeOverlay(index) {{
                if (overlays[index]) {{
                    overlays[index].setMap(null);
                }}
            }}
            
            map.setBounds(bounds);
        </script>
    </body>
    </html>
    """

def show_library_search_button(book_name: str, user_region: str):
    """지역별 도서관 검색 버튼을 표시"""
    encoded_book = urllib.parse.quote(book_name)

    library_urls = {
        "강남구": f"https://library.gangnam.go.kr/intro/menu/10003/program/30001/plusSearchResultList.do?searchType=SIMPLE&searchMenuCollectionCategory=&searchCategory=ALL&searchKey=ALL&searchKeyword={encoded_book}&searchLibrary=ALL",
        "서초구": f"https://public.seocholib.or.kr/KeywordSearchResult/{encoded_book}",
        "송파구": f"https://www.splib.or.kr/intro/menu/10003/program/30001/plusSearchSimple.do"
    }

    # 현재 지역에 맞는 URL 찾기
    for region, url in library_urls.items():
        if region.startswith(user_region):
            st.link_button(
                f"🔗 {region} 통합도서관에서 직접 검색하기",
                url,
                width='stretch'
            )
            break  # 찾으면 반복 종료

# ============================================================================
# UI 렌더링
# ============================================================================

# 헤더
st.markdown("""
    <div class="main-header">
        <div class="main-title">📚 Book Toss</div>
        <div class="subtitle">내 근처 공공 도서관을 쉽게 찾아보세요</div>
    </div>
    """, unsafe_allow_html=True)

# 검색 폼
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    address = st.text_input(
        "📍 내 주소",
        placeholder="서울특별시 강남구 개포로 416"
    )

with col2:
    book_name = st.text_input(
        "📖 찾고 싶은 도서",
        placeholder="트렌드 코리아 2026"
    )

with col3:
    st.write("")
    st.write("")
    search_btn = st.button("🔍 검색하기", use_container_width=True)

# 검색 실행
if search_btn:
    if not address.strip():
        st.warning("📍 주소를 입력해주세요")
        st.stop()
    elif not book_name.strip():
        st.warning("📖 도서명을 입력해주세요")
        st.stop()
    else:
        st.session_state["address"] = address.strip()
        st.session_state["book_name"] = book_name.strip()

# 결과 표시
if ("address" in st.session_state and "book_name" in st.session_state and
    st.session_state["address"].strip() and st.session_state["book_name"].strip()):
    # st.markdown("---")
    
    with st.spinner("🔍 도서관 검색 중..."):
        # 사용자 위치 좌표 가져오기
        user_coords = get_coordinates(st.session_state["address"])
        
        if not user_coords:
            st.error("❌ 입력하신 주소를 찾을 수 없거나 주소 정보가 부족합니다. 주소를 다시 확인해주세요.")
            st.stop()
        
        user_lng, user_lat, user_region = user_coords

        # 실제 도서관 검색 실행 (pipeline_graph 연동)
        sys.path.insert(0, "00_src")
        from graph.pipeline_graph import run_once

        place = ALLOWED_REGION_TO_PLACE.get(user_region)

        if not place:
            st.warning("😥 입력하신 지역의 서비스는 아직 준비 중입니다. 강남구, 서초구, 송파구 내에서 검색해주세요.")
            st.stop()

        # LangGraph 파이프라인 실행 (브라우저 자동화 + HTML 파싱)
        result = run_once(place=place, title=st.session_state["book_name"])
        # JSONL 데이터 추출
        jsonl_path = result.get("out_jsonl")
        if jsonl_path and os.path.exists(jsonl_path):
            with open(jsonl_path, "r", encoding="utf-8") as f:
                jsonl_data = f.read()
        else:
            st.error(":x: 도서관 검색에 실패했습니다. 다시 시도해주세요.")
            st.stop()

        map_libraries, all_libraries, first_cover_image = process_book_results(
            jsonl_data, user_lat, user_lng
        )

        if not all_libraries:
            st.warning("⚠️ 현재 대출 가능한 도서관을 찾을 수 없습니다.")
            show_library_search_button(st.session_state["book_name"], user_region)
            st.stop()

        # 결과 카드
        st.write("")
        with st.container(horizontal_alignment="center"):
            if first_cover_image:
                st.image(
                    first_cover_image,
                    width=200,
                    caption=None,
                    clamp=True,
                    channels="RGB",
                    output_format="auto",
                )
        st.markdown(f"""
        <div class="result-card">
            <h3 style="text-align:center;">📖 {st.session_state['book_name']}</h3>
            <p style="margin:0.5rem 0 0 0; opacity:0.9;text-align:center;">
                {user_region}에서 대출 가능한 도서관 {len(all_libraries)}곳을 찾았어요! 🥳
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 지도 표시 (가장 가까운 N개)
        if map_libraries:
            st.markdown(f"#### 🗺️ 가장 가까운 도서관")
            map_html = generate_map_html(
                user_lat, user_lng, map_libraries, st.session_state['book_name']
            )
            st.components.v1.html(map_html, height=570)
        
        # 전체 도서관 목록
        for idx, lib in enumerate(all_libraries):
            is_top = idx < TOP_N_MAP
            status_class = "available" if is_top else ""
            duration_text = format_duration(lib.get("duration"))
            distance_text = format_distance(
                lib.get("route_distance_m"),
                lib.get("straight_distance", lib["distance"])
            )
            distance_badge = f"{duration_text}"
            
            with st.container():
                st.markdown(f"""
                <div class="library-item {status_class}">
                    <h4>
                        {'🥇' if idx == 0 else '🥈' if idx == 1 else ''} {lib['name']}
                        <span class="distance-badge">차로 {distance_badge}</span>
                    </h4>
                    <p style="margin:0 0; display:flex; align-items:center; gap:0.4rem;">
                        <span style="flex:0 1 auto; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            {lib['address']}
                        </span>
                        <a href="https://map.kakao.com/link/from/내위치,{user_lat},{user_lng}/to/{lib['name']},{lib['lat']},{lib['lng']}" 
                        target="_blank"
                        title="길찾기"
                        style="
                            display:inline-flex;
                            align-items:center;
                            justify-content:center;
                            height:1.7rem;
                            border-radius:50%;
                            background: none;
                            font-size:0.8rem;
                            flex-shrink:0;
                        ">
                        길찾기
                        </a>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📚 대출 가능 도서 {len(lib['books'])}권", expanded=True):
                    for book in lib['books']:
                        if book['cover_image']:
                            st.markdown(f"""
                            <div style="display:flex; align-items:flex-start; gap:0.8rem; margin-bottom:0.8rem;">
                                <img src="{book['cover_image']}" alt="book cover" width="90" height="120"
                                style="border-radius:6px; object-fit:cover; flex-shrink:0;">
                                <div>
                                    <div style="font-weight:bold; font-size:1.2rem;">{book['title']}</div>
                                    <div style="margin-top:0.3rem;">· 자료실: {book.get('room', 'N/A')}</div>
                                    <div>· 청구기호: {book.get('call_number', 'N/A')}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="display:flex; align-items:flex-start; gap:0.8rem; margin-bottom:0.8rem;">
                                <div>
                                    <div style="font-weight:bold; font-size:1.2rem;">{book['title']}</div>
                                    <div style="margin-top:0.3rem;">· 자료실: {book.get('room', 'N/A')}</div>
                                    <div>· 청구기호: {book.get('call_number', 'N/A')}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                st.write("")
        show_library_search_button(st.session_state["book_name"], user_region)

        # 푸터 안내
        st.markdown("---")
        st.markdown("""
        <div style="text-align:center; color:#999; font-size:0.9rem; padding:1rem 0;">
            💡 <b>TIP:</b> 지도의 도서관 마커를 클릭하면 상세 정보를 확인할 수 있어요
        </div>
        """, unsafe_allow_html=True)
