# 보조금 검색 서비스 기능 확장 및 성능 개선 설계

> 작성일: 2026-03-26
> 상태: 설계 승인 완료

---

## 1. 개요

### 1.1 현재 상태
- FastAPI + Vanilla JS 단일 페이지 보조금 검색 서비스
- `data.py`에 12개 샘플 보조금 하드코딩
- SEO, 캐싱, 성능 최적화, 애드센스/Analytics 미적용
- 배포 환경 미구성

### 1.2 목표
- 공공 API 연동으로 실제 보조금 데이터 확보 (2,000건+)
- Jinja2 SSR 전환으로 검색엔진 인덱싱 가능한 구조 확보
- 단계적 콘텐츠 페이지 확장으로 SEO 트래픽 확보 → 애드센스 수익화
- TTL 기반 캐싱 + 성능 최적화로 사용자 경험 개선

### 1.3 접근 방식
단계적 확장 (A→B→C→D). 각 단계가 독립적으로 동작하며 매 단계마다 배포 가능.

---

## 2. 프로젝트 구조

```
subsidy-search/
├── main.py                    # FastAPI 앱 + 라우팅 + lifespan 이벤트
├── api_client.py              # 멀티소스 공공 API 클라이언트
├── cache.py                   # TTL 기반 인메모리 캐시
├── data_cleaner.py            # 데이터 정제/매핑 로직
├── models.py                  # 데이터 모델 (Subsidy dataclass)
├── data.py                    # 폴백용 샘플 데이터 (기존 유지)
├── requirements.txt
├── mappings/
│   ├── categories.json        # 카테고리 매핑 (코드 수정 없이 확장 가능)
│   ├── regions.json           # 지역 매핑
│   └── income_thresholds.json # 가구형태별 기준중위소득 (계산기용)
├── templates/
│   ├── base.html              # 공통 레이아웃 (head, nav, footer, 애드센스 슬롯)
│   ├── index.html             # 메인 검색 페이지
│   ├── subsidy_detail.html    # 보조금 상세 페이지 (2단계)
│   ├── calculator.html        # 보조금 매칭 계산기 (2단계)
│   ├── category_list.html     # 카테고리별 목록 (3단계)
│   ├── region_list.html       # 지역별 목록 (3단계)
│   └── guide.html             # 가이드/블로그 (4단계)
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── images/
└── seo/
    ├── sitemap.py             # 동적 sitemap.xml 생성
    └── robots.txt
```

---

## 3. 라우팅 구조

| URL 패턴 | 설명 | 단계 |
|-----------|------|------|
| `/` | 메인 검색 페이지 | 1단계 |
| `/api/filters` | 필터 옵션 API | 1단계 |
| `/api/subsidies` | 보조금 검색 API | 1단계 |
| `/api/subsidies/{id}` | 보조금 상세 API | 1단계 |
| `/sitemap.xml` | 동적 사이트맵 | 1단계 |
| `/robots.txt` | 크롤러 안내 | 1단계 |
| `/subsidies/{id}/{slug}` | 보조금 상세 페이지 (SEO URL) | 2단계 |
| `/calculator` | 보조금 매칭 계산기 | 2단계 |
| `/category/{category}` | 카테고리별 목록 | 3단계 |
| `/region/{region}` | 지역별 목록 | 3단계 |
| `/guide/{slug}` | 가이드 콘텐츠 | 4단계 |

- slug는 한글 + 숫자 ID 조합 (예: `/subsidies/123/청년-월세-지원`)

---

## 4. 데이터 마이그레이션

### 4.1 기존 `data.py` 필드명 → 새 `Subsidy` 모델 매핑

기존 `data.py`의 dict 구조와 새 `Subsidy` dataclass 간 필드명이 다르므로, 폴백 로드 시 변환이 필요하다.

| 기존 `data.py` | 새 `Subsidy` 모델 | 변환 |
|----------------|-------------------|------|
| `id` (int) | `id` (str) | `str(id)` |
| `min_age` | `age_min` | 이름 변경 |
| `max_age` | `age_max` | 이름 변경 |
| `org` | `organization` | 이름 변경 |
| `regions` | `region` | 이름 변경 |
| `required_docs` | `documents` | 이름 변경 |
| `max_income_percentile` | `income_percentile` | 이름 변경 |
| `gender: "무관"` | `gender: None` | `"무관"` → `None` |
| `business_types` (없을 수 있음) | `business_types` | 있으면 그대로, 없으면 `[]` |
| (없음) | `slug` | 보조금명에서 자동 생성 |
| (없음) | `source` | `"fallback"` 고정 |
| (없음) | `url` | `None` |
| (없음) | `raw_data` | 원본 dict 그대로 저장 |

- `data.py`는 수정하지 않음 (폴백 원본 유지)
- `data_cleaner.py`에 `convert_legacy(raw: dict) -> Subsidy` 함수를 추가하여 로드 시 변환 (폴백 전용, API 안정화 후 deprecated 가능)
- 모든 `id`는 내부적으로 `str` 타입으로 통일. 기존 int ID는 `str()` 변환.
- API 라우트 `/api/subsidies/{id}`는 `str` 타입으로 변경

---

## 5. 데이터 소스 및 API 클라이언트

### 5.1 데이터 소스 (우선순위)

| 순위 | API | 예상 데이터 | 용도 |
|------|-----|------------|------|
| 1순위 | 보조금24 API | ~1,075건 | 메인 데이터 소스 |
| 2순위 | 기업마당 API (bizinfo.go.kr) | ~1,000건+ | 지자체 포함 보완 |
| 3순위 | 정부24 API | 보완용 | 보조금24에 없는 데이터 보완 |

### 5.2 멀티소스 API 클라이언트 (`api_client.py`)

```python
from abc import ABC, abstractmethod

class BaseAPIClient(ABC):
    """공공 API 클라이언트 추상 클래스"""

    @abstractmethod
    async def fetch_all(self) -> list[dict]:
        """전체 보조금 데이터를 가져옴 (페이지네이션 처리 포함)"""
        ...

    @abstractmethod
    async def fetch_detail(self, subsidy_id: str) -> dict | None:
        """개별 보조금 상세 정보"""
        ...

    @abstractmethod
    def normalize(self, raw: dict) -> Subsidy:
        """API 원본 데이터를 Subsidy 인스턴스로 변환"""
        ...

class Bojokim24Client(BaseAPIClient):
    """보조금24 API 클라이언트"""
    ...

class BizinfoClient(BaseAPIClient):
    """기업마당 API 클라이언트"""
    ...

class Gov24Client(BaseAPIClient):
    """정부24 API 클라이언트"""
    ...

class AggregatedClient:
    """여러 API 소스를 통합하여 관리"""
    def __init__(self, clients: list[BaseAPIClient]):
        self.clients = clients

    async def fetch_all_sources(self) -> list[Subsidy]:
        """모든 소스에서 데이터를 수집하고 중복 제거. 각 클라이언트의 normalize()로 Subsidy 변환."""
        ...
```

### 5.3 API 호출 전략

- **사용자 요청 시 API 직접 호출하지 않음**
- 서버 시작 시(`lifespan` 이벤트) batch fetch로 전체 데이터 수집
- **캐시 갱신 루프**: lifespan에서 별도 백그라운드 태스크로 등록. `subsidies:list` TTL(24시간) 주기로 자동 re-fetch.
  - 정상 응답 시 캐시 갱신
  - API 장애 시 stale-while-error 적용 (만료된 캐시 데이터를 계속 제공)
- API 호출 실패 시 최대 3회 재시도 (exponential backoff)
- 모든 API 소스 + 캐시 실패 시 `data.py`의 12개 샘플 데이터를 폴백으로 사용

```python
async def data_refresh_loop(client: AggregatedClient, cache: TTLCache):
    """24시간 주기로 API 데이터를 갱신하는 백그라운드 태스크"""
    while True:
        await asyncio.sleep(86400)  # 24시간
        try:
            subsidies = await client.fetch_all_sources()
            cache.set("subsidies:list", subsidies, ttl_seconds=86400)
        except Exception:
            pass  # stale-while-error: 기존 만료 데이터 유지
```

### 5.4 중복 제거 전략

멀티소스에서 동일 보조금이 수집될 수 있으므로:

- **매칭 기준**: 보조금명 정규화(공백/특수문자 제거 후 비교) + 기관명
- **우선순위**: 보조금24 > 기업마당 > 정부24 (Section 5.1 순위)
- 중복 발견 시 높은 순위 소스의 데이터를 채택
- 낮은 순위 소스의 `raw_data`는 버림 (높은 순위 데이터에 `source` 필드로 출처만 기록)

### 5.5 인증

- 환경변수로 API 키 관리:
  - `DATA_GO_KR_API_KEY` (보조금24 + 정부24)
  - `BIZINFO_API_KEY` (기업마당)
  - `KAKAO_JS_KEY` (카카오톡 공유 SDK, 2단계)
  - `SITE_DOMAIN` (sitemap, robots.txt, canonical URL에 사용)

---

## 6. 데이터 모델

```python
@dataclass
class Subsidy:
    id: str                        # 고유 ID (API 원본 ID)
    name: str                      # 보조금명
    slug: str                      # URL용 슬러그 (한글, 예: "청년-월세-지원")
    category: str                  # 통일된 카테고리
    description: str               # 설명
    amount: str                    # 지원 금액 (원본 텍스트)
    organization: str              # 관할 기관
    region: list[str]              # 대상 지역
    age_min: int | None            # 최소 나이
    age_max: int | None            # 최대 나이
    gender: str | None             # 성별 제한
    income_percentile: int | None  # 소득분위 기준
    business_types: list[str]      # 업종
    deadline: str | None           # 마감일
    documents: list[str]           # 필요 서류
    url: str | None                # 원본 공고 링크
    source: str                    # 데이터 출처 ("bojokim24", "bizinfo", "gov24")
    raw_data: dict                 # API 원본 데이터 보존
```

- `slug` 생성: 보조금명에서 특수문자 제거, 공백을 `-`로 치환
- URL 형식: `/subsidies/{id}/{slug}` (예: `/subsidies/123/청년-월세-지원`)
- **slug 불일치 처리**: `{id}`가 실제 식별자. `/subsidies/123/wrong-slug` 접근 시 올바른 slug로 301 리다이렉트

---

## 7. 데이터 정제 (`data_cleaner.py`)

### 7.1 정제 로직

- 빈 값 처리: `None`, 빈 문자열 → 기본값 또는 "정보 없음"
- 문자열 정규화: 공백 트림, 중복 공백 제거
- 중복 제거: 보조금명 + 기관명 기준 dedup (멀티소스 간 중복 포함)

### 7.2 매핑 파일 (`mappings/`)

코드 수정 없이 매핑을 추가/변경할 수 있도록 별도 JSON 파일로 관리.

**`mappings/categories.json`:**
```json
{
  "mapping": {
    "창업지원": "창업",
    "창업육성": "창업",
    "고용촉진": "고용",
    "취업지원": "고용",
    "주거안정": "주거",
    "전세자금": "주거"
  },
  "default": "기타"
}
```

**`mappings/regions.json`:**
```json
{
  "mapping": {
    "서울특별시": "서울",
    "서울시": "서울",
    "부산광역시": "부산",
    "부산시": "부산"
  },
  "default": "전국"
}
```

- `data_cleaner.py`는 시작 시 매핑 파일을 로드하여 사용 (서버 재시작 시 반영)
- API별 분류 체계 차이를 우리 서비스 기준으로 통일

---

## 8. 캐싱 (`cache.py`)

### 8.1 TTL 기반 인메모리 캐시

```python
class TTLCache:
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
        self._stale: dict[str, Any] = {}                 # stale-while-error용 백업

    def get(self, key: str) -> Any | None
    def get_stale(self, key: str) -> Any | None          # 만료 데이터 반환 (장애 시)
    def set(self, key: str, value: Any, ttl_seconds: int) -> None
    def invalidate(self, key: str) -> None
    def clear_expired(self) -> None
```

**stale 저장소 동작:**
- `set()` 호출 시 `_store`에 저장하면서 동시에 `_stale`에도 복사
- `clear_expired()`는 `_store`에서만 만료 항목을 삭제. `_stale`은 건드리지 않음.
- `get()` 실패 시(만료) → `get_stale()`로 이전 값 반환 (stale-while-error)
- `_stale`은 새 값으로 `set()` 될 때만 덮어씌워짐

### 8.2 TTL 설정

| 캐시 대상 | TTL | 키 패턴 |
|-----------|-----|---------|
| 보조금 전체 목록 | 24시간 | `subsidies:list` |
| 보조금 상세 | 6시간 | `subsidies:detail:{id}` |
| 필터 옵션 | 24시간 | `filters:all` |
| 카테고리별 목록 | 24시간 | `subsidies:category:{name}` |
| 지역별 목록 | 24시간 | `subsidies:region:{name}` |
| sitemap.xml | 24시간 | `seo:sitemap` |

### 8.3 자동 정리

- `clear_expired()`를 FastAPI lifespan 이벤트에서 `asyncio.create_task`로 등록
- 5분 주기로 만료된 `_store` 엔트리를 자동 삭제 (메모리 누수 방지)
- `_stale`은 정리하지 않음 (stale-while-error 보장)

```python
async def cache_cleanup_loop(cache: TTLCache):
    while True:
        await asyncio.sleep(300)  # 5분
        cache.clear_expired()  # _store만 정리, _stale 유지
```

참고: 데이터 갱신(re-fetch)은 이 정리 루프가 아닌 별도 `data_refresh_loop`에서 담당 (Section 5.3 참조).

---

## 9. 성능 최적화

| 항목 | 구현 방법 |
|------|-----------|
| Gzip 압축 | `GZipMiddleware(app, minimum_size=500)` |
| 정적 파일 캐싱 | `Cache-Control: public, max-age=604800` (7일) |
| CSS/JS 분리 | `static/index.html`에서 `static/css/style.css`, `static/js/main.js`로 분리 |
| 폰트 최적화 | Pretendard `font-display: swap` |
| API 캐싱 | 섹션 8 참조 (사용자 요청 시 캐시에서만 제공) |

---

## 10. SEO 및 구조화 데이터

### 10.1 메타 태그 (`base.html`에서 동적 생성)

```html
<title>{{ page_title }} | 보조금 검색</title>
<meta name="description" content="{{ page_description }}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{{ canonical_url }}">

<!-- Open Graph -->
<meta property="og:title" content="{{ page_title }}">
<meta property="og:description" content="{{ page_description }}">
<meta property="og:type" content="{{ og_type }}">
<meta property="og:url" content="{{ canonical_url }}">
<meta property="og:locale" content="ko_KR">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{{ page_title }}">
<meta name="twitter:description" content="{{ page_description }}">
```

### 10.2 페이지별 title/description (연도 포함)

| 페이지 | title | description |
|--------|-------|-------------|
| 메인 | 보조금 조건 검색 서비스 | 나이, 지역, 소득 조건에 맞는 정부 보조금을 검색하세요 |
| 상세 | {보조금명} - 신청 조건 및 방법 (2026) | {보조금명}: {금액}, {대상}, {마감일} 안내 |
| 계산기 | 2026 보조금 매칭 계산기 - 내게 맞는 보조금 찾기 | 나이, 지역, 소득 조건을 입력하면 받을 수 있는 보조금을 알려드립니다 |
| 카테고리 | 2026 {카테고리} 보조금 목록 ({N}건) | 2026년 {카테고리} 관련 정부 보조금 {N}건 |
| 지역 | 2026 {지역} 보조금 목록 ({N}건) | 2026년 {지역}에서 신청 가능한 정부 보조금 {N}건 |
| 가이드 | {가이드 제목} | {가이드 요약 150자} |

- 연도는 서버 시간 기준 `datetime.now().year`로 동적 삽입

### 10.3 JSON-LD 구조화 데이터

| 페이지 | 스키마 |
|--------|--------|
| 메인 | `WebSite` + `SearchAction` |
| 상세 | `GovernmentService` + `FAQPage` |
| 계산기 | `WebApplication` |
| 목록 | `ItemList` |
| 가이드 | `Article` |

**상세 페이지 FAQPage 스키마:**

```json
{
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "신청 자격은?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "{age_min}~{age_max}세, {region}, 소득분위 {income_percentile}% 이하"
      }
    },
    {
      "@type": "Question",
      "name": "지원 금액은?",
      "acceptedAnswer": { "@type": "Answer", "text": "{amount}" }
    },
    {
      "@type": "Question",
      "name": "신청 방법은?",
      "acceptedAnswer": { "@type": "Answer", "text": "{organization}을 통해 신청. 필요서류: {documents}" }
    }
  ]
}
```

- 구글 검색결과에 FAQ 리치스니펫으로 노출되어 클릭률 향상

### 10.4 상세 페이지 내부 링크 블록

각 상세 페이지 하단에 3개 내부 링크 블록:

1. **"같은 카테고리 보조금"** → `/category/{category}` 링크
2. **"같은 지역 보조금"** → `/region/{region}` 링크
3. **"관련 보조금 3건"** → 같은 카테고리 내 다른 보조금 상세 페이지 링크

- 내부 링크가 SEO 권위도를 페이지 간 순환시킴

### 10.5 sitemap.xml / robots.txt

**sitemap.xml (`seo/sitemap.py`):**
- 메인 페이지 + 모든 보조금 상세 페이지 + 카테고리/지역 목록 + 계산기 페이지
- `lastmod`를 API 캐시 갱신 시점으로 설정
- sitemap 자체도 TTL 24시간 캐싱

**robots.txt:**
```
User-agent: *
Allow: /
Disallow: /api/
Sitemap: https://{domain}/sitemap.xml
```

- `{domain}`은 환경변수 `SITE_DOMAIN`에서 읽음 (Section 5.5)
- `robots.txt`는 FastAPI 라우트로 동적 제공 (도메인 삽입)

---

## 11. 보조금 매칭 계산기 (2단계)

### 11.1 페이지: `/calculator`

Jinja2 SSR 페이지. 사용자가 조건을 입력하면 매칭되는 보조금을 보여줌.

### 11.2 입력 폼

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| 나이 | number | O | 만 나이 |
| 지역 | select | O | 시/도 선택 |
| 월소득 | number | O | 만원 단위 |
| 가구 형태 | select | O | 1인가구, 2인가구, 3인가구, 4인 이상 |

### 11.3 매칭 로직

- Subsidy 모델의 `age_min`/`age_max`, `region`, `income_percentile`로 조건 매칭 필터링
- **정확한 금액 계산이 아닌 매칭 + 원본 금액 표시**
- 월소득 → 소득분위 변환은 `mappings/income_thresholds.json` 참조

**`mappings/income_thresholds.json`:**
```json
{
  "year": 2026,
  "median_income_monthly": {
    "1": 2392196,
    "2": 3932658,
    "3": 5025353,
    "4": 6097773
  },
  "percentile_brackets": [50, 75, 100, 120, 150, 200],
  "note": "기준중위소득(원/월). percentile_brackets는 중위소득 대비 %로, 예: 50=중위소득 50% 이하"
}
```

변환 로직: `사용자 월소득 / 가구별 기준중위소득 × 100 = 소득분위(%)`. 이 값을 Subsidy의 `income_percentile`과 비교하여 매칭.

### 11.4 출력

- 매칭 보조금 리스트: 보조금명, 금액 텍스트, 마감일
- 각 항목 클릭 시 상세 페이지 내부 링크 (`/subsidies/{id}/{slug}`)
- **금액 합산 로직:**
  - 금액 텍스트에서 숫자 추출 가능한 것만 합산하여 "예상 총 수혜액" 표시
  - 숫자 추출 불가능한 건 "별도 확인" 표시
  - 예: "월 30만원" → 추출 가능 / "실비 지원" → "별도 확인"

### 11.5 공유 기능

- **결과 URL에 쿼리 파라미터 포함** (공유/SEO용)
  - 예: `/calculator?age=28&region=서울&income=250&household=1`
  - 쿼리 파라미터가 있으면 SSR 시점에 결과를 미리 렌더링
- **SNS 공유 버튼:**
  - 카카오톡: Kakao JavaScript SDK 연동 (공유 메시지 커스텀)
  - 트위터: Twitter Web Intent URL 기반

### 11.6 SEO

- title: "2026 보조금 매칭 계산기 - 내게 맞는 보조금 찾기"
- 결과 페이지에도 메타 태그 동적 생성 (쿼리 파라미터 기반)
- JSON-LD: `WebApplication` 스키마

---

## 12. 단계별 구현 범위

### 1단계: 기반 구축

| 항목 | 내용 |
|------|------|
| Jinja2 SSR 전환 | `base.html` + `index.html` 템플릿, CSS/JS 분리 |
| 공공 API 연동 | BaseAPIClient 멀티소스 구조, 보조금24 + 기업마당 + 정부24 |
| API 호출 전략 | 서버 시작 시 batch fetch, stale-while-error |
| 데이터 정제 | `data_cleaner.py` + JSON 매핑 파일 (`mappings/`) |
| TTL 캐싱 | 인메모리 TTL 캐시 + 5분 주기 자동 정리 |
| 기본 SEO | 메타 태그, robots.txt, sitemap.xml (동적) |
| 기본 성능 | Gzip 압축, 정적 파일 캐싱, 폰트 최적화 |
| 기존 기능 마이그레이션 | 필터 검색, 소득분위 가이드, 나이 계산기 (아래 참조) |

**기존 기능 마이그레이션 상세:**
- 필터 검색: `index.html` Jinja2 템플릿에서 폼 렌더링, `main.js`에서 fetch API로 `/api/subsidies` 호출 (기존 로직 유지)
- 소득분위 가이드: 기존 `static/index.html`의 인라인 테이블을 `index.html` 템플릿에 이식
- 나이 계산기 (생년월일↔만나이 토글): 기존 클라이언트 JS 로직을 `main.js`로 이동
- **상세 모달**: 1단계에서는 기존 모달(클릭 시 오버레이) 유지. 2단계에서 `/subsidies/{id}/{slug}` 상세 페이지로 대체 후 모달 제거.

### 2단계: 콘텐츠 페이지

| 항목 | 내용 |
|------|------|
| 보조금 상세 페이지 | `/subsidies/{id}/{slug}` (SEO URL) |
| JSON-LD 구조화 데이터 | `GovernmentService` + `FAQPage` 스키마 |
| 상세 페이지 내부 링크 | 같은 카테고리/지역/관련 보조금 링크 블록 |
| 보조금 매칭 계산기 | `/calculator` 페이지 (매칭 + 금액 합산 + SNS 공유) |

### 3단계: 롱테일 SEO

| 항목 | 내용 |
|------|------|
| 카테고리별 목록 | `/category/{category}` |
| 지역별 목록 | `/region/{region}` |
| Redis 캐시 전환 | 인메모리 → Redis (선택) |

### 4단계: 수익화

| 항목 | 내용 |
|------|------|
| 블로그/가이드 콘텐츠 | `/guide/{slug}` |
| 애드센스 적용 | `base.html` 애드센스 슬롯 활성화 |

### 후순위

| 항목 | 내용 |
|------|------|
| 재방문 유도 기능 | 즐겨찾기, 알림 등 |
| DB 전환 | 인메모리 → 별도 DB |
| 배포 환경 | 별도 결정 후 구성 |

---

## 13. 폴백 전략

- 공공 API 연동 완료 전: `data.py`의 12개 샘플 데이터 사용
- API 장애 시: stale-while-error로 만료된 캐시 데이터 제공
- 모든 API + 캐시 실패 시: `data.py` 폴백

---

## 14. 기술 의존성 (예상 requirements.txt 추가)

```
jinja2
aiohttp          # 비동기 HTTP 클라이언트 (공공 API 호출)
python-dotenv    # 환경변수 관리
```
