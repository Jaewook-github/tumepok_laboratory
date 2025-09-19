# 순위정보 TR 문서 요약

## 개요
순위정보 TR은 키움증권 REST API를 통해 다양한 기준으로 주식 순위 정보를 조회하는 기능을 제공합니다. 등락률, 거래량, 호가 잔량, 거래원 정보 등 시장 전체의 순위 데이터를 실시간으로 확인하여 투자 기회를 발굴할 수 있습니다.

## 공통 사항

### API 설정
- **엔드포인트**: `/api/dostk/rkinfo`
- **메서드**: POST
- **인증**: Bearer 토큰 필요
- **서버**:
  - 실전: `https://api.kiwoom.com`
  - 모의: `https://mockapi.kiwoom.com`

### 공통 필터 조건
- **시장구분**: 000(전체), 001(코스피), 101(코스닥)
- **거래소구분**: 1(KRX), 2(NXT), 3(통합)
- **종목조건**: 관리종목/우선주/증거금 제외 옵션
- **가격조건**: 1천원~10만원 등 가격대별 필터
- **거래량조건**: 5천주~100만주 이상 필터
- **거래대금조건**: 3천만원~500억원 이상 필터

## 주요 기능 분류

### 1. 등락률 및 가격 순위

#### KA10027 - 전일대비등락률상위요청
**목적**: 등락률 기준 상위 종목 발굴

**정렬 옵션**:
- 1: 상승률
- 2: 상승폭
- 3: 하락률
- 4: 하락폭

**응답 데이터**:
- 종목코드/명, 현재가, 전일대비
- 등락률, 매도/매수 잔량
- 현재거래량, 체결강도

**활용**: 급등/급락주 발굴, 일일 시장 동향 파악

#### KA10029 - 예상체결등락률상위요청
**목적**: 장전 예상체결가 기준 등락률 순위

**활용**: 장 시작 전 관심종목 선별, 갭상승/갭하락 예상

### 2. 거래량 관련 순위

#### KA10030 - 당일거래량상위요청
**목적**: 거래량/거래회전율/거래대금 기준 순위

**정렬 옵션**:
- 1: 거래량
- 2: 거래회전율
- 3: 거래대금

**세부 정보**:
- 장중/장전/장후 거래량 분리
- 전일대비 거래량 비율
- 거래회전율

**활용**: 거래 활발한 종목 발굴, 유동성 분석

#### KA10031 - 전일거래량상위요청
**목적**: 전일 거래량 기준 상위 종목

**활용**: 전일 관심도 높았던 종목 확인

#### KA10023 - 거래량급증요청
**목적**: 거래량 급증 종목 실시간 포착

**시간구분**:
- 1: 분 단위 급증
- 2: 전일 대비 급증

**정렬 옵션**:
- 1: 급증량
- 2: 급증률

**응답 데이터**:
- 이전거래량 vs 현재거래량
- 급증량, 급증률

**활용**: 돌발 이슈나 호재 발생 종목 포착

### 3. 호가 및 잔량 분석

#### KA10020 - 호가잔량상위요청
**목적**: 매수/매도 호가 잔량 상위 종목

**활용**: 대량 주문 대기 종목 파악, 수급 불균형 분석

#### KA10021 - 호가잔량급증요청
**목적**: 호가 잔량 급증 종목

**활용**: 급작스런 매수/매도 압력 감지

#### KA10022 - 잔량율급증요청
**목적**: 잔량율(잔량/거래량) 급증 종목

**활용**: 호가 대기량 증가 추세 파악

### 4. 거래원 및 수급 분석

#### ka10040 - 당일주요거래원요청
**목적**: 특정 종목의 주요 거래원 정보

**응답 데이터**:
- 매수/매도 거래원 상위 5개사
- 거래원별 수량 및 증감
- 거래원 코드

**활용**: 세력 분석, 기관/외국인 동향 파악

#### ka10038 - 종목별증권사순위요청
**목적**: 종목별 증권사 거래 순위

**활용**: 거래 주도 증권사 파악

#### ka10039 - 증권사별매매상위요청
**목적**: 증권사별 매매 상위 종목

**활용**: 특정 증권사의 관심 종목 파악

#### ka10042 - 순매수거래원순위요청
**목적**: 순매수 거래원 순위

**활용**: 매수세 강한 거래원 및 종목 파악

### 5. 기관/외국인 수급

#### ka90009 - 외국인기관매매상위요청
**목적**: 외국인/기관 순매수/순매도 상위 종목

**응답 데이터**:
- 외국인 순매수/순매도 상위
- 기관 순매수/순매도 상위
- 금액/수량 구분 가능

**활용**: 스마트머니 동향 추적

#### KA10034 - 외인기간별매매상위요청
**목적**: 외국인 기간별 매매 상위 종목

**활용**: 외국인 중장기 관심 종목 파악

#### KA10035 - 외인연속순매매상위요청
**목적**: 외국인 연속 순매매 상위 종목

**활용**: 외국인 지속적 관심 종목

#### ka10036 - 외인한도소진율증가상위
**목적**: 외국인 한도소진율 증가 상위

**활용**: 외국인 한도 임박 종목, 향후 매수 제약 예상

#### ka10037 - 외국계창구매매상위요청
**목적**: 외국계 증권사 창구 매매 상위

**활용**: 외국계 자금 동향 파악

### 6. 기타 특수 순위

#### KA10032 - 거래대금상위요청
**목적**: 거래대금 기준 상위 종목

**활용**: 자금 집중도 분석

#### KA10033 - 신용비율상위요청
**목적**: 신용거래 비율 상위 종목

**활용**: 신용 레버리지 높은 종목, 변동성 예상

#### ka10065 - 장중투자자별매매상위요청
**목적**: 장중 투자자별 매매 상위

**활용**: 실시간 투자자별 수급 파악

#### ka10062 - 동일순매매순위요청
**목적**: 동일 순매매 패턴 순위

**활용**: 수급 패턴 분석

#### ka10069 - 프로그램거래량상위10종목요청
**목적**: 프로그램 거래량 상위 종목

**활용**: 기관 프로그램 매매 동향

#### ka10098 - 시간외단일가등락율순위요청
**목정**: 시간외 단일가 등락률 순위

**활용**: 시간외 거래 동향, 다음날 갭 예상

#### KA10053 - 당일상위이탈원요청
**목적**: 상위권에서 이탈한 종목

**활용**: 관심도 하락 종목 파악

## 시스템 활용 가이드

### 1. 급등주 실시간 포착
```python
def find_surge_stocks():
    """급등주 실시간 포착"""
    
    # KA10027: 등락률 상위 (상승률 기준)
    surge_params = {
        'mrkt_tp': '000',  # 전체 시장
        'sort_tp': '1',    # 상승률
        'trde_qty_cnd': '0100',  # 10만주 이상
        'trde_prica_cnd': '50',  # 5억원 이상
        'pric_cnd': '8',   # 1천원 이상
        'stk_cnd': '1'     # 관리종목 제외
    }
    
    surge_stocks = get_price_surge_ranking(surge_params)
    
    # 20% 이상 급등 + 거래량 충분한 종목 필터링
    candidates = []
    for stock in surge_stocks['pred_pre_flu_rt_upper']:
        if (float(stock['flu_rt']) >= 20.0 and 
            int(stock['now_trde_qty']) >= 100000):
            candidates.append(stock)
    
    return candidates
```

### 2. 거래량 급증 모니터링
```python
def monitor_volume_surge():
    """거래량 급증 종목 모니터링"""
    
    # KA10023: 거래량 급증 (전일 대비)
    volume_params = {
        'mrkt_tp': '000',
        'sort_tp': '2',    # 급증률
        'tm_tp': '2',      # 전일 대비
        'trde_qty_tp': '50'  # 5만주 이상
    }
    
    volume_surge = get_volume_surge(volume_params)
    
    # 급증률 300% 이상 종목
    strong_surge = []
    for stock in volume_surge['trde_qty_sdnin']:
        if float(stock['sdnin_rt']) >= 300.0:
            strong_surge.append({
                'code': stock['stk_cd'],
                'name': stock['stk_nm'],
                'surge_rate': stock['sdnin_rt'],
                'current_volume': stock['now_trde_qty']
            })
    
    return strong_surge
```

### 3. 수급 기반 종목 선별
```python
def select_by_supply_demand():
    """수급 기반 종목 선별"""
    
    # ka90009: 외국인/기관 매매 상위
    supply_params = {
        'mrkt_tp': '001',  # 코스피
        'amt_qty_tp': '1', # 금액 기준
        'qry_dt_tp': '1'   # 당일 포함
    }
    
    supply_data = get_foreign_institutional_ranking(supply_params)
    
    # 외국인+기관 동반 매수 종목 찾기
    buy_stocks = []
    
    foreign_buy = [s['for_netprps_stk_cd'] 
                   for s in supply_data['frgnr_orgn_trde_upper']]
    institutional_buy = [s['orgn_netprps_stk_cd'] 
                        for s in supply_data['frgnr_orgn_trde_upper']]
    
    # 교집합 (동반 매수 종목)
    common_buy = set(foreign_buy) & set(institutional_buy)
    
    return list(common_buy)
```

### 4. 세력 분석
```python
def analyze_major_traders(stock_code):
    """주요 거래원 분석"""
    
    # ka10040: 당일 주요 거래원
    trader_data = get_major_traders(stock_code)
    
    analysis = {
        'buy_power': 0,
        'sell_power': 0,
        'major_buyers': [],
        'major_sellers': []
    }
    
    # 매수/매도 거래원 분석
    for i in range(1, 6):
        buy_trader = trader_data.get(f'buy_trde_ori_{i}')
        buy_qty = trader_data.get(f'buy_trde_ori_qty_{i}', '0')
        
        sell_trader = trader_data.get(f'sel_trde_ori_{i}')
        sell_qty = trader_data.get(f'sel_trde_ori_qty_{i}', '0')
        
        if buy_trader:
            analysis['major_buyers'].append({
                'name': buy_trader,
                'quantity': int(buy_qty)
            })
            analysis['buy_power'] += int(buy_qty)
        
        if sell_trader:
            analysis['major_sellers'].append({
                'name': sell_trader,
                'quantity': int(sell_qty)
            })
            analysis['sell_power'] += int(sell_qty)
    
    # 매수/매도 세력 비교
    analysis['net_power'] = analysis['buy_power'] - analysis['sell_power']
    
    return analysis
```

### 5. 전략 통합
```python
class TumepokRankingStrategy:
    def __init__(self):
        self.ranking_filters = {
            'min_price_change': 20.0,  # 최소 20% 상승
            'min_volume': 100000,      # 최소 10만주 거래
            'min_amount': 5000000000   # 최소 50억원 거래대금
        }
    
    def find_tumepok_candidates(self):
        """전략 후보 종목 발굴"""
        
        # 1단계: 급등주 스크리닝
        surge_stocks = self.get_surge_stocks()
        
        # 2단계: 거래량 급증 확인
        volume_surge = self.get_volume_surge_stocks()
        
        # 3단계: 수급 지원 확인
        supply_support = self.get_supply_support_stocks()
        
        # 교집합으로 최종 후보 선별
        candidates = set(surge_stocks) & set(volume_surge) & set(supply_support)
        
        # 4단계: 세력 분석
        final_candidates = []
        for stock_code in candidates:
            trader_analysis = analyze_major_traders(stock_code)
            if trader_analysis['net_power'] > 0:  # 매수세 우세
                final_candidates.append(stock_code)
        
        return final_candidates
    
    def monitor_exit_signals(self, holdings):
        """보유 종목 매도 신호 모니터링"""
        
        exit_signals = []
        
        for position in holdings:
            stock_code = position['stock_code']
            
            # 하락률 순위 확인
            decline_rank = self.check_decline_ranking(stock_code)
            
            # 거래량 감소 확인
            volume_decline = self.check_volume_decline(stock_code)
            
            # 수급 악화 확인
            supply_deterioration = self.check_supply_deterioration(stock_code)
            
            if decline_rank or volume_decline or supply_deterioration:
                exit_signals.append({
                    'stock_code': stock_code,
                    'signals': [decline_rank, volume_decline, supply_deterioration]
                })
        
        return exit_signals
```

## 실전 활용 시나리오

### 1. 장 시작 전 후보군 선별
```python
# 1. 예상체결 급등주 (KA10029)
pre_market_surge = get_pre_market_surge()

# 2. 전일 거래량 상위 + 당일 급등 조합
yesterday_volume = get_yesterday_volume_leaders()
today_surge = get_today_surge()

candidates = combine_criteria([pre_market_surge, yesterday_volume, today_surge])
```

### 2. 장중 실시간 모니터링
```python
# 실시간 급등 + 거래량 급증 종목
real_time_candidates = []

while market_open:
    # 5분마다 업데이트
    new_surge = get_price_surge()  # KA10027
    new_volume = get_volume_surge()  # KA10023
    
    combined = intersect(new_surge, new_volume)
    real_time_candidates.extend(combined)
    
    time.sleep(300)  # 5분 대기
```

### 3. 매도 타이밍 판단
```python
def check_exit_conditions(position):
    """매도 조건 확인"""
    
    stock_code = position['stock_code']
    
    # 1. 하락률 상위 진입 확인
    decline_check = check_decline_ranking(stock_code)
    
    # 2. 거래원 매도 증가 확인
    trader_sell = check_major_seller_increase(stock_code)
    
    # 3. 외국인/기관 매도 전환 확인
    institutional_sell = check_institutional_selling(stock_code)
    
    exit_score = sum([decline_check, trader_sell, institutional_sell])
    
    if exit_score >= 2:
        return "STRONG_SELL"
    elif exit_score == 1:
        return "WEAK_SELL"
    else:
        return "HOLD"
```

## 주의사항

### 데이터 해석
- 순위 데이터는 실시간이지만 지연 가능
- 거래량/거래대금은 누적 기준
- 호가 잔량은 순간적 변동 가능

### 필터링 최적화
- 너무 엄격한 조건은 기회 상실
- 시장 상황에 따른 조건 조정 필요
- 백테스팅으로 최적 파라미터 도출

### API 효율성
- 불필요한 연속조회 지양
- 관심 종목 중심으로 선별 조회
- 캐싱으로 중복 호출 방지

## 결론
순위정보 TR은 전략의 핵심 도구로, 시장 전체에서 급등주를 발굴하고 수급 상황을 파악하는 데 필수적입니다. 다양한 순위 정보를 조합하여 고품질의 투자 후보를 선별하고, 실시간 모니터링으로 최적의 매매 타이밍을 포착할 수 있습니다.