# 차트_TR API 요약

## 개요
키움증권 REST API의 차트 데이터 관련 TR(Transaction Request) 코드들로, 주식 및 업종의 시계열 데이터를 다양한 시간 단위로 제공합니다. 전략 자동매매 시스템에서 기술적 분석, 패턴 인식, 트렌드 분석 등 전략적 판단의 핵심 데이터를 제공하는 API 그룹입니다.

## 주요 API 카테고리

### 1. 주식 차트 데이터 (시간별)
- **ka10079 - 주식틱차트조회요청**: 1틱~30틱 단위 실시간 차트 데이터
- **ka10080 - 주식분봉차트조회요청**: 1분~60분 단위 분봉 차트 데이터
- **ka10081 - 주식일봉차트조회요청**: 일봉 차트 데이터 (기준일자 기반)
- **ka10082 - 주식주봉차트조회요청**: 주봉 차트 데이터
- **ka10083 - 주식월봉차트조회요청**: 월봉 차트 데이터
- **ka10094 - 주식년봉차트조회요청**: 년봉 차트 데이터

### 2. 거래량 포함 고급 차트
- **ka10094 - 분봉차트요청(거래량포함)**: 거래량과 거래대금이 포함된 분봉 데이터
- **ka10083 - 틱차트요청**: 실시간 틱 차트 데이터

### 3. 업종 차트 데이터
- **ka20004 - 업종틱차트조회요청**: 업종별 틱 차트 (KOSPI, KOSDAQ 등)
- **ka20005 - 업종분봉조회요청**: 업종별 분봉 차트
- **ka20006 - 업종일봉조회요청**: 업종별 일봉 차트
- **ka20007 - 업종주봉조회요청**: 업종별 주봉 차트
- **ka20008 - 업종월봉조회요청**: 업종별 월봉 차트
- **ka20019 - 업종년봉조회요청**: 업종별 년봉 차트

### 4. 투자자별 매매 차트
- **ka10060 - 종목별투자자기관별차트요청**: 일별 투자자별 매매 현황 차트
- **ka10064 - 장중투자자별매매차트요청**: 실시간 투자자별 매매 흐름

## 차트 데이터 구조

### 기본 OHLCV 데이터
모든 차트 API는 다음과 같은 기본 구조를 제공합니다:
- **open_pric**: 시가
- **high_pric**: 고가  
- **low_pric**: 저가
- **cur_prc**: 종가 (현재가)
- **trde_qty**: 거래량
- **trde_prica**: 거래대금 (일부 API)
- **cntr_tm/dt**: 체결시간/일자

### 수정주가 처리
- **upd_stkpc_tp**: 수정주가 구분 (0 또는 1)
- **upd_rt**: 수정 비율
- **수정 이벤트**: 유상증자, 무상증자, 배당락, 액면분할 등 처리

## 전략 시스템 통합 전략

### 1. 멀티 타임프레임 분석 시스템
```python
class MultiTimeFrameAnalyzer:
    def __init__(self):
        self.timeframes = {
            'tick': {'api': 'ka10079', 'scope': '1'},     # 1틱
            '1m': {'api': 'ka10080', 'scope': '1'},       # 1분
            '5m': {'api': 'ka10080', 'scope': '5'},       # 5분
            '15m': {'api': 'ka10080', 'scope': '15'},     # 15분
            '1h': {'api': 'ka10080', 'scope': '60'},      # 1시간
            '1d': {'api': 'ka10081', 'base_dt': 'today'} # 일봉
        }
    
    def analyze_tumepok_pattern(self, stock_code):
        """전략 패턴 분석을 위한 멀티 타임프레임 데이터 수집"""
        chart_data = {}
        
        for tf, config in self.timeframes.items():
            if config['api'] == 'ka10081':  # 일봉
                data = self.get_daily_chart(stock_code)
            else:  # 틱, 분봉
                data = self.get_intraday_chart(stock_code, config)
            
            chart_data[tf] = self.process_chart_data(data)
        
        return self.identify_tumepok_signals(chart_data)
    
    def identify_tumepok_signals(self, chart_data):
        """전략 신호 식별"""
        signals = {
            'surge_confirmation': self.check_surge_pattern(chart_data['1d'], chart_data['1h']),
            'drop_analysis': self.analyze_drop_pattern(chart_data['15m'], chart_data['5m']),
            'support_levels': self.find_support_levels(chart_data['1d'], chart_data['1h']),
            'volume_pattern': self.analyze_volume_pattern(chart_data)
        }
        
        return signals
```

### 2. 실시간 차트 모니터링 시스템
```python
class RealTimeChartMonitor:
    def __init__(self):
        self.tracking_stocks = {}
        self.chart_buffer = {}
    
    def monitor_tracking_stocks(self):
        """추적 중인 종목들의 실시간 차트 모니터링"""
        for stock_code in self.tracking_stocks:
            # 틱 차트로 실시간 모니터링
            tick_data = self.get_tick_chart(stock_code)
            
            # 5분봉으로 단기 트렌드 확인
            min5_data = self.get_minute_chart(stock_code, 5)
            
            # 전략 진입 조건 확인
            if self.check_entry_conditions(stock_code, tick_data, min5_data):
                self.generate_buy_signal(stock_code)
    
    def check_entry_conditions(self, stock_code, tick_data, min5_data):
        """실시간 진입 조건 확인"""
        # 1. 하락률 확인
        tracking_info = self.tracking_stocks[stock_code]
        current_price = float(tick_data[-1]['cur_prc'])
        high_price = tracking_info['high_price']
        drop_rate = ((high_price - current_price) / high_price) * 100
        
        # 2. 전략 매트릭스 조건 확인
        required_drop = self.get_required_drop_rate(tracking_info['rise_rate'])
        if drop_rate < required_drop['min'] or drop_rate > required_drop['max']:
            return False
        
        # 3. 지지선 터치 확인
        support_level = self.calculate_support_level(min5_data)
        if current_price <= support_level * 1.01:  # 1% 허용 오차
            return True
        
        # 4. 거래량 건조 확인
        recent_volume = sum([float(d['trde_qty']) for d in tick_data[-10:]])
        avg_volume = tracking_info['avg_volume']
        if recent_volume <= avg_volume * 0.25:  # 평균의 25% 이하
            return True
        
        return False
```

### 3. 패턴 인식 및 기술적 분석
```python
class TechnicalAnalyzer:
    def __init__(self):
        self.indicators = {}
    
    def analyze_stock_pattern(self, stock_code):
        """종목별 기술적 패턴 분석"""
        # 일봉 데이터로 중장기 트렌드 분석
        daily_data = self.get_daily_chart_data(stock_code, days=60)
        
        # 분봉 데이터로 단기 패턴 분석
        minute_data = self.get_minute_chart_data(stock_code, minutes=240)  # 4시간
        
        analysis = {
            'trend_analysis': self.analyze_trend(daily_data),
            'support_resistance': self.find_support_resistance(daily_data, minute_data),
            'rsi_analysis': self.calculate_rsi(daily_data, minute_data),
            'volume_analysis': self.analyze_volume_pattern(daily_data, minute_data),
            'candlestick_patterns': self.identify_candlestick_patterns(minute_data)
        }
        
        return analysis
    
    def calculate_rsi(self, daily_data, minute_data):
        """RSI 계산 (일봉, 분봉)"""
        daily_rsi = self.rsi_calculation(daily_data, period=14)
        minute_rsi = self.rsi_calculation(minute_data, period=14)
        
        return {
            'daily_rsi': daily_rsi,
            'minute_rsi': minute_rsi,
            'oversold_signal': daily_rsi <= 30 and minute_rsi <= 30,
            'divergence': self.check_rsi_divergence(daily_data, daily_rsi)
        }
    
    def find_support_resistance(self, daily_data, minute_data):
        """지지선/저항선 식별"""
        # 일봉에서 주요 지지/저항선 식별
        major_levels = self.find_major_levels(daily_data)
        
        # 분봉에서 단기 지지/저항선 식별
        minor_levels = self.find_minor_levels(minute_data)
        
        return {
            'major_support': major_levels['support'],
            'major_resistance': major_levels['resistance'],
            'minor_support': minor_levels['support'],
            'minor_resistance': minor_levels['resistance'],
            'current_position': self.analyze_current_position(daily_data[-1], major_levels)
        }
```

### 4. 업종 분석 및 섹터 로테이션
```python
class SectorAnalyzer:
    def __init__(self):
        self.sector_codes = {
            'KOSPI': '001',
            'KOSDAQ': '101', 
            'KOSPI200': '201',
            'KRX100': '701'
        }
    
    def analyze_market_trend(self):
        """시장 전체 트렌드 분석"""
        market_analysis = {}
        
        for sector_name, sector_code in self.sector_codes.items():
            # 업종별 일봉 데이터
            daily_data = self.get_sector_daily_chart(sector_code)
            
            # 업종별 분봉 데이터 (실시간 동향)
            minute_data = self.get_sector_minute_chart(sector_code)
            
            market_analysis[sector_name] = {
                'trend': self.calculate_trend_strength(daily_data),
                'momentum': self.calculate_momentum(minute_data),
                'relative_strength': self.calculate_relative_strength(daily_data)
            }
        
        return self.determine_favorable_sectors(market_analysis)
    
    def determine_favorable_sectors(self, analysis):
        """전략 전략에 유리한 섹터 판단"""
        favorable_sectors = []
        
        for sector, data in analysis.items():
            # 상승 모멘텀이 강하고 변동성이 큰 섹터 선호
            if (data['momentum'] > 0.5 and 
                data['trend'] > 0.3 and 
                data['relative_strength'] > 1.1):
                favorable_sectors.append(sector)
        
        return favorable_sectors
```

### 5. 투자자별 매매 흐름 분석
```python
class InvestorFlowAnalyzer:
    def __init__(self):
        self.investor_types = [
            'frgnr_invsr',   # 외국인
            'orgn',          # 기관
            'invtrt',        # 투신
            'insrnc',        # 보험
            'bank'           # 은행
        ]
    
    def analyze_investor_flow(self, stock_code, days=5):
        """투자자별 매매 흐름 분석"""
        # 일별 투자자 매매 현황
        daily_flow = self.get_investor_daily_chart(stock_code, days)
        
        # 장중 투자자 매매 현황 (실시간)
        intraday_flow = self.get_investor_intraday_chart(stock_code)
        
        analysis = {
            'trend_analysis': self.analyze_flow_trends(daily_flow),
            'net_buying_pressure': self.calculate_net_buying(daily_flow, intraday_flow),
            'smart_money_flow': self.identify_smart_money(daily_flow),
            'retail_sentiment': self.analyze_retail_sentiment(daily_flow)
        }
        
        return analysis
    
    def identify_smart_money(self, daily_flow):
        """스마트머니 (외국인, 기관) 흐름 분석"""
        smart_money_net = []
        
        for data in daily_flow:
            foreign_net = float(data.get('frgnr_invsr', 0))
            institution_net = float(data.get('orgn', 0))
            total_smart = foreign_net + institution_net
            smart_money_net.append(total_smart)
        
        return {
            'net_position': sum(smart_money_net),
            'trend': 'buying' if sum(smart_money_net[-3:]) > 0 else 'selling',
            'intensity': abs(sum(smart_money_net)) / len(smart_money_net)
        }
```

## 전략 특화 차트 활용 시나리오

### 1. 급등 종목 발굴 후 차트 분석 파이프라인
```python
def tumepok_chart_analysis_pipeline(stock_code):
    """전략 종목 차트 분석 파이프라인"""
    
    # 1단계: 기본 차트 패턴 확인
    daily_chart = get_daily_chart(stock_code, days=20)
    rise_days = count_consecutive_rise_days(daily_chart)
    rise_rate = calculate_rise_rate(daily_chart)
    
    # 2단계: 실시간 하락 모니터링 설정
    if rise_rate >= 20 and rise_days <= 4:
        setup_realtime_monitoring(stock_code, daily_chart)
        
    # 3단계: 지지선 분석
    support_levels = identify_support_levels(daily_chart)
    minute_chart = get_minute_chart(stock_code, minutes=60)
    current_support = find_nearest_support(minute_chart, support_levels)
    
    # 4단계: 투자자 흐름 확인
    investor_flow = analyze_investor_flow(stock_code)
    
    return {
        'tumepok_score': calculate_tumepok_score(rise_rate, rise_days, support_levels),
        'entry_price_range': calculate_entry_range(current_support, rise_rate),
        'risk_level': assess_risk_level(investor_flow, rise_days)
    }
```

### 2. 실시간 하락 추적 및 매수 타이밍
```python
def monitor_drop_and_entry_timing(stock_code):
    """실시간 하락 추적 및 매수 타이밍 포착"""
    
    while True:  # 실시간 루프
        # 틱 데이터로 즉시 반영되는 가격 변화 추적
        current_tick = get_latest_tick(stock_code)
        current_price = float(current_tick['cur_prc'])
        
        # 5분봉으로 단기 트렌드 확인
        recent_5min = get_recent_minute_chart(stock_code, 5, count=12)  # 1시간
        
        # 하락률 계산 및 전략 조건 확인
        drop_rate = calculate_current_drop_rate(stock_code, current_price)
        entry_condition = check_tumepok_entry_condition(drop_rate, recent_5min)
        
        if entry_condition:
            # 3단계 매수 시퀀스 실행
            execute_tumepok_buy_sequence(stock_code, drop_rate, current_price)
            break
        
        time.sleep(1)  # 1초 간격 모니터링
```

## 성능 최적화 및 데이터 관리

### 1. 차트 데이터 캐싱 전략
```python
class ChartDataCache:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = {
            'tick': 0,      # 캐싱 없음 (실시간)
            'minute': 60,   # 1분 캐싱
            'daily': 3600,  # 1시간 캐싱
            'weekly': 86400 # 1일 캐싱
        }
    
    def get_cached_data(self, api_key, params, data_type):
        """캐시된 차트 데이터 조회"""
        cache_key = f"{api_key}_{hash(str(params))}"
        
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_ttl[data_type]:
                return data
        
        # 캐시 미스 시 API 호출
        fresh_data = self.call_chart_api(api_key, params)
        self.cache[cache_key] = (time.time(), fresh_data)
        
        return fresh_data
```

### 2. 대용량 차트 데이터 처리
```python
def process_large_chart_data(stock_code, days=252):  # 1년 데이터
    """대용량 차트 데이터 효율적 처리"""
    
    batch_size = 50  # 50일씩 배치 처리
    all_data = []
    
    for i in range(0, days, batch_size):
        end_date = get_trading_date_offset(-i)
        start_date = get_trading_date_offset(-(i + batch_size))
        
        batch_data = get_daily_chart_range(stock_code, start_date, end_date)
        all_data.extend(batch_data)
        
        time.sleep(0.1)  # API 호출 제한 준수
    
    return process_and_optimize_data(all_data)
```

### 3. 실시간 데이터 스트리밍
```python
async def stream_chart_data(stock_codes):
    """다중 종목 실시간 차트 데이터 스트리밍"""
    
    tasks = []
    for stock_code in stock_codes:
        task = asyncio.create_task(stream_single_stock(stock_code))
        tasks.append(task)
    
    await asyncio.gather(*tasks)

async def stream_single_stock(stock_code):
    """단일 종목 실시간 데이터 스트림"""
    while True:
        try:
            tick_data = await get_tick_data_async(stock_code)
            await process_realtime_data(stock_code, tick_data)
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"스트리밍 오류 {stock_code}: {e}")
            await asyncio.sleep(5)  # 오류 시 5초 대기
```

## 결론

차트_TR API 그룹은 전략 자동매매 시스템의 분석 엔진으로, 다양한 시간 단위의 차트 데이터를 통해 정교한 기술적 분석과 패턴 인식을 가능하게 합니다. 특히 실시간 틱/분봉 데이터(ka10079, ka10080)를 활용한 정밀한 진입 타이밍 포착과, 일봉 데이터(ka10081)를 통한 중장기 트렌드 분석이 전략 전략 성공의 핵심입니다. 투자자별 매매 흐름 분석(ka10060, ka10064)과 업종 차트 분석(ka20xxx 시리즈)을 통합하여 종합적인 시장 분석 시스템을 구축할 수 있습니다.