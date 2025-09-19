# 종목정보_TR API 요약

## 개요
키움증권 REST API의 종목정보 관련 TR(Transaction Request) 코드들로, 개별 종목의 기본 정보부터 고급 분석 데이터까지 광범위한 종목 정보를 제공합니다. 전략 자동매매 시스템에서 종목 발굴, 분석, 모니터링에 필수적인 API 그룹입니다.

## 주요 API 카테고리

### 1. 기본 종목 정보 조회
- **ka10001 - 주식기본정보요청**: 종목의 모든 기본 정보 (PER, PBR, ROE, 시가총액, 재무정보 등)
- **ka10100 - 종목정보 조회**: 특정 종목의 간략 정보 조회
- **ka10099 - 종목정보 리스트**: 시장별 전체 종목 리스트 조회

### 2. 체결 및 거래 정보
- **ka10003 - 체결정보요청**: 실시간 체결 내역과 호가 정보
- **ka10002 - 주식거래원요청**: 종목별 거래원 현황
- **ka10015 - 일별거래상세요청**: 일별 상세 거래 내역

### 3. 시장 이벤트 및 급등락 분석
- **ka10019 - 가격급등락요청**: 급등/급락 종목 발굴 (전략 핵심 API)
- **ka10020 - 거래량갱신요청**: 거래량 급증 종목 모니터링
- **ka10026 - 변동성완화장치발동종목요청**: VI 발동 종목 추적

### 4. 투자자별 매매 동향
- **ka10028 - 투자자별일별매매종목요청**: 기관/외국인/개인 매매 현황
- **ka10029/30 - 종목별투자자기관별요청**: 투자자별 상세 거래 내역

### 5. 고급 분석 정보
- **ka10016 - 신고저가요청**: 52주 신고가/신저가 종목
- **ka10017 - 상하한가요청**: 상하한가 근접 종목
- **ka10018 - 고저가근접요청**: 고가/저가 근접 종목
- **ka10021 - 매물대집중요청**: 매물대 분석
- **ka10022 - 고저PER요청**: PER 고저 분석

### 6. 신용 및 대차 거래
- **ka10013 - 신용매매동향요청**: 신용 거래 현황
- **ka10035 - 대차거래내역요청**: 공매도 관련 대차 거래 내역

## 전략 시스템 통합 전략

### 1. 급등 종목 발굴 시스템
```python
class TumepokStockDiscovery:
    def discover_surge_stocks(self):
        """20% 이상 급등 종목 발굴"""
        # ka10019: 가격급등락요청 활용
        surge_params = {
            'flu_tp': '1',  # 급등
            'tm_tp': '1',   # 분전
            'tm': '60',     # 60분전 대비
            'flu_rt_min': '20'  # 20% 이상
        }
        
        # ka10020: 거래량갱신요청으로 거래량 확인
        volume_params = {
            'cycle_tp': '5',     # 5일 평균 대비
            'trde_qty_tp': '50'  # 5만주 이상
        }
        
        return self.filter_tumepok_candidates(surge_stocks, volume_data)
    
    def filter_tumepok_candidates(self, stocks, volume_data):
        """전략 조건에 맞는 종목 필터링"""
        candidates = []
        for stock in stocks:
            # 기본 조건: 20% 이상 상승, 거래량 급증
            if stock['flu_rt'] >= 20 and stock['volume_ratio'] >= 2.0:
                candidates.append(stock)
        return candidates
```

### 2. 종목 상세 분석 시스템
```python
class StockAnalyzer:
    def analyze_stock_details(self, stock_code):
        """종목 상세 분석"""
        # ka10001: 기본 정보 수집
        basic_info = self.get_basic_info(stock_code)
        
        # ka10003: 실시간 체결 정보
        tick_data = self.get_tick_data(stock_code)
        
        # ka10028: 투자자별 매매 동향
        investor_trend = self.get_investor_trend(stock_code)
        
        return {
            'market_cap': basic_info['mac'],
            'per': basic_info['per'],
            'volume_trend': tick_data['volume_strength'],
            'foreign_buy': investor_trend['foreign_net_buy'],
            'tumepok_score': self.calculate_tumepok_score(basic_info, tick_data)
        }
    
    def calculate_tumepok_score(self, basic, tick):
        """전략 적합도 점수 계산"""
        score = 0
        
        # 시가총액 조건 (5000억 미만 선호)
        if float(basic['mac']) < 500000000000:
            score += 20
            
        # PER 조건 (적정 밸류에이션)
        if 5 <= float(basic['per']) <= 20:
            score += 15
            
        # 거래량 강도
        if float(tick['cntr_str']) > 150:
            score += 25
            
        return score
```

### 3. 실시간 모니터링 시스템
```python
class RealTimeMonitor:
    def monitor_tracking_stocks(self):
        """추적 중인 종목 실시간 모니터링"""
        for stock_code in self.tracking_list:
            # ka10003: 실시간 체결 정보
            current_data = self.get_current_price(stock_code)
            
            # 하락률 계산
            drop_rate = self.calculate_drop_rate(stock_code, current_data)
            
            # 전략 매트릭스 확인
            if self.check_tumepok_entry_condition(stock_code, drop_rate):
                self.prepare_buy_signal(stock_code, drop_rate)
    
    def check_tumepok_entry_condition(self, stock_code, drop_rate):
        """전략 진입 조건 확인"""
        # 연속 상승일 확인
        rise_days = self.get_consecutive_rise_days(stock_code)
        
        # 적정 하락폭 계산
        required_drop = self.get_required_drop_rate(rise_days)
        
        return drop_rate >= required_drop['min'] and drop_rate <= required_drop['max']
```

### 4. 위험 관리 시스템
```python
class RiskManager:
    def assess_stock_risk(self, stock_code):
        """종목별 위험도 평가"""
        # ka10017: 상하한가 근접도 확인
        limit_proximity = self.get_limit_proximity(stock_code)
        
        # ka10026: VI 발동 이력 확인
        vi_history = self.get_vi_history(stock_code)
        
        # ka10035: 대차거래 비율 확인 (공매도 압력)
        short_pressure = self.get_short_pressure(stock_code)
        
        risk_score = self.calculate_risk_score(limit_proximity, vi_history, short_pressure)
        
        return {
            'risk_level': 'HIGH' if risk_score > 70 else 'MEDIUM' if risk_score > 40 else 'LOW',
            'position_ratio': self.get_position_ratio(risk_score),
            'stop_loss_rate': self.get_stop_loss_rate(risk_score)
        }
```

## 전략 특화 활용 시나리오

### 1. 급등 종목 스크리닝 파이프라인
1. **ka10019**: 60분간 20% 이상 급등 종목 1차 스크리닝
2. **ka10001**: 기본 정보로 시가총액, PER 등 기본 조건 확인
3. **ka10020**: 거래량 급증 확인 (평균 대비 2배 이상)
4. **ka10028**: 외국인/기관 매수 여부 확인
5. **전략 후보 리스트 생성**

### 2. 실시간 하락 모니터링
1. **ka10003**: 실시간 체결가 모니터링
2. **하락률 계산**: 최고가 대비 현재 하락률
3. **전략 매트릭스 대조**: 상승률별 적정 하락률 확인
4. **지지 조건 분석**: RSI, 지지선, 거래량 건조 확인
5. **매수 신호 생성**

### 3. 포지션 관리 및 청산
1. **수익률 추적**: 매수가 대비 현재 수익률
2. **트레일링 스톱**: +2% 도달 시 트레일링 스톱 활성화
3. **손절 관리**: -2% 도달 시 즉시 손절
4. **ka10028**: 투자자별 매매 동향으로 청산 타이밍 판단

## API 사용 시 주의사항

### 1. 데이터 신뢰성
- PER, ROE 등 재무 데이터는 주간 단위 업데이트
- 실시간 체결 데이터 우선 활용
- 연속 조회 시 next-key 관리 필수

### 2. 요청 제한
- 분당 요청 횟수 제한 준수
- 종목별 순차 요청으로 부하 분산
- 에러 발생 시 재시도 로직 구현

### 3. 데이터 검증
- 상한가/하한가 종목 필터링
- VI 발동 종목 거래 제한 확인
- 거래 정지 종목 사전 제외

## 성능 최적화 전략

### 1. 효율적 데이터 수집
```python
# 우선순위별 API 호출
priority_apis = [
    'ka10019',  # 급등락 (최우선)
    'ka10003',  # 체결정보 (실시간)
    'ka10001',  # 기본정보 (캐싱 가능)
    'ka10028'   # 투자자동향 (일 1회)
]
```

### 2. 캐싱 전략
- 기본 정보: 일별 캐싱
- 실시간 데이터: 캐싱 없음
- 투자자 동향: 시간별 캐싱

### 3. 병렬 처리
- 다중 종목 동시 조회
- 비동기 API 호출
- 큐 기반 요청 관리

## 결론
종목정보_TR API 그룹은 전략 전략의 핵심 인프라로, 급등 종목 발굴부터 실시간 모니터링, 위험 관리까지 전 과정을 지원합니다. 특히 ka10019(급등락), ka10003(체결정보), ka10028(투자자동향) API를 중심으로 한 통합 시스템 구축이 전략 전략 성공의 핵심입니다.