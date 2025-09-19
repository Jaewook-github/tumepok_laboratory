# 시세_TR API 요약

## 개요

시세_TR 폴더는 키움증권 REST API의 시세 정보 조회 API들을 포함합니다. 이 API들은 실시간 및 과거 주식 시세, 호가, 체결 정보, 그리고 기관/외국인 매매 동향 등을 제공하여 자동매매 시스템의 핵심 데이터 소스 역할을 합니다.

## 주요 API 분류

### 1. 기본 시세 정보 (핵심 API)

#### ka10004 - 주식호가요청
- **목적**: 실시간 매수/매도 호가 및 잔량 정보 조회
- **엔드포인트**: `/api/dostk/mrkcond`
- **전략 활용**: 호가 불균형 분석, 진입/청산 타이밍 결정
- **주요 데이터**:
  - 매수/매도 호가 10단계 (최우선~10차선)
  - 각 호가별 잔량 및 직전 대비 변화량
  - 총 매수/매도 잔량 및 시간외 잔량

```python
def analyze_bid_ask_imbalance(stock_code):
    """호가 불균형 분석"""
    bid_data = get_stock_bid(stock_code)
    
    total_buy = int(bid_data['tot_buy_req'])
    total_sell = int(bid_data['tot_sel_req'])
    
    imbalance_ratio = (total_buy - total_sell) / (total_buy + total_sell)
    
    # 매수 우세 시 진입 시그널
    if imbalance_ratio > 0.3:
        return "BUY_SIGNAL"
    elif imbalance_ratio < -0.3:
        return "SELL_SIGNAL"
    else:
        return "NEUTRAL"
```

#### ka10005 - 주식일주월시분요청
- **목적**: 일/주/월 단위 OHLC 데이터 및 수급 정보
- **전략 활용**: 연속 상승일 계산, 추세 분석
- **주요 데이터**:
  - OHLC (시가/고가/저가/종가)
  - 등락률, 거래량/대금
  - 외인/기관/개인 순매수
  - 신용잔고율, 프로그램 매매량

```python
def calculate_consecutive_rise_days(stock_code):
    """연속 상승일 계산 (핵심 지표)"""
    price_data = get_stock_ohlc(stock_code)
    
    consecutive_days = 0
    for i, day_data in enumerate(price_data['stk_ddwkmm']):
        if float(day_data['flu_rt']) > 0:
            consecutive_days += 1
        else:
            break
    
    return consecutive_days
```

#### ka10086 - 일별주가요청
- **목적**: 특정 일자 기준 상세 주가 및 투자자별 매매 정보
- **전략 활용**: 일별 세부 분석, 백테스팅 데이터
- **주요 파라미터**:
  - `qry_dt`: 조회 일자 (YYYYMMDD)
  - `indc_tp`: 표시 구분 (0:수량, 1:금액)

### 2. 체결 강도 및 매매 압력 분석

#### ka10046 - 체결강도추이시간별요청
- **목적**: 시간별 체결 강도 변화 추이 분석
- **전략 활용**: 매매 압력 변화 감지, 모멘텀 분석
- **주요 데이터**:
  - 체결강도 (실시간/5분/20분/60분)
  - 시간별 현재가, 등락률
  - 누적 거래량/대금

```python
def monitor_execution_strength(stock_code):
    """체결강도 모니터링 (전략 진입 신호)"""
    strength_data = get_execution_strength(stock_code)
    
    signals = []
    for data in strength_data['cntr_str_tm']:
        strength_5min = float(data['cntr_str_5min'])
        strength_20min = float(data['cntr_str_20min'])
        
        # 체결강도 급상승 시 매수 신호
        if strength_5min > 200 and strength_20min > 150:
            signals.append({
                'time': data['cntr_tm'],
                'signal': 'STRONG_BUY',
                'strength': strength_5min
            })
    
    return signals
```

#### ka10047 - 체결강도추이일별요청
- **목적**: 일별 체결강도 추이 분석
- **전략 활용**: 장기 모멘텀 평가

### 3. 기관/외국인 매매 동향 분석

#### ka10044 - 일별기관매매종목요청
- **목적**: 기간별 기관 순매수/순매도 상위 종목
- **전략 활용**: 기관 수급 지원 확인
- **주요 파라미터**:
  - `strt_dt` / `end_dt`: 기간 설정
  - `trde_tp`: 1(순매도), 2(순매수)
  - `mrkt_tp`: 시장 구분

```python
def check_institutional_support(stock_code, days=5):
    """기관 수급 지원 확인"""
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    # 기관 순매수 조회
    buy_data = get_institutional_trading(start_date, end_date, trde_tp='2')
    
    for stock in buy_data['daly_orgn_trde_stk']:
        if stock['stk_cd'] == stock_code:
            return {
                'net_buy_amount': int(stock['netprps_amt']),
                'net_buy_quantity': int(stock['netprps_qty']),
                'support_level': 'STRONG' if int(stock['netprps_amt']) > 1000000000 else 'WEAK'
            }
    
    return {'support_level': 'NONE'}
```

#### ka10045 - 종목별기관매매추이요청
- **목적**: 특정 종목의 기관 매매 추이
- **전략 활용**: 개별 종목 기관 동향 분석

#### ka10063 - 장중투자자별매매요청
- **목적**: 장중 실시간 투자자별 매매 동향
- **전략 활용**: 실시간 수급 변화 모니터링

#### ka10066 - 장마감후투자자별매매요청
- **목적**: 장마감 후 투자자별 매매 동향
- **전략 활용**: 장마감 후 수급 정리 확인

### 4. 프로그램 매매 분석

#### ka90005 - 프로그램매매추이요청시간대별
- **목적**: 시간대별 프로그램 매매 추이 (차익/비차익)
- **전략 활용**: 기관 프로그램 매매 영향 분석
- **주요 데이터**:
  - 차익거래 매수/매도/순매수
  - 비차익거래 매수/매도/순매수
  - KOSPI200, BASIS 정보

```python
def analyze_program_trading_impact():
    """프로그램 매매 영향 분석"""
    today = datetime.now().strftime('%Y%m%d')
    
    program_data = get_program_trading_trend(date=today, mrkt_tp='P00101')
    
    analysis = {
        'arbitrage_pressure': 0,
        'non_arbitrage_pressure': 0,
        'overall_trend': 'NEUTRAL'
    }
    
    for data in program_data['prm_trde_trnsn']:
        arb_net = float(data['dfrt_trde_netprps'])
        non_arb_net = float(data['ndiffpro_trde_netprps'])
        
        analysis['arbitrage_pressure'] += arb_net
        analysis['non_arbitrage_pressure'] += non_arb_net
    
    total_pressure = analysis['arbitrage_pressure'] + analysis['non_arbitrage_pressure']
    
    if total_pressure > 500000000:  # 5억 이상 순매수
        analysis['overall_trend'] = 'BULLISH'
    elif total_pressure < -500000000:  # 5억 이상 순매도
        analysis['overall_trend'] = 'BEARISH'
    
    return analysis
```

#### ka90006 - 프로그램매매차익잔고추이요청
- **목적**: 프로그램 매매 차익 잔고 추이
- **전략 활용**: 차익거래 포지션 분석

#### ka90008 - 종목시간별프로그램매매추이요청
- **목적**: 특정 종목의 시간별 프로그램 매매
- **전략 활용**: 개별 종목 프로그램 영향도

#### ka90010 - 프로그램매매추이요청일자별
- **목적**: 일자별 프로그램 매매 추이
- **전략 활용**: 중장기 프로그램 트렌드

#### ka90013 - 종목일별프로그램매매추이요청
- **목적**: 특정 종목의 일별 프로그램 매매 추이
- **전략 활용**: 종목별 프로그램 패턴 분석

### 5. 기타 시세 정보

#### ka10006 - 주식시분요청
- **목적**: 분단위 시세 정보
- **전략 활용**: 단기 가격 변동 모니터링

#### ka10007 - 시세표성정보요청
- **목적**: 시세 표시 정보
- **전략 활용**: 화면 표시용 데이터

#### ka10011 - 신주인수권전체시세요청
- **목적**: 신주인수권 시세
- **전략 활용**: 특수상황 분석

#### ka10078 - 증권사별종목매매동향요청
- **목적**: 증권사별 매매 동향
- **전략 활용**: 세력 분석

#### ka10087 - 시간외단일가요청
- **목적**: 시간외 단일가 정보
- **전략 활용**: 시간외 거래 모니터링

## 전략 시스템 통합 전략

### 1. 실시간 시세 모니터링 시스템

```python
class RealTimeMarketMonitor:
    def __init__(self):
        self.tracking_stocks = {}
        self.market_analysis = {}
    
    def monitor_surge_stocks(self, stock_list):
        """급등주 실시간 모니터링"""
        for stock_code in stock_list:
            # 1. 호가 분석
            bid_analysis = self.analyze_bid_ask(stock_code)
            
            # 2. 체결강도 분석
            strength_analysis = self.analyze_execution_strength(stock_code)
            
            # 3. 기관 동향 확인
            institutional_flow = self.check_institutional_flow(stock_code)
            
            # 4. 통합 신호 생성
            signal = self.generate_integrated_signal(
                bid_analysis, strength_analysis, institutional_flow
            )
            
            self.tracking_stocks[stock_code] = signal
    
    def analyze_bid_ask(self, stock_code):
        """호가창 분석"""
        return get_stock_bid(stock_code)
    
    def analyze_execution_strength(self, stock_code):
        """체결강도 분석"""
        return get_execution_strength(stock_code)
    
    def check_institutional_flow(self, stock_code):
        """기관 수급 확인"""
        return check_institutional_support(stock_code)
```

### 2. 전략 진입 신호 생성

```python
class TumepokEntrySignalGenerator:
    def __init__(self):
        self.signal_weights = {
            'bid_imbalance': 0.3,
            'execution_strength': 0.25,
            'institutional_support': 0.25,
            'program_trading': 0.2
        }
    
    def generate_entry_signal(self, stock_code):
        """전략 진입 신호 생성"""
        signals = {}
        
        # 1. 호가 불균형 점수
        bid_data = get_stock_bid(stock_code)
        signals['bid_imbalance'] = self.calculate_bid_score(bid_data)
        
        # 2. 체결강도 점수
        strength_data = get_execution_strength(stock_code)
        signals['execution_strength'] = self.calculate_strength_score(strength_data)
        
        # 3. 기관 지원 점수
        institutional_data = check_institutional_support(stock_code)
        signals['institutional_support'] = self.calculate_institutional_score(institutional_data)
        
        # 4. 프로그램 매매 점수
        program_data = analyze_program_trading_impact()
        signals['program_trading'] = self.calculate_program_score(program_data)
        
        # 가중 평균 점수 계산
        total_score = sum(
            signals[key] * self.signal_weights[key] 
            for key in signals.keys()
        )
        
        return {
            'stock_code': stock_code,
            'total_score': total_score,
            'individual_scores': signals,
            'recommendation': self.get_recommendation(total_score)
        }
    
    def get_recommendation(self, score):
        """점수 기반 추천"""
        if score >= 80:
            return "STRONG_BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 40:
            return "HOLD"
        elif score >= 20:
            return "WEAK_SELL"
        else:
            return "SELL"
```

### 3. 리스크 관리 시스템

```python
class MarketRiskAssessment:
    def assess_market_condition(self):
        """시장 상황 평가"""
        assessment = {
            'program_trading_pressure': self.assess_program_pressure(),
            'institutional_flow': self.assess_institutional_flow(),
            'market_strength': self.assess_market_strength(),
            'overall_risk_level': 'MEDIUM'
        }
        
        # 전체 리스크 레벨 계산
        risk_factors = [
            assessment['program_trading_pressure'],
            assessment['institutional_flow'],
            assessment['market_strength']
        ]
        
        high_risk_count = sum(1 for factor in risk_factors if factor == 'HIGH_RISK')
        
        if high_risk_count >= 2:
            assessment['overall_risk_level'] = 'HIGH'
        elif high_risk_count == 0:
            assessment['overall_risk_level'] = 'LOW'
        
        return assessment
    
    def assess_program_pressure(self):
        """프로그램 매매 압력 평가"""
        program_data = analyze_program_trading_impact()
        
        if program_data['overall_trend'] == 'BEARISH':
            return 'HIGH_RISK'
        elif program_data['overall_trend'] == 'BULLISH':
            return 'LOW_RISK'
        else:
            return 'MEDIUM_RISK'
```

### 4. 백테스팅 데이터 수집

```python
class HistoricalDataCollector:
    def collect_tumepok_backtest_data(self, stock_code, start_date, end_date):
        """전략 백테스팅용 데이터 수집"""
        data = {
            'daily_prices': [],
            'institutional_flows': [],
            'execution_strengths': [],
            'program_trading': []
        }
        
        # 일별 주가 데이터
        data['daily_prices'] = self.get_historical_prices(stock_code, start_date, end_date)
        
        # 기관 수급 데이터
        data['institutional_flows'] = self.get_historical_institutional_flow(
            stock_code, start_date, end_date
        )
        
        # 체결강도 데이터
        data['execution_strengths'] = self.get_historical_execution_strength(
            stock_code, start_date, end_date
        )
        
        # 프로그램 매매 데이터
        data['program_trading'] = self.get_historical_program_trading(
            start_date, end_date
        )
        
        return data
```

## API 사용 시 주의사항

### 1. 공통 설정
- **엔드포인트**: `/api/dostk/mrkcond`
- **인증**: Bearer 토큰 필수
- **Content-Type**: `application/json;charset=UTF-8`

### 2. 실시간 데이터 특성
- 호가 데이터는 실시간 변동
- 체결강도는 누적 계산
- 프로그램 매매는 시간 지연 가능

### 3. 연속조회 처리
```python
def get_continuous_data(api_function, params):
    all_data = []
    cont_yn = 'N'
    next_key = ''
    
    while True:
        response = api_function(params, cont_yn, next_key)
        
        if 'error' in response:
            break
            
        all_data.extend(response['body']['data'])
        
        if response['header']['cont-yn'] != 'Y':
            break
            
        cont_yn = response['header']['cont-yn']
        next_key = response['header']['next-key']
    
    return all_data
```

### 4. 데이터 신뢰성 검증
```python
def validate_market_data(data):
    """시세 데이터 유효성 검증"""
    if not data or len(data) == 0:
        return False
    
    # 가격 데이터 검증
    try:
        float(data['cur_prc'])
        float(data['flu_rt'])
        int(data['trde_qty'])
    except (ValueError, KeyError):
        return False
    
    return True
```

## 전략 전략 최적화

### 1. 데이터 우선순위
1. **ka10004** (주식호가) - 실시간 진입/청산 결정
2. **ka10005** (일주월시분) - 연속상승일 계산
3. **ka10046** (체결강도) - 모멘텀 확인
4. **ka10044** (기관매매) - 수급 지원 확인

### 2. 실시간 업데이트 주기
- 호가 정보: 1초마다 업데이트
- 체결강도: 5분마다 업데이트
- 기관 동향: 10분마다 업데이트
- 프로그램 매매: 30분마다 업데이트

### 3. 메모리 효율성
- 필요한 종목만 실시간 모니터링
- 과거 데이터는 압축 저장
- 불필요한 필드 제거로 데이터 최적화

이러한 시세 정보 API들을 체계적으로 활용하면 전략 전략의 핵심인 정확한 타이밍 포착과 리스크 관리가 가능합니다.