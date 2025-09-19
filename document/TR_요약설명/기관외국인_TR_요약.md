# 기관외국인 TR 문서 요약

## 개요
기관외국인 TR은 키움증권 REST API를 통해 기관과 외국인의 매매 동향을 분석하는 기능을 제공합니다. 개별 종목 및 시장 전체의 기관/외국인 순매수 현황, 연속 매매 패턴, 보유 비중 등 수급 분석에 필수적인 데이터를 실시간으로 확인할 수 있습니다.

## 공통 사항

### API 설정
- **엔드포인트**: `/api/dostk/frgnistt`
- **메서드**: POST
- **인증**: Bearer 토큰 필요
- **서버**:
  - 실전: `https://api.kiwoom.com`
  - 모의: `https://mockapi.kiwoom.com`

## 주요 기능

### 1. ka10008 - 주식외국인종목별매매동향
**목적**: 특정 종목의 외국인 매매 동향 및 보유 현황 추적

**필수 파라미터**:
- `stk_cd`: 종목코드

**응답 데이터**:
- **일자별 정보**:
  - 일자, 종가, 전일대비
  - 거래량
  - 변동수량 (순매수/순매도)
  - 보유주식수
  - 비중 (전체 발행주식 대비)
  - 취득가능주식수
  - 외국인한도 및 증감
  - 한도소진률

**활용**:
- 외국인 수급 변화 추적
- 외국인 보유 비중 모니터링
- 한도소진률 기반 매매 신호

### 2. ka10009 - 주식기관요청
**목적**: 특정 종목의 기관/외국인 종합 매매 동향

**필수 파라미터**:
- `stk_cd`: 종목코드

**응답 데이터**:
- 날짜, 종가, 대비
- 기관 기간누적 매매량
- 기관 일별 순매매
- 외국인 일별 순매매
- 외국인 지분율

**활용**:
- 기관과 외국인 동향 비교
- 누적 매매 추이 분석
- 지분율 변화 추적

### 3. ka10131 - 기관외국인연속매매현황요청
**목적**: 시장 전체에서 기관/외국인이 연속 매수/매도하는 종목 발굴

**필수 파라미터**:
- `dt`: 기간 (1일, 3일, 5일, 10일, 20일, 120일)
- `mrkt_tp`: 장구분 (코스피/코스닥)
- `netslmt_tp`: 순매도수구분 (2:순매수 고정)
- `stk_inds_tp`: 종목업종구분 (0:종목, 1:업종)
- `amt_qty_tp`: 금액수량구분 (0:금액, 1:수량)
- `stex_tp`: 거래소구분 (1:KRX, 2:NXT, 3:통합)

**응답 데이터**:
- **순위별 종목 정보**:
  - 순위, 종목코드, 종목명
  - 기간 중 주가등락률
  - **기관 매매**:
    - 순매매금액/수량
    - 연속순매수일수
    - 연속순매수량/금액
  - **외국인 매매**:
    - 순매매금액/수량
    - 연속순매수일수
    - 연속순매수량/금액
  - **합계**:
    - 총 연속순매수일수
    - 총 연속순매매수량/금액

**활용**:
- 기관/외국인 집중 매수 종목 발굴
- 연속 매매 패턴 분석
- 수급 주도주 선별

## 시스템 활용 가이드

### 1. 수급 기반 종목 필터링
```python
def filter_by_supply_demand(stock_code):
    """기관/외국인 수급으로 종목 필터링"""
    
    # ka10009: 기관/외국인 매매 동향
    supply_data = get_institutional_foreign_trading(stock_code)
    
    # 최근 5일 순매수 합계
    recent_5days = supply_data[-5:]
    
    inst_net_buy = sum([float(d['orgn_daly_nettrde']) for d in recent_5days])
    foreign_net_buy = sum([float(d['frgnr_daly_nettrde']) for d in recent_5days])
    
    # 수급 점수 계산
    supply_score = 0
    
    # 기관 순매수
    if inst_net_buy > 0:
        supply_score += 1
    
    # 외국인 순매수
    if foreign_net_buy > 0:
        supply_score += 1
    
    # 외국인 지분율 증가
    if float(supply_data[-1]['frgnr_qota_rt']) > float(supply_data[-5]['frgnr_qota_rt']):
        supply_score += 1
    
    return supply_score >= 2  # 2개 이상 충족 시 통과
```

### 2. 연속 매수 종목 발굴
```python
def find_continuous_buying_stocks():
    """기관/외국인 연속 매수 종목 발굴"""
    
    # ka10131: 연속매매현황
    params = {
        'dt': '5',  # 5일간
        'mrkt_tp': '001',  # 코스피
        'amt_qty_tp': '0',  # 금액 기준
        'stex_tp': '1'  # KRX
    }
    
    continuous_buying = get_continuous_trading(params)
    
    strong_stocks = []
    
    for stock in continuous_buying['orgn_frgnr_cont_trde_prst']:
        # 기관/외국인 모두 3일 이상 연속 매수
        if (int(stock['orgn_cont_netprps_dys']) >= 3 and 
            int(stock['frgnr_cont_netprps_dys']) >= 3):
            
            strong_stocks.append({
                'code': stock['stk_cd'],
                'name': stock['stk_nm'],
                'inst_days': stock['orgn_cont_netprps_dys'],
                'foreign_days': stock['frgnr_cont_netprps_dys'],
                'price_change': stock['prid_stkpc_flu_rt']
            })
    
    return strong_stocks
```

### 3. 외국인 한도 모니터링
```python
def monitor_foreign_limit(stock_code):
    """외국인 한도 소진률 모니터링"""
    
    # ka10008: 외국인 매매 동향
    foreign_data = get_foreign_trading(stock_code)
    
    latest = foreign_data[-1]
    
    limit_exhaustion = float(latest['limit_exh_rt'])
    foreign_holding = float(latest['wght'])
    
    # 한도 소진률 경고 레벨
    if limit_exhaustion >= 90:
        return "CRITICAL", "한도소진 임박"
    elif limit_exhaustion >= 70:
        return "WARNING", "한도소진 주의"
    elif limit_exhaustion >= 50:
        return "WATCH", "한도소진 관찰"
    else:
        return "NORMAL", f"여유 {100-limit_exhaustion:.1f}%"
```

### 4. 수급 전환 신호 포착
```python
class SupplyDemandSignal:
    def __init__(self):
        self.history = {}
    
    def detect_reversal(self, stock_code):
        """수급 전환 신호 감지"""
        
        # ka10009: 최근 20일 데이터
        data = get_institutional_foreign_20days(stock_code)
        
        # 5일 이동평균
        ma5_inst = self.calculate_ma(data, 'orgn_daly_nettrde', 5)
        ma5_foreign = self.calculate_ma(data, 'frgnr_daly_nettrde', 5)
        
        # 20일 이동평균
        ma20_inst = self.calculate_ma(data, 'orgn_daly_nettrde', 20)
        ma20_foreign = self.calculate_ma(data, 'frgnr_daly_nettrde', 20)
        
        signals = []
        
        # 기관 매수 전환 (5일 MA > 20일 MA 상향돌파)
        if ma5_inst[-1] > ma20_inst[-1] and ma5_inst[-2] <= ma20_inst[-2]:
            signals.append("기관 매수 전환")
        
        # 외국인 매수 전환
        if ma5_foreign[-1] > ma20_foreign[-1] and ma5_foreign[-2] <= ma20_foreign[-2]:
            signals.append("외국인 매수 전환")
        
        return signals
```

### 5. 전략과 수급 결합
```python
class TumepokWithSupplyDemand:
    def __init__(self):
        self.supply_weight = 0.3  # 수급 가중치 30%
        self.technical_weight = 0.7  # 기술적 분석 가중치 70%
    
    def calculate_entry_score(self, stock_code, tumepok_score):
        """전략 점수와 수급 점수 결합"""
        
        # 수급 점수 계산 (0~100)
        supply_score = self.calculate_supply_score(stock_code)
        
        # 최종 점수 = 전략 점수 * 0.7 + 수급 점수 * 0.3
        final_score = (tumepok_score * self.technical_weight + 
                      supply_score * self.supply_weight)
        
        return final_score
    
    def calculate_supply_score(self, stock_code):
        """수급 점수 계산"""
        score = 0
        
        # ka10131: 연속 매수 확인
        continuous = get_continuous_buying_info(stock_code)
        
        # 기관 연속 매수일
        if continuous['inst_days'] >= 3:
            score += 30
        elif continuous['inst_days'] >= 1:
            score += 15
        
        # 외국인 연속 매수일
        if continuous['foreign_days'] >= 3:
            score += 40
        elif continuous['foreign_days'] >= 1:
            score += 20
        
        # ka10008: 외국인 비중 증가
        foreign_trend = get_foreign_holding_trend(stock_code)
        if foreign_trend > 0:
            score += 30
        
        return min(score, 100)  # 최대 100점
```

## 실전 활용 시나리오

### 1. 급등주 수급 확인
```python
def validate_surge_with_supply(stock_code, surge_rate):
    """급등주의 수급 뒷받침 확인"""
    
    if surge_rate < 20:
        return False, "급등 조건 미충족"
    
    # 수급 확인
    supply_check = {
        'inst_buying': False,
        'foreign_buying': False,
        'continuous_days': 0
    }
    
    # ka10131: 연속 매수 확인
    continuous = get_continuous_trading_single(stock_code)
    
    if continuous['inst_net_buy'] > 0:
        supply_check['inst_buying'] = True
    
    if continuous['foreign_net_buy'] > 0:
        supply_check['foreign_buying'] = True
    
    supply_check['continuous_days'] = max(
        continuous['inst_days'],
        continuous['foreign_days']
    )
    
    # 급등 + 수급 = 강한 매수 신호
    if supply_check['inst_buying'] and supply_check['foreign_buying']:
        return True, "급등 + 기관/외국인 동반 매수"
    elif supply_check['inst_buying'] or supply_check['foreign_buying']:
        return True, "급등 + 일부 수급 지원"
    else:
        return False, "급등했으나 수급 미흡"
```

### 2. 매도 타이밍 판단
```python
def check_sell_signal_with_supply(position):
    """수급 기반 매도 신호"""
    
    stock_code = position['stock_code']
    
    # ka10009: 최근 수급 동향
    recent_supply = get_recent_supply(stock_code, days=5)
    
    sell_signals = []
    
    # 기관 매도 전환
    if recent_supply['inst_trend'] < 0:
        sell_signals.append("기관 매도 전환")
    
    # 외국인 매도 전환
    if recent_supply['foreign_trend'] < 0:
        sell_signals.append("외국인 매도 전환")
    
    # 연속 매도일 3일 이상
    if recent_supply['inst_sell_days'] >= 3:
        sell_signals.append("기관 3일 연속 매도")
    
    if recent_supply['foreign_sell_days'] >= 3:
        sell_signals.append("외국인 3일 연속 매도")
    
    # 매도 신호 강도
    if len(sell_signals) >= 2:
        return "STRONG_SELL", sell_signals
    elif len(sell_signals) == 1:
        return "WEAK_SELL", sell_signals
    else:
        return "HOLD", []
```

## 주요 지표 해석

### 외국인 관련
- **보유주식수**: 외국인이 보유한 총 주식 수
- **비중**: 전체 발행주식 대비 외국인 보유 비율
- **한도소진률**: 외국인 투자한도 대비 현재 보유 비율
- **변동수량**: 일별 순매수/순매도 수량

### 기관 관련
- **기관계**: 금융투자, 보험, 투신, 은행, 연기금 등 총합
- **기간누적**: 특정 기간 동안의 누적 매매량
- **연속매수일**: 연속으로 순매수한 일수

### 매매 패턴
- **연속 3일 이상**: 강한 매수/매도 신호
- **기관/외국인 동반**: 수급 신뢰도 높음
- **divergence**: 기관↑ 외국인↓ 또는 반대 = 관망

## 주의사항

### 데이터 해석
- 기관/외국인 매매는 T+1 공시 (1일 지연)
- 프로그램 매매와 실제 투자 구분 필요
- 윈도우 드레싱 기간 왜곡 주의

### 한계점
- 개인 투자자 동향 미포함
- 차익거래/헤지 거래 구분 불가
- 장외거래 미반영

### API 제한
- 호출 횟수 제한
- 대량 데이터 조회 시 연속조회 활용
- 실시간 데이터 아님 (지연 반영)

## 결론
기관외국인 TR은 투매폭 전략에 수급 분석을 더하여 매매 신뢰도를 높이는 핵심 도구입니다. 기술적 분석과 수급 분석을 결합하면 더욱 정확한 매매 타이밍을 포착할 수 있습니다.