# OAuth TR 문서 요약

## 개요
OAuth TR은 키움증권 REST API 사용을 위한 인증 토큰 관리 기능을 제공합니다. OAuth 2.0 표준을 기반으로 안전한 API 접근 권한을 관리하며, 모든 API 호출에 필수적인 접근토큰(Access Token)의 발급과 폐기를 처리합니다.

## 주요 기능

### 1. AU10001 - 접근토큰 발급
**목적**: Kiwoom API 사용을 위한 접근토큰 획득

**엔드포인트**: `/oauth2/token`

**필수 파라미터**:
- `grant_type`: "client_credentials" (고정값)
- `appkey`: 개발자센터에서 발급받은 앱키
- `secretkey`: 개발자센터에서 발급받은 시크릿키

**응답 데이터**:
- `token`: API 호출 시 사용할 접근토큰
- `token_type`: "Bearer" (토큰 타입)
- `expires_dt`: 토큰 만료일시

**활용**:
```python
# 토큰 발급 후 API 호출 시 헤더에 포함
headers = {
    'authorization': f'Bearer {token}',
    'Content-Type': 'application/json;charset=UTF-8'
}
```

### 2. AU10002 - 접근토큰 폐기
**목적**: 발급받은 접근토큰 무효화 (보안 목적)

**엔드포인트**: `/oauth2/revoke`

**필수 파라미터**:
- `appkey`: 개발자센터에서 발급받은 앱키
- `secretkey`: 개발자센터에서 발급받은 시크릿키
- `token`: 폐기할 접근토큰

**응답**: HTTP 상태 코드로 성공/실패 판단
- 200: 성공
- 400: 잘못된 요청
- 401: 인증 실패

## OAuth 2.0 인증 프로세스

### 1. 초기 설정
```
1. Kiwoom 개발자센터 접속
2. 애플리케이션 등록
3. 앱키(AppKey) 및 시크릿키(SecretKey) 발급
4. 실전/모의투자 환경 선택
```

### 2. 토큰 발급 플로우
```
Client                     Kiwoom API Server
  |                              |
  |--[1] 토큰 요청 (앱키/시크릿키)-->|
  |                              |
  |<--[2] 접근토큰 응답-----------|
  |                              |
  |--[3] API 호출 (Bearer 토큰)-->|
  |                              |
  |<--[4] API 응답 데이터---------|
```

### 3. 토큰 생명주기 관리
```python
# 1. 프로그램 시작 시 토큰 발급
token = get_access_token(appkey, secretkey)

# 2. API 호출 시 토큰 사용
response = call_api(token, api_params)

# 3. 프로그램 종료 시 토큰 폐기 (선택사항)
revoke_token(appkey, secretkey, token)
```

## 중요 사항

### 토큰 유효기간
- **유효기간**: 24시간
- **자동 만료**: 발급 후 24시간 경과 시 자동 무효화
- **재발급 필요**: 매일 새로운 토큰 발급 필요
- **권장사항**: 프로그램 시작 시 토큰 발급, 종료 시 폐기

### 보안 주의사항
1. **앱키/시크릿키 보호**:
   - 소스코드에 직접 입력 금지
   - 환경변수 또는 설정 파일 활용
   - Git 등 버전관리 시스템에 포함 금지

2. **토큰 관리**:
   - 토큰을 로컬 파일에 저장 시 암호화
   - 메모리에만 보관 권장
   - 사용 완료 후 명시적 폐기

3. **환경 분리**:
   - 실전/모의투자 환경별 토큰 분리
   - 테스트는 모의투자 환경에서 수행

### API 호출 제한
- **Rate Limiting**: API별 호출 제한 존재
- **동시 접속**: 동일 계정 동시 접속 제한
- **토큰 재사용**: 24시간 내 동일 토큰 재사용 가능

## 시스템 통합 가이드

### 1. 토큰 관리 모듈 구현
```python
class TokenManager:
    def __init__(self, appkey, secretkey):
        self.appkey = appkey
        self.secretkey = secretkey
        self.token = None
        self.expires_dt = None
    
    def get_token(self):
        """토큰 발급 또는 기존 토큰 반환"""
        if self.is_token_valid():
            return self.token
        return self.refresh_token()
    
    def refresh_token(self):
        """새 토큰 발급"""
        # AU10001 호출
        pass
    
    def revoke_token(self):
        """토큰 폐기"""
        # AU10002 호출
        pass
    
    def is_token_valid(self):
        """토큰 유효성 검증"""
        # 만료시간 체크
        pass
```

### 2. 자동 토큰 갱신
```python
import schedule
import time

def refresh_token_daily():
    """매일 자정에 토큰 갱신"""
    token_manager.refresh_token()

# 매일 00:01에 토큰 갱신
schedule.every().day.at("00:01").do(refresh_token_daily)

# 프로그램 시작 시 초기 토큰 발급
token_manager.refresh_token()
```

### 3. API 호출 래퍼
```python
def api_call_with_retry(api_func, params, max_retries=3):
    """토큰 만료 시 자동 재발급 후 재시도"""
    for attempt in range(max_retries):
        try:
            token = token_manager.get_token()
            return api_func(token, params)
        except TokenExpiredError:
            token_manager.refresh_token()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)
```

### 4. 환경별 설정
```python
# config.py
import os

class Config:
    # 환경변수에서 읽기
    APPKEY = os.environ.get('KIWOOM_APPKEY')
    SECRETKEY = os.environ.get('KIWOOM_SECRETKEY')
    
    # 실전/모의 환경 선택
    IS_PRODUCTION = os.environ.get('ENV', 'dev') == 'prod'
    API_HOST = 'https://api.kiwoom.com' if IS_PRODUCTION else 'https://mockapi.kiwoom.com'
```

## 트러블슈팅

### 자주 발생하는 오류

1. **401 Unauthorized**:
   - 원인: 토큰 만료, 잘못된 앱키/시크릿키
   - 해결: 토큰 재발급, 인증정보 확인

2. **400 Bad Request**:
   - 원인: 필수 파라미터 누락
   - 해결: grant_type, appkey, secretkey 확인

3. **토큰 발급 실패**:
   - 원인: 네트워크 오류, 서버 점검
   - 해결: 재시도 로직 구현, 점검시간 확인

### 디버깅 팁
1. 토큰 만료시간 로깅
2. API 호출 전 토큰 유효성 사전 체크
3. 토큰 갱신 이벤트 모니터링
4. 실전/모의 환경 명확히 구분

## 모범 사례

### 1. 싱글톤 패턴 활용
```python
class TokenSingleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### 2. 토큰 캐싱
- 메모리 캐시 활용
- Redis 등 외부 캐시 고려
- 토큰 공유 시 동시성 제어

### 3. 에러 핸들링
- 토큰 관련 예외 클래스 정의
- 재시도 로직 구현
- 로깅 및 알림 설정

### 4. 성능 최적화
- 토큰 발급 횟수 최소화
- 불필요한 토큰 폐기 호출 제거
- 비동기 처리 고려

## 결론
OAuth TR은 키움증권 REST API 사용의 첫 단계이자 가장 중요한 인증 과정입니다. 안전한 토큰 관리와 적절한 생명주기 관리를 통해 안정적인 API 서비스 이용이 가능합니다. 시스템 구현 시 토큰 관리 모듈을 별도로 구성하여 모든 API 호출에서 일관된 인증 처리를 보장해야 합니다.