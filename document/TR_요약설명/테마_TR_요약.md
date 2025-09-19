# 테마_TR API 요약

## 개요
키움증권 REST API의 테마 관련 TR(Transaction Request) 코드들로, 시장에서 주목받는 테마별 종목 그룹화 정보와 각 테마의 성과 분석을 제공합니다. 전략 자동매매 시스템에서 섹터 로테이션 전략, 테마주 발굴, 시장 트렌드 분석에 활용할 수 있는 핵심 API 그룹입니다.

## 주요 API 구성

### 1. KA90001 - 테마그룹별요청
- **용도**: 전체 테마 목록 및 각 테마의 성과 조회
- **엔드포인트**: `/api/dostk/thme`
- **핵심 기능**:
  - 테마별 등락률 및 기간수익률 제공
  - 테마 내 상승/하락 종목 수 통계
  - 테마별 주요 대표 종목 정보
  - 다양한 검색 조건 (전체, 테마명, 종목코드 검색)

### 2. KA90002 - 테마구성종목요청  
- **용도**: 특정 테마를 구성하는 개별 종목 상세 정보 조회
- **엔드포인트**: `/api/dostk/thme`
- **핵심 기능**:
  - 테마별 구성 종목 전체 리스트
  - 개별 종목의 현재가, 등락률, 거래량 정보
  - 실시간 호가 정보 (매수/매도 호가 및 잔량)
  - 종목별 기간 수익률 분석

## 데이터 구조 및 활용 정보

### 테마 그룹 정보 (KA90001)
```json
{
    "thema_grp_cd": "100",        // 테마그룹코드
    "thema_nm": "전기차",          // 테마명
    "stk_num": "25",              // 구성종목수
    "flu_rt": "5.32",             // 테마 등락률
    "rising_stk_num": "18",       // 상승종목수
    "fall_stk_num": "7",          // 하락종목수
    "dt_prft_rt": "12.45",        // 기간수익률
    "main_stk": "삼성SDI"         // 주요종목
}
```

### 테마 구성종목 정보 (KA90002)
```json
{
    "stk_cd": "006400",           // 종목코드
    "stk_nm": "삼성SDI",          // 종목명
    "cur_prc": "425000",          // 현재가
    "flu_rt": "3.66",             // 등락률
    "acc_trde_qty": "125430",     // 누적거래량
    "sel_bid": "426000",          // 매도호가
    "buy_bid": "425000",          // 매수호가
    "dt_prft_rt_n": "15.23"       // 기간수익률
}
```

## 전략 시스템 통합 전략

### 1. 테마 기반 종목 발굴 시스템
```python
class ThemeBasedStockDiscovery:
    def __init__(self):
        self.hot_themes = []
        self.theme_performance = {}
        
    def discover_hot_themes(self, days=5):
        """핫 테마 발굴 및 성과 분석"""
        # 전체 테마 성과 조회
        theme_data = self.get_theme_groups({
            'qry_tp': '0',           # 전체검색
            'date_tp': str(days),    # N일 기간
            'flu_pl_amt_tp': '1',    # 상위기간수익률
            'stex_tp': '1'           # KRX
        })
        
        hot_themes = []
        for theme in theme_data['thema_grp']:
            # 전략에 적합한 테마 조건
            profit_rate = float(theme['dt_prft_rt'])
            rising_ratio = float(theme['rising_stk_num']) / float(theme['stk_num'])
            
            if self.is_tumepok_favorable_theme(profit_rate, rising_ratio, theme):
                hot_themes.append(theme)
        
        return sorted(hot_themes, key=lambda x: float(x['dt_prft_rt']), reverse=True)
    
    def is_tumepok_favorable_theme(self, profit_rate, rising_ratio, theme):
        """전략 전략에 유리한 테마 판단"""
        # 1. 기간 수익률 10% 이상
        if profit_rate < 10:
            return False
            
        # 2. 상승 종목 비율 60% 이상 (강한 테마)
        if rising_ratio < 0.6:
            return False
            
        # 3. 구성 종목 수 5개 이상 (충분한 선택권)
        if int(theme['stk_num']) < 5:
            return False
            
        # 4. 현재 등락률 5% 이상 (모멘텀 확인)
        if float(theme['flu_rt']) < 5:
            return False
            
        return True
```

### 2. 테마별 종목 선별 및 분석
```python
class ThemeStockAnalyzer:
    def __init__(self):
        self.tumepok_candidates = []
        
    def analyze_theme_stocks(self, theme_code, days=3):
        """테마 구성종목 중 전략 후보 선별"""
        # 테마 구성종목 상세 조회
        theme_stocks = self.get_theme_composition({
            'thema_grp_cd': theme_code,
            'date_tp': str(days),
            'stex_tp': '1'
        })
        
        candidates = []
        for stock in theme_stocks['thema_comp_stk']:
            analysis = self.analyze_individual_stock(stock)
            
            if analysis['tumepok_score'] >= 70:
                candidates.append({
                    'stock_info': stock,
                    'analysis': analysis,
                    'theme_code': theme_code
                })
        
        return sorted(candidates, key=lambda x: x['analysis']['tumepok_score'], reverse=True)
    
    def analyze_individual_stock(self, stock):
        """개별 종목 전략 적합성 분석"""
        current_price = float(stock['cur_prc'])
        profit_rate = float(stock['dt_prft_rt_n'])
        volume = float(stock['acc_trde_qty'])
        change_rate = float(stock['flu_rt'])
        
        tumepok_score = 0
        
        # 1. 가격대 조건 (1,000원 ~ 50,000원)
        if 1000 <= current_price <= 50000:
            tumepok_score += 20
        
        # 2. 기간 수익률 (20% 이상)
        if profit_rate >= 20:
            tumepok_score += 30
        elif profit_rate >= 15:
            tumepok_score += 20
        elif profit_rate >= 10:
            tumepok_score += 10
        
        # 3. 거래량 (활발한 거래)
        if volume >= 100000:  # 10만주 이상
            tumepok_score += 15
        elif volume >= 50000:
            tumepok_score += 10
        
        # 4. 현재 등락률 (적절한 상승)
        if 10 <= change_rate <= 25:  # 적정 상승 범위
            tumepok_score += 15
        elif change_rate > 25:  # 과열 구간
            tumepok_score += 5
        
        return {
            'tumepok_score': tumepok_score,
            'price_level': 'optimal' if 1000 <= current_price <= 50000 else 'suboptimal',
            'momentum': 'strong' if profit_rate >= 20 else 'moderate',
            'liquidity': 'high' if volume >= 100000 else 'medium'
        }
```

### 3. 테마 로테이션 전략
```python
class ThemeRotationStrategy:
    def __init__(self):
        self.theme_lifecycle = {}
        self.rotation_signals = []
        
    def analyze_theme_lifecycle(self, theme_codes, periods=[1, 3, 5, 10]):
        """테마별 생명주기 분석"""
        lifecycle_analysis = {}
        
        for theme_code in theme_codes:
            theme_data = {}
            
            for period in periods:
                period_data = self.get_theme_performance(theme_code, period)
                theme_data[f'{period}d'] = period_data
            
            lifecycle_analysis[theme_code] = self.determine_theme_phase(theme_data)
        
        return lifecycle_analysis
    
    def determine_theme_phase(self, theme_data):
        """테마 단계 판단 (발생기, 성장기, 성숙기, 쇠퇴기)"""
        profit_1d = float(theme_data['1d']['dt_prft_rt'])
        profit_3d = float(theme_data['3d']['dt_prft_rt'])
        profit_5d = float(theme_data['5d']['dt_prft_rt'])
        profit_10d = float(theme_data['10d']['dt_prft_rt'])
        
        # 모멘텀 분석
        momentum_3d = profit_3d - profit_1d
        momentum_5d = profit_5d - profit_3d
        momentum_10d = profit_10d - profit_5d
        
        if profit_1d > 5 and momentum_3d > 0 and momentum_5d > 0:
            return 'growth'      # 성장기 - 전략 진입 최적기
        elif profit_3d > 15 and momentum_3d > momentum_5d:
            return 'maturity'    # 성숙기 - 신중한 접근
        elif profit_10d > 20 and momentum_5d < 0:
            return 'decline'     # 쇠퇴기 - 회피
        else:
            return 'emergence'   # 발생기 - 관찰 대기
    
    def generate_rotation_signals(self, lifecycle_analysis):
        """테마 로테이션 신호 생성"""
        signals = []
        
        for theme_code, phase in lifecycle_analysis.items():
            if phase == 'growth':
                # 성장기 테마 - 적극 투자
                theme_stocks = self.analyze_theme_stocks(theme_code)
                top_candidates = theme_stocks[:3]  # 상위 3종목
                
                for candidate in top_candidates:
                    signals.append({
                        'action': 'BUY',
                        'theme_code': theme_code,
                        'stock_code': candidate['stock_info']['stk_cd'],
                        'priority': 'HIGH',
                        'reason': f'Growth phase theme with tumepok score: {candidate["analysis"]["tumepok_score"]}'
                    })
                    
            elif phase == 'maturity':
                # 성숙기 테마 - 선별적 투자
                signals.append({
                    'action': 'WATCH',
                    'theme_code': theme_code,
                    'priority': 'MEDIUM',
                    'reason': 'Maturity phase - selective investment'
                })
                
            elif phase == 'decline':
                # 쇠퇴기 테마 - 청산 고려
                signals.append({
                    'action': 'SELL',
                    'theme_code': theme_code,
                    'priority': 'HIGH',
                    'reason': 'Decline phase - consider exit'
                })
        
        return signals
```

### 4. 실시간 테마 모니터링
```python
class RealTimeThemeMonitor:
    def __init__(self):
        self.monitoring_themes = []
        self.theme_alerts = []
        
    def monitor_theme_performance(self):
        """실시간 테마 성과 모니터링"""
        for theme_code in self.monitoring_themes:
            # 최신 테마 성과 조회
            current_data = self.get_theme_current_status(theme_code)
            
            # 구성종목 변화 분석
            stock_changes = self.analyze_theme_stock_movements(theme_code)
            
            # 알람 조건 확인
            if self.check_alert_conditions(current_data, stock_changes):
                self.generate_theme_alert(theme_code, current_data, stock_changes)
    
    def check_alert_conditions(self, theme_data, stock_changes):
        """테마 알람 조건 확인"""
        # 1. 급격한 상승 (1일 10% 이상)
        if float(theme_data['flu_rt']) >= 10:
            return True
        
        # 2. 구성종목 80% 이상 상승
        rising_ratio = len([s for s in stock_changes if s['change'] > 0]) / len(stock_changes)
        if rising_ratio >= 0.8:
            return True
        
        # 3. 주요종목 급등 (20% 이상)
        main_stock_change = max([s['change_rate'] for s in stock_changes])
        if main_stock_change >= 20:
            return True
        
        return False
    
    def generate_theme_alert(self, theme_code, theme_data, stock_changes):
        """테마 알람 생성"""
        alert = {
            'timestamp': datetime.now(),
            'theme_code': theme_code,
            'theme_name': theme_data['thema_nm'],
            'alert_type': 'SURGE_DETECTED',
            'theme_change': theme_data['flu_rt'],
            'top_stocks': sorted(stock_changes, key=lambda x: x['change_rate'], reverse=True)[:5],
            'action_required': 'IMMEDIATE_ANALYSIS'
        }
        
        self.theme_alerts.append(alert)
        self.notify_alert(alert)
```

### 5. 테마 기반 포트폴리오 관리
```python
class ThemePortfolioManager:
    def __init__(self):
        self.theme_positions = {}
        self.max_theme_allocation = 0.3  # 단일 테마 최대 30%
        
    def optimize_theme_allocation(self, available_capital):
        """테마별 최적 자본 배분"""
        # 현재 핫 테마 분석
        hot_themes = self.discover_hot_themes()
        
        # 테마별 할당 비중 계산
        allocation_plan = {}
        total_score = sum([self.calculate_theme_score(theme) for theme in hot_themes])
        
        for theme in hot_themes[:5]:  # 상위 5개 테마
            theme_score = self.calculate_theme_score(theme)
            allocation_ratio = min(theme_score / total_score, self.max_theme_allocation)
            
            allocation_plan[theme['thema_grp_cd']] = {
                'theme_name': theme['thema_nm'],
                'allocation_ratio': allocation_ratio,
                'allocated_capital': available_capital * allocation_ratio,
                'target_stocks': self.select_theme_stocks(theme['thema_grp_cd'])
            }
        
        return allocation_plan
    
    def calculate_theme_score(self, theme):
        """테마 점수 계산"""
        profit_rate = float(theme['dt_prft_rt'])
        rising_ratio = float(theme['rising_stk_num']) / float(theme['stk_num'])
        momentum = float(theme['flu_rt'])
        
        score = (profit_rate * 0.4 + rising_ratio * 100 * 0.3 + momentum * 0.3)
        return max(score, 0)
    
    def rebalance_theme_portfolio(self):
        """테마 포트폴리오 리밸런싱"""
        # 현재 포지션 평가
        current_performance = self.evaluate_current_positions()
        
        # 신규 테마 기회 분석
        new_opportunities = self.discover_hot_themes()
        
        rebalance_actions = []
        
        # 수익률 저조 테마 청산
        for theme_code, position in self.theme_positions.items():
            if position['profit_rate'] < -5:  # -5% 이하
                rebalance_actions.append({
                    'action': 'LIQUIDATE',
                    'theme_code': theme_code,
                    'reason': 'Poor performance'
                })
        
        # 신규 유망 테마 편입
        for theme in new_opportunities[:3]:
            if theme['thema_grp_cd'] not in self.theme_positions:
                rebalance_actions.append({
                    'action': 'ENTER',
                    'theme_code': theme['thema_grp_cd'],
                    'reason': f'New opportunity with {theme["dt_prft_rt"]}% return'
                })
        
        return rebalance_actions
```

## 실전 활용 시나리오

### 1. 일일 테마 스캐닝
```python
def daily_theme_scanning():
    """일일 테마 스캐닝 루틴"""
    
    # 1. 전체 테마 성과 조회 (최근 3일)
    hot_themes = get_theme_groups({
        'qry_tp': '0',
        'date_tp': '3',
        'flu_pl_amt_tp': '1',  # 상위수익률 우선
        'stex_tp': '1'
    })
    
    # 2. 상위 테마별 구성종목 분석
    for theme in hot_themes[:10]:  # 상위 10개 테마
        theme_stocks = analyze_theme_stocks(theme['thema_grp_cd'])
        
        # 3. 전략 후보 종목 선별
        for candidate in theme_stocks:
            if candidate['analysis']['tumepok_score'] >= 80:
                add_to_watchlist(candidate)
```

### 2. 테마 기반 전략 전략
```python
def theme_based_tumepok_strategy():
    """테마 기반 전략 전략 실행"""
    
    # 1. 성장기 테마 식별
    growth_themes = identify_growth_phase_themes()
    
    # 2. 각 테마별 최고 종목 선별
    for theme in growth_themes:
        best_stocks = select_best_theme_stocks(theme['thema_grp_cd'])
        
        # 3. 급등 후 하락 패턴 모니터링
        for stock in best_stocks:
            if stock['profit_rate'] >= 20:  # 20% 이상 상승
                start_drop_monitoring(stock['stk_cd'], theme['thema_grp_cd'])
```

## 성능 최적화 및 활용 팁

### 1. API 호출 최적화
- 테마 데이터는 일 1-2회 갱신으로 충분 (캐싱 활용)
- 구성종목 데이터는 실시간성이 중요 (자주 갱신)
- 대량 테마 조회 시 연속조회 기능 활용

### 2. 데이터 분석 최적화
- 테마별 성과 히스토리 DB 구축
- 종목별 테마 참여 이력 추적
- 테마 생명주기 패턴 학습

### 3. 리스크 관리
- 단일 테마 집중투자 위험 방지
- 테마 버블 구간 식별 로직 구현
- 테마 쇠퇴기 조기 감지 시스템

## 결론

테마_TR API 그룹은 전략 자동매매 시스템에서 섹터별 투자 기회 발굴과 시장 트렌드 분석의 핵심 도구입니다. KA90001을 통한 전체 테마 성과 분석과 KA90002를 통한 개별 종목 선별을 조합하여, 테마 기반 종목 발굴부터 포트폴리오 관리까지 체계적인 투자 전략을 구축할 수 있습니다. 특히 급등하는 테마 내에서 전략 조건에 부합하는 종목을 선별하는 것이 수익률 극대화의 핵심입니다.