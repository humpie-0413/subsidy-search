아래 내용을 설계에 반영한 뒤 설계 문서를 작성해줘:

1. 데이터 소스 확장:
   - 1순위: 보조금24 API (~1,075건)
   - 2순위: 기업마당 API bizinfo.go.kr (~1,000건+, 지자체 포함)
   - 3순위: 정부24 API (보완용)
   - api_client.py를 BaseAPIClient 추상 클래스 기반 멀티소스 구조로 설계

2. API 호출 전략:
   - 사용자 요청 시 API 직접 호출 안 함
   - 서버 시작 시 + 캐시 만료 시에만 batch fetch
   - stale-while-error 패턴 적용

3. SEO 보강:
   - title에 연도 삽입
   - FAQPage 스키마 추가
   - 상세 페이지 내부 링크 블록
   - slug + ID 조합 URL (/subsidies/123/청년-월세-지원)

4. 캐시 clear_expired() 5분 주기 자동 실행

5. 2단계에 "보조금 매칭 계산기" 추가:
   - /calculator 페이지 (Jinja2 SSR)
   - 입력: 나이, 지역, 월소득, 가구 형태
   - 로직: Subsidy 모델의 age_min/max, region, income_percentile로 조건 매칭 필터링 (정확한 금액 계산이 아닌 매칭 + 원본 금액 표시)
   - 출력: 매칭 보조금 리스트 + 금액 텍스트 + 마감일
   - 각 항목 클릭 시 상세 페이지 내부 링크
   - 금액 텍스트에서 숫자 추출 가능한 것만 합산, 불가능한 건 "별도 확인" 표시
   - 결과 URL에 쿼리 파라미터 포함 (공유/SEO용)
   - SNS 공유 버튼 (카카오톡, 트위터)

설계 문서 작성 후 구현 계획으로 넘어가줘.
