"""보조금 조건 검색 서비스 — FastAPI 백엔드"""

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional

from data import SUBSIDIES, REGIONS, CATEGORIES, BUSINESS_TYPES, GENDERS

app = FastAPI(title="보조금 조건 검색 서비스")


@app.get("/api/filters")
def get_filters():
    """검색 필터에 사용할 옵션 목록 반환"""
    return {
        "regions": REGIONS,
        "categories": CATEGORIES,
        "business_types": BUSINESS_TYPES,
        "genders": GENDERS,
    }


@app.get("/api/subsidies")
def search_subsidies(
    age: Optional[int] = Query(None, description="신청자 만 나이"),
    gender: Optional[str] = Query(None, description="성별 (남성/여성)"),
    region: Optional[str] = Query(None, description="지역"),
    category: Optional[str] = Query(None, description="보조금 분류"),
    business_type: Optional[str] = Query(None, description="업종"),
    income_percentile: Optional[int] = Query(None, description="소득분위 (1-100)"),
    keyword: Optional[str] = Query(None, description="키워드 검색"),
):
    """조건에 맞는 보조금 목록을 검색"""
    results = SUBSIDIES

    if age is not None:
        results = [s for s in results if s["min_age"] <= age <= s["max_age"]]

    if gender:
        results = [s for s in results if s["gender"] in ("무관", gender)]

    if region:
        results = [s for s in results if region in s["regions"]]

    if category:
        results = [s for s in results if s["category"] == category]

    if business_type:
        results = [
            s for s in results
            if not s["business_types"] or business_type in s["business_types"]
        ]

    if income_percentile is not None:
        results = [s for s in results if income_percentile <= s["max_income_percentile"]]

    if keyword:
        kw = keyword.lower()
        results = [
            s for s in results
            if kw in s["name"].lower()
            or kw in s["description"].lower()
            or kw in s["org"].lower()
        ]

    return {"count": len(results), "results": results}


@app.get("/api/subsidies/{subsidy_id}")
def get_subsidy(subsidy_id: int):
    """보조금 상세 정보 조회"""
    for s in SUBSIDIES:
        if s["id"] == subsidy_id:
            return s
    return {"error": "보조금을 찾을 수 없습니다"}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
