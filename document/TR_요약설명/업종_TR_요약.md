# 업종_TR API 요약

## 개요

업종_TR 폴더는 키움증권 REST API의 업종별 정보 조회 API들을 포함합니다. 이 API들은 전략(tumepok) 자동매매 시스템에서 시장 전체 동향 파악, 섹터 로테이션 분석, 업종별 수급 분석을 통한 거래 전략 수립에 활용됩니다.

## 공통 설정

### API 기본 정보
- **엔드포인트**: `/api/dostk/sect`
- **메서드**: POST
- **인증**: Bearer 토큰 필요
- **Content-Type**: `application/json;charset=UTF-8`

### 업종 코드 체계
```python
SECTOR_CODES = {
    # KOSPI 업종
    '001': '종합(KOSPI)',
    '002': '대형주',
    '003': '중형주', 
    '004': '소형주',
    
    # KOSDAQ 업종
    '101': '종합(KOSDAQ)',
    
    # 기타 지수
    '201': 'KOSPI200',
    '302': 'KOSTAR',
    '701': 'KRX100',
    
    # 세부 업종 (예시)
    '010': '음식료업',
    '020': '섬유의복',
    '030': '종이목재',
    '040': '화학',
    '050': '의약품',
    '060': '비금속광물',
    '070': '철강금속',
    '080': '기계',
    '090': '전기전자',
    '100': '의료정밀',
    '110': '운수장비',
    '120': '유통업',
    '130': '전기가스업',
    '140': '건설업',
    '150': '운수창고',
    '160': '통신업',
    '170': '금융업',
    '180': '은행',
    '190': '증권',
    '200': '보험',
    '210': '서비스업',
    '220': '제조업'
}
```

### 시장 구분 코드
- `0`: 코스피 (KOSPI)
- `1`: 코스닥 (KOSDAQ)
- `2`: 코스피200 (KOSPI200)

## 주요 API 분류

### 1. ka20001 - 업종현재가요청 (핵심)

#### 기본 정보
- **목적**: 업종별 실시간 현재가 및 시세 정보
- **전략 활용**: 업종별 강세/약세 파악, 섹터 로테이션 전략

#### 주요 파라미터
```python
{
    'mrkt_tp': '0',    # 시장구분 (0:코스피, 1:코스닥, 2:코스피200)
    'inds_cd': '001'   # 업종코드
}
```

#### 주요 응답 데이터
```python
SECTOR_QUOTE_FIELDS = {
    'cur_prc': '현재가',
    'pred_pre_sig': '전일대비기호',
    'pred_pre': '전일대비',
    'flu_rt': '등락률',
    'trde_qty': '거래량',
    'trde_prica': '거래대금',
    'trde_frmatn_stk_num': '거래형성종목수',
    'trde_frmatn_rt': '거래형성비율',
    'open_prc': '시가',
    'high_prc': '고가',
    'low_prc': '저가',
    'upl': '상한',      # 상한가 종목수
    'rising': '상승',   # 상승 종목수
    'stdns': '보합',    # 보합 종목수
    'fall': '하락',     # 하락 종목수
    'lst': '하한',      # 하한가 종목수
    '52wk_hgst_pric': '52주최고가',
    '52wk_lwst_pric': '52주최저가'
}
```

#### 전략 활용 예시
```python
def analyze_sector_strength():
    """업종별 강세 분석"""
    
    # 주요 업종별 현재가 조회
    strong_sectors = []
    weak_sectors = []
    
    major_sectors = ['010', '040', '050', '090', '170']  # 주요 업종
    
    for sector_code in major_sectors:
        sector_data = get_sector_quote(sector_code)
        
        change_rate = float(sector_data['flu_rt'])
        rising_stocks = int(sector_data['rising'])
        falling_stocks = int(sector_data['fall'])
        
        # 업종 강도 계산
        sector_strength = {
            'code': sector_code,
            'change_rate': change_rate,
            'rising_ratio': rising_stocks / (rising_stocks + falling_stocks) if (rising_stocks + falling_stocks) > 0 else 0,
            'trading_formation_ratio': float(sector_data['trde_frmatn_rt'])
        }
        
        # 강세 업종 판별 (등락률 > 1% 및 상승 종목 비율 > 60%)
        if change_rate > 1.0 and sector_strength['rising_ratio'] > 0.6:
            strong_sectors.append(sector_strength)
        elif change_rate < -1.0 and sector_strength['rising_ratio'] < 0.4:
            weak_sectors.append(sector_strength)
    
    return {
        'strong_sectors': sorted(strong_sectors, key=lambda x: x['change_rate'], reverse=True),
        'weak_sectors': sorted(weak_sectors, key=lambda x: x['change_rate'])
    }
```

### 2. ka20003 - 전업종지수요청

#### 기본 정보
- **목적**: 전체 업종의 지수 정보 일괄 조회
- **전략 활용**: 시장 전체 히트맵 분석, 섹터별 비교

#### 주요 응답 데이터
```python
ALL_SECTOR_INDEX_FIELDS = {
    'stk_cd': '종목코드',
    'stk_nm': '종목명',
    'cur_prc': '현재가',
    'pre_sig': '대비기호',
    'pred_pre': '전일대비',
    'flu_rt': '등락률',
    'trde_qty': '거래량',
    'wght': '비중',
    'trde_prica': '거래대금',
    'upl': '상한',
    'rising': '상승',
    'stdns': '보합',
    'fall': '하락',
    'lst': '하한',
    'flo_stk_num': '상장종목수'
}
```

#### 전략 활용 예시
```python
def create_sector_heatmap():
    """업종별 히트맵 생성"""
    
    all_sectors = get_all_sector_index()
    
    heatmap_data = []
    for sector in all_sectors['all_inds_idex']:
        sector_info = {
            'sector_code': sector['stk_cd'],
            'sector_name': sector['stk_nm'],
            'change_rate': float(sector['flu_rt']),
            'trading_volume': int(sector['trde_qty']),
            'market_weight': float(sector['wght']),
            'rising_count': int(sector['rising']),
            'falling_count': int(sector['fall']),
            'total_stocks': int(sector['flo_stk_num'])
        }
        
        # 업종 건강도 계산
        sector_info['health_score'] = calculate_sector_health(sector_info)
        heatmap_data.append(sector_info)
    
    return sorted(heatmap_data, key=lambda x: x['change_rate'], reverse=True)

def calculate_sector_health(sector_info):
    """업종 건강도 계산"""
    change_rate = sector_info['change_rate']
    rising_ratio = sector_info['rising_count'] / sector_info['total_stocks']
    
    # 가중 점수 계산 (등락률 70% + 상승종목비율 30%)
    health_score = (change_rate * 0.7) + (rising_ratio * 100 * 0.3)
    return health_score
```

### 3. ka10010 - 업종프로그램요청

#### 기본 정보
- **목적**: 특정 종목의 업종별 프로그램 매매 정보
- **전략 활용**: 기관 프로그램 매매 동향 파악

#### 주요 응답 데이터
```python
PROGRAM_TRADING_FIELDS = {
    'dfrt_trst_sell_qty': '차익위탁매도수량',
    'dfrt_trst_sell_amt': '차익위탁매도금액',
    'dfrt_trst_buy_qty': '차익위탁매수수량',
    'dfrt_trst_buy_amt': '차익위탁매수금액',
    'dfrt_trst_netprps_qty': '차익위탁순매수수량',
    'dfrt_trst_netprps_amt': '차익위탁순매수금액',
    'ndiffpro_trst_sell_qty': '비차익위탁매도수량',
    'ndiffpro_trst_sell_amt': '비차익위탁매도금액',
    'ndiffpro_trst_buy_qty': '비차익위탁매수수량',
    'ndiffpro_trst_buy_amt': '비차익위탁매수금액',
    'ndiffpro_trst_netprps_qty': '비차익위탁순매수수량',
    'ndiffpro_trst_netprps_amt': '비차익위탁순매수금액'
}
```

#### 전략 활용 예시
```python
def analyze_program_trading_impact(stock_code):
    """프로그램 매매 영향 분석"""
    
    program_data = get_sector_program_trading(stock_code)
    
    # 차익거래 분석
    arbitrage_net_buy = int(program_data['dfrt_trst_netprps_amt'])
    non_arbitrage_net_buy = int(program_data['ndiffpro_trst_netprps_amt'])
    total_net_buy = arbitrage_net_buy + non_arbitrage_net_buy
    
    analysis = {
        'arbitrage_pressure': arbitrage_net_buy,
        'non_arbitrage_pressure': non_arbitrage_net_buy,
        'total_pressure': total_net_buy,
        'program_impact_level': 'NEUTRAL'
    }
    
    # 프로그램 매매 영향도 판별
    if total_net_buy > 500000000:  # 5억원 이상 순매수
        analysis['program_impact_level'] = 'POSITIVE'
    elif total_net_buy < -500000000:  # 5억원 이상 순매도
        analysis['program_impact_level'] = 'NEGATIVE'
    
    return analysis
```

### 4. ka10051 - 업종별투자자순매수요청

#### 기본 정보
- **목적**: 업종별 투자자 유형별 순매수 정보
- **전략 활용**: 업종별 수급 분석, 스마트머니 추적

#### 주요 파라미터
```python
{
    'mrkt_tp': '0',        # 시장구분 (코스피:0, 코스닥:1)
    'amt_qty_tp': '0',     # 금액수량구분 (금액:0, 수량:1)
    'base_dt': '20241107', # 기준일자 (YYYYMMDD)
    'stex_tp': '3'         # 거래소구분 (1:KRX, 2:NXT, 3:통합)
}
```

#### 주요 응답 데이터 (투자자별 순매수)
```python
INVESTOR_NET_BUY_FIELDS = {
    'sc_netprps': '증권순매수',
    'insrnc_netprps': '보험순매수',
    'invtrt_netprps': '투신순매수',
    'bank_netprps': '은행순매수',
    'jnsinkm_netprps': '종신금순매수',
    'endw_netprps': '기금순매수',
    'etc_corp_netprps': '기타법인순매수',
    'ind_netprps': '개인순매수',
    'frgnr_netprps': '외국인순매수',
    'native_trmt_frgnr_netprps': '내국인대우외국인순매수',
    'natn_netprps': '국가순매수',
    'samo_fund_netprps': '사모펀드순매수',
    'orgn_netprps': '기관계순매수'
}
```

#### 전략 활용 예시
```python
def analyze_sector_money_flow():
    """업종별 자금 흐름 분석"""
    
    today = datetime.now().strftime('%Y%m%d')
    
    # 코스피 업종별 투자자 순매수 조회
    kospi_flow = get_sector_investor_flow('0', today)
    # 코스닥 업종별 투자자 순매수 조회  
    kosdaq_flow = get_sector_investor_flow('1', today)
    
    money_flow_analysis = {
        'foreign_preferred_sectors': [],
        'institution_preferred_sectors': [],
        'individual_preferred_sectors': [],
        'smart_money_consensus': []
    }
    
    all_sectors = kospi_flow['inds_netprps'] + kosdaq_flow['inds_netprps']
    
    for sector in all_sectors:
        sector_code = sector['inds_cd']
        sector_name = sector['inds_nm']
        
        foreign_net = int(sector['frgnr_netprps'])
        institution_net = int(sector['orgn_netprps'])
        individual_net = int(sector['ind_netprps'])
        
        # 외국인 선호 업종 (순매수 > 50억)
        if foreign_net > 5000000000:
            money_flow_analysis['foreign_preferred_sectors'].append({
                'sector': sector_name,
                'net_buy': foreign_net
            })
        
        # 기관 선호 업종 (순매수 > 30억)
        if institution_net > 3000000000:
            money_flow_analysis['institution_preferred_sectors'].append({
                'sector': sector_name,
                'net_buy': institution_net
            })
        
        # 스마트머니 합의 업종 (외국인 + 기관 모두 순매수)
        if foreign_net > 0 and institution_net > 0:
            money_flow_analysis['smart_money_consensus'].append({
                'sector': sector_name,
                'foreign_net': foreign_net,
                'institution_net': institution_net,
                'combined_strength': foreign_net + institution_net
            })
    
    return money_flow_analysis
```

### 5. ka20002 - 업종별주가요청

#### 기본 정보
- **목적**: 특정 업종에 속한 개별 종목들의 주가 정보
- **전략 활용**: 업종 내 종목별 상대 강도 분석

#### 전략 활용 예시
```python
def find_sector_leaders(sector_code):
    """업종 내 리더 종목 발굴"""
    
    sector_stocks = get_sector_stock_prices(sector_code)
    
    leaders = []
    laggards = []
    
    for stock in sector_stocks['inds_stkpc']:
        stock_info = {
            'code': stock['stk_cd'],
            'name': stock['stk_nm'],
            'current_price': float(stock['cur_prc']),
            'change_rate': float(stock['flu_rt']),
            'volume': int(stock['now_trde_qty']),
            'high_price': float(stock['high_pric']),
            'low_price': float(stock['low_pric'])
        }
        
        # 상대 강도 계산
        if stock_info['change_rate'] > 0:
            stock_info['relative_strength'] = (
                (stock_info['current_price'] - stock_info['low_price']) /
                (stock_info['high_price'] - stock_info['low_price'])
            ) * 100
        else:
            stock_info['relative_strength'] = 0
        
        # 리더/래거드 분류
        if stock_info['change_rate'] > 5.0 and stock_info['relative_strength'] > 80:
            leaders.append(stock_info)
        elif stock_info['change_rate'] < -3.0 and stock_info['relative_strength'] < 30:
            laggards.append(stock_info)
    
    return {
        'leaders': sorted(leaders, key=lambda x: x['change_rate'], reverse=True),
        'laggards': sorted(laggards, key=lambda x: x['change_rate'])
    }
```

### 6. ka20009 - 업종현재가일별요청

#### 기본 정보
- **목적**: 업종의 일별 현재가 추이 정보
- **전략 활용**: 업종별 추세 분석, 모멘텀 확인

#### 전략 활용 예시
```python
def analyze_sector_trend(sector_code):
    """업종 추세 분석"""
    
    daily_data = get_sector_daily_prices(sector_code)
    
    # 일별 데이터 추출
    daily_prices = []
    for daily_info in daily_data['inds_cur_prc_daly_rept']:
        daily_prices.append({
            'date': daily_info['dt_n'],
            'price': float(daily_info['cur_prc_n']),
            'change_rate': float(daily_info['flu_rt_n']),
            'volume': int(daily_info['acc_trde_qty_n'])
        })
    
    # 추세 분석
    if len(daily_prices) >= 5:
        recent_5days = daily_prices[-5:]
        positive_days = sum(1 for day in recent_5days if day['change_rate'] > 0)
        
        trend_analysis = {
            'trend_direction': 'BULLISH' if positive_days >= 3 else 'BEARISH',
            'momentum_strength': calculate_momentum(daily_prices),
            'volume_trend': analyze_volume_trend(daily_prices)
        }
        
        return trend_analysis
    
    return None
```

## 전략 시스템 통합 전략

### 1. 섹터 로테이션 전략

```python
class SectorRotationStrategy:
    def __init__(self):
        self.sector_rankings = {}
        self.rotation_threshold = 0.02  # 2% 이상 차이
        
    def analyze_sector_rotation(self):
        """섹터 로테이션 분석"""
        
        # 전 업종 성과 분석
        sector_performance = self.get_all_sector_performance()
        
        # 상대 강도 순위 계산
        sorted_sectors = sorted(
            sector_performance.items(),
            key=lambda x: x[1]['relative_strength'],
            reverse=True
        )
        
        # 로테이션 신호 생성
        rotation_signals = self.detect_rotation_signals(sorted_sectors)
        
        return rotation_signals
    
    def detect_rotation_signals(self, sorted_sectors):
        """로테이션 신호 감지"""
        signals = []
        
        top_sectors = sorted_sectors[:3]  # 상위 3개 업종
        bottom_sectors = sorted_sectors[-3:]  # 하위 3개 업종
        
        for sector_code, performance in top_sectors:
            if performance['momentum_change'] > self.rotation_threshold:
                signals.append({
                    'action': 'ROTATE_INTO',
                    'sector': sector_code,
                    'strength': performance['relative_strength'],
                    'reason': 'Strong momentum building'
                })
        
        return signals
```

### 2. 업종별 급등주 발굴

```python
class SectorSurgeDetector:
    def __init__(self):
        self.surge_threshold = 20.0  # 20% 이상 급등
        
    def scan_sector_surges(self):
        """업종별 급등주 스캐닝"""
        
        surge_candidates = {}
        
        # 주요 업종별 스캔
        major_sectors = ['010', '040', '050', '090', '170']
        
        for sector_code in major_sectors:
            # 업종 전체 강도 확인
            sector_strength = self.check_sector_strength(sector_code)
            
            if sector_strength['change_rate'] > 2.0:  # 업종 자체가 2% 이상 상승
                # 업종 내 개별 종목 분석
                sector_stocks = get_sector_stock_prices(sector_code)
                
                for stock in sector_stocks['inds_stkpc']:
                    change_rate = float(stock['flu_rt'])
                    volume = int(stock['now_trde_qty'])
                    
                    # 전략 조건: 20% 이상 상승 + 10만주 이상 거래
                    if change_rate >= self.surge_threshold and volume >= 100000:
                        surge_candidates[stock['stk_cd']] = {
                            'stock_name': stock['stk_nm'],
                            'sector': sector_code,
                            'change_rate': change_rate,
                            'volume': volume,
                            'sector_support': sector_strength['change_rate']
                        }
        
        return surge_candidates
```

### 3. 업종별 리스크 관리

```python
class SectorRiskManager:
    def __init__(self):
        self.sector_exposure_limits = {
            'single_sector_max': 0.3,  # 단일 업종 최대 30%
            'top3_sectors_max': 0.6,   # 상위 3개 업종 최대 60%
            'correlation_threshold': 0.7  # 상관관계 임계치
        }
    
    def assess_sector_concentration_risk(self, portfolio):
        """업종 집중도 리스크 평가"""
        
        sector_exposure = {}
        total_value = sum(position['value'] for position in portfolio.values())
        
        # 업종별 노출도 계산
        for stock_code, position in portfolio.items():
            sector = self.get_stock_sector(stock_code)
            sector_weight = position['value'] / total_value
            
            if sector in sector_exposure:
                sector_exposure[sector] += sector_weight
            else:
                sector_exposure[sector] = sector_weight
        
        # 리스크 신호 생성
        risk_signals = []
        
        # 단일 업종 집중도 체크
        for sector, weight in sector_exposure.items():
            if weight > self.sector_exposure_limits['single_sector_max']:
                risk_signals.append({
                    'type': 'SECTOR_CONCENTRATION',
                    'sector': sector,
                    'current_weight': weight,
                    'limit': self.sector_exposure_limits['single_sector_max'],
                    'recommendation': 'REDUCE_EXPOSURE'
                })
        
        return {
            'sector_exposure': sector_exposure,
            'risk_signals': risk_signals,
            'overall_risk_level': self.calculate_overall_risk(risk_signals)
        }
```

### 4. 업종별 백테스팅

```python
class SectorBacktester:
    def __init__(self):
        self.lookback_period = 252  # 1년
        
    def backtest_sector_strategy(self, start_date, end_date):
        """업종별 전략 백테스팅"""
        
        results = {
            'sector_rotation_returns': {},
            'sector_momentum_returns': {},
            'benchmark_return': 0,
            'alpha_by_sector': {}
        }
        
        # 업종별 수익률 계산
        for sector_code in MAJOR_SECTORS:
            sector_returns = self.calculate_sector_returns(
                sector_code, start_date, end_date
            )
            
            # 업종 로테이션 전략 성과
            rotation_returns = self.simulate_rotation_strategy(
                sector_code, sector_returns
            )
            
            results['sector_rotation_returns'][sector_code] = rotation_returns
            
            # 벤치마크 대비 알파 계산
            benchmark_returns = self.get_benchmark_returns(start_date, end_date)
            alpha = rotation_returns['total_return'] - benchmark_returns
            results['alpha_by_sector'][sector_code] = alpha
        
        return results
```

## API 사용 시 주의사항

### 1. 공통 설정
- **엔드포인트**: `/api/dostk/sect`
- **인증**: Bearer 토큰 필수
- **업종 코드**: 정확한 3자리 코드 사용

### 2. 데이터 해석
- 업종 지수는 시가총액 가중평균
- 거래형성비율은 실제 거래 참여도 지표
- 52주 고저가 대비율로 상대적 위치 파악

### 3. 연속조회 처리
```python
def get_all_sector_data(api_function, params):
    """업종 데이터 연속조회"""
    all_data = []
    cont_yn = 'N'
    next_key = ''
    
    while True:
        response = api_function(params, cont_yn, next_key)
        
        if response.get('body'):
            all_data.extend(response['body'])
            
        if response.get('header', {}).get('cont-yn') != 'Y':
            break
            
        cont_yn = 'Y'
        next_key = response['header']['next-key']
    
    return all_data
```

### 4. 업종 코드 검증
```python
def validate_sector_code(sector_code):
    """업종 코드 유효성 검증"""
    if len(sector_code) != 3 or not sector_code.isdigit():
        return False
    
    valid_codes = ['001', '002', '003', '004', '101', '201', '302', '701']
    detailed_codes = [f'{i:03d}' for i in range(10, 230, 10)]
    
    return sector_code in valid_codes or sector_code in detailed_codes
```

## 전략 업종 전략 최적화

### 1. 업종 강도 지표
- 업종 내 상승 종목 비율
- 거래형성비율
- 외국인/기관 순매수 동향
- 프로그램 매매 압력

### 2. 섹터 로테이션 타이밍
- 업종 간 상대 강도 변화
- 경제 사이클과 업종 특성
- 계절성 및 이벤트 영향

### 3. 리스크 분산 전략
- 업종별 노출도 제한
- 상관관계 낮은 업종 조합
- 방어적 업종 편입 비율

이러한 업종 정보 API들을 체계적으로 활용하면 전략 전략에서 개별 종목뿐만 아니라 시장 전체의 흐름을 파악하고, 보다 정교한 포트폴리오 관리와 리스크 분산이 가능합니다.