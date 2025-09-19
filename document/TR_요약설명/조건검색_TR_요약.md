# 조건검색_TR API 요약

## 개요

조건검색_TR 폴더는 키움증권 REST API의 조건검색 기능을 포함합니다. 이 API들은 사전에 설정된 조건식을 통해 자동으로 종목을 검색하고 실시간으로 모니터링하는 기능을 제공하여, 전략(tumepok) 자동매매 시스템에서 체계적인 종목 발굴과 신호 감지에 핵심적인 역할을 합니다.

## WebSocket 기반 조건검색 시스템

### 연결 정보
- **실전 URL**: `wss://api.kiwoom.com:10000/api/dostk/websocket`
- **모의 URL**: `wss://mockapi.kiwoom.com:10000/api/dostk/websocket`
- **인증**: Bearer 토큰 필요
- **프로토콜**: JSON 메시지 기반 비동기 통신

### 조건검색 프로세스
1. **조건검색 목록 조회** (ka10171) → 등록된 조건식 확인
2. **일반 조건검색 실행** (ka10172) → 1회성 검색 수행
3. **실시간 조건검색 실행** (ka10173) → 지속적 모니터링 시작
4. **실시간 조건검색 해제** (ka10174) → 모니터링 중단

## 주요 API 분류

### 1. ka10171 - 조건검색 목록조회 (CNSRLST)

#### 기본 정보
- **목적**: 등록된 조건검색식 목록 조회
- **WebSocket 서비스명**: CNSRLST
- **전략 활용**: 사용 가능한 조건식 확인, 전략별 조건식 매핑

#### 요청 구조
```python
{
    'trnm': 'CNSRLST'  # 고정값
}
```

#### 응답 구조
```python
{
    'return_code': 0,         # 결과코드 (정상: 0)
    'return_msg': '',         # 결과메시지
    'trnm': 'CNSRLST',       # 서비스명
    'data': [                # 조건검색식 목록
        {
            'seq': '1',       # 조건검색식 일련번호
            'name': '급등주발굴조건'  # 조건검색식명
        }
    ]
}
```

#### 전략 활용 예시
```python
class TumepokConditionManager:
    def __init__(self, websocket_client):
        self.ws_client = websocket_client
        self.condition_map = {}
        
    async def load_condition_list(self):
        """조건검색 목록 로드"""
        await self.ws_client.send_message({'trnm': 'CNSRLST'})
        
        # 응답 대기 및 처리
        response = await self.wait_for_response('CNSRLST')
        
        if response['return_code'] == 0:
            for condition in response['data']:
                self.condition_map[condition['seq']] = {
                    'name': condition['name'],
                    'active': False,
                    'last_results': []
                }
            
            return self.condition_map
        else:
            raise Exception(f"조건검색 목록 조회 실패: {response['return_msg']}")
    
    def get_tumepok_conditions(self):
        """전략 관련 조건식 필터링"""
        tumepok_conditions = {}
        
        for seq, info in self.condition_map.items():
            name = info['name'].lower()
            
            # 전략 관련 키워드로 필터링
            if any(keyword in name for keyword in ['급등', '돌파', '상승', '볼륨', '전략']):
                tumepok_conditions[seq] = info
        
        return tumepok_conditions
```

### 2. ka10172 - 조건검색 요청 일반 (CNSRREQ - 일회성)

#### 기본 정보
- **목적**: 조건검색식을 이용한 일회성 검색
- **WebSocket 서비스명**: CNSRREQ
- **search_type**: 0 (조건검색)
- **전략 활용**: 장 시작 전 후보주 선별, 주기적 스캔

#### 요청 구조
```python
{
    'trnm': 'CNSRREQ',        # 서비스명 고정값
    'seq': '4',               # 조건검색식 일련번호
    'search_type': '0',       # 조회타입 (0: 조건검색)
    'stex_tp': 'K',          # 거래소구분 (K: KRX)
    'cont_yn': 'N',          # 연속조회여부
    'next_key': ''           # 연속조회키
}
```

#### 응답 구조
```python
{
    'return_code': 0,
    'return_msg': '',
    'trnm': 'CNSRREQ',
    'seq': '4',
    'cont_yn': 'N',
    'next_key': '',
    'data': [
        {
            '9001': '005930',    # 종목코드
            '302': '삼성전자',   # 종목명
            '10': '82000',       # 현재가
            '25': '2',           # 전일대비기호
            '11': '1500',        # 전일대비
            '12': '1.86',        # 등락율
            '13': '1234567',     # 누적거래량
            '16': '81000',       # 시가
            '17': '82500',       # 고가
            '18': '80500'        # 저가
        }
    ]
}
```

#### 전략 활용 예시
```python
async def scan_condition_stocks(self, condition_seq):
    """조건검색으로 종목 스캔"""
    
    request = {
        'trnm': 'CNSRREQ',
        'seq': condition_seq,
        'search_type': '0',
        'stex_tp': 'K',
        'cont_yn': 'N',
        'next_key': ''
    }
    
    await self.ws_client.send_message(request)
    response = await self.wait_for_response('CNSRREQ')
    
    if response['return_code'] == 0:
        candidates = []
        
        for stock_data in response['data']:
            stock_info = {
                'code': stock_data['9001'],
                'name': stock_data['302'],
                'current_price': float(stock_data['10']),
                'change_rate': float(stock_data['12']),
                'volume': int(stock_data['13']),
                'high_price': float(stock_data['17']),
                'low_price': float(stock_data['18'])
            }
            
            # 전략 조건 확인
            if self.check_tumepok_criteria(stock_info):
                candidates.append(stock_info)
        
        return candidates
    
    return []

def check_tumepok_criteria(self, stock_info):
    """전략 기준 확인"""
    return (
        stock_info['change_rate'] >= 20.0 and      # 20% 이상 상승
        stock_info['volume'] >= 100000 and         # 10만주 이상 거래
        stock_info['current_price'] >= 1000 and    # 1000원 이상
        stock_info['current_price'] <= 50000       # 5만원 이하
    )
```

### 3. ka10173 - 조건검색 요청 실시간 (CNSRREQ - 실시간)

#### 기본 정보
- **목적**: 조건검색식을 이용한 실시간 조건검색
- **WebSocket 서비스명**: CNSRREQ
- **search_type**: 1 (조건검색 + 실시간 조건검색)
- **전략 활용**: 실시간 급등주 포착, 조건 만족 시점 즉시 알림

#### 요청 구조
```python
{
    'trnm': 'CNSRREQ',        # 서비스명 고정값
    'seq': '4',               # 조건검색식 일련번호
    'search_type': '1',       # 조회타입 (1: 조건검색 + 실시간)
    'stex_tp': 'K'           # 거래소구분 (K: KRX)
}
```

#### 실시간 응답 구조
```python
{
    'trnm': 'REAL',           # 실시간 데이터
    'data': [
        {
            'type': '',           # 실시간 항목
            'name': '005930',     # 종목코드
            'values': {
                '841': '',        # 신호종류
                '9001': '005930', # 종목코드
                '843': '',        # 삽입삭제 구분
                '20': '153000',   # 체결시간
                '907': ''         # 매도/수 구분
            }
        }
    ]
}
```

#### 전략 활용 예시
```python
class RealTimeConditionMonitor:
    def __init__(self, websocket_client):
        self.ws_client = websocket_client
        self.active_conditions = {}
        self.signal_handlers = {}
        
    async def start_realtime_monitoring(self, condition_seq):
        """실시간 조건검색 시작"""
        
        request = {
            'trnm': 'CNSRREQ',
            'seq': condition_seq,
            'search_type': '1',
            'stex_tp': 'K'
        }
        
        await self.ws_client.send_message(request)
        
        # 초기 검색 결과 처리
        initial_response = await self.wait_for_response('CNSRREQ')
        if initial_response['return_code'] == 0:
            self.active_conditions[condition_seq] = {
                'status': 'ACTIVE',
                'initial_stocks': [data['jmcode'] for data in initial_response['data']]
            }
            
            print(f"조건검색 {condition_seq} 실시간 모니터링 시작")
            print(f"초기 조건 만족 종목: {len(initial_response['data'])}개")
        
    async def handle_realtime_signal(self, response):
        """실시간 조건검색 신호 처리"""
        
        if response.get('trnm') == 'REAL':
            for data in response['data']:
                stock_code = data['name']
                values = data['values']
                
                signal_type = values.get('841')  # 신호종류
                insert_delete = values.get('843')  # 삽입삭제구분
                execution_time = values.get('20')  # 체결시간
                
                # 조건 진입 신호
                if insert_delete == 'I':  # Insert (조건 만족)
                    await self.handle_condition_entry(stock_code, execution_time)
                
                # 조건 이탈 신호
                elif insert_delete == 'D':  # Delete (조건 이탈)
                    await self.handle_condition_exit(stock_code, execution_time)
    
    async def handle_condition_entry(self, stock_code, execution_time):
        """조건 진입 처리"""
        
        print(f"조건 진입: {stock_code} at {execution_time}")
        
        # 종목 정보 조회
        stock_info = await self.get_stock_info(stock_code)
        
        # 전략 후보로 등록
        if self.validate_tumepok_candidate(stock_info):
            await self.add_tracking_stock(stock_code, stock_info)
            
            # 즉시 매수 신호 생성 (조건에 따라)
            if self.check_immediate_buy_condition(stock_info):
                await self.generate_buy_signal(stock_code, stock_info)
    
    async def handle_condition_exit(self, stock_code, execution_time):
        """조건 이탈 처리"""
        
        print(f"조건 이탈: {stock_code} at {execution_time}")
        
        # 추적 중인 종목인지 확인
        if self.is_tracking_stock(stock_code):
            # 조건 이탈 시 매도 신호 고려
            await self.consider_sell_signal(stock_code)
```

### 4. ka10174 - 조건검색 실시간 해제 (CNSRCLR)

#### 기본 정보
- **목적**: 실행 중인 실시간 조건검색 해제
- **WebSocket 서비스명**: CNSRCLR
- **전략 활용**: 모니터링 종료, 리소스 관리

#### 요청 구조
```python
{
    'trnm': 'CNSRCLR',        # 서비스명 고정값
    'seq': '1'                # 조건검색식 일련번호
}
```

#### 응답 구조
```python
{
    'return_code': 0,         # 결과코드 (정상: 0)
    'return_msg': '',         # 결과메시지
    'trnm': 'CNSRCLR',       # 서비스명
    'seq': '1'               # 조건검색식 일련번호
}
```

#### 전략 활용 예시
```python
async def stop_realtime_monitoring(self, condition_seq):
    """실시간 조건검색 중지"""
    
    request = {
        'trnm': 'CNSRCLR',
        'seq': condition_seq
    }
    
    await self.ws_client.send_message(request)
    response = await self.wait_for_response('CNSRCLR')
    
    if response['return_code'] == 0:
        if condition_seq in self.active_conditions:
            self.active_conditions[condition_seq]['status'] = 'STOPPED'
            print(f"조건검색 {condition_seq} 모니터링 중지됨")
        return True
    else:
        print(f"조건검색 중지 실패: {response['return_msg']}")
        return False

async def cleanup_all_conditions(self):
    """모든 실시간 조건검색 정리"""
    
    cleanup_tasks = []
    for seq in list(self.active_conditions.keys()):
        if self.active_conditions[seq]['status'] == 'ACTIVE':
            cleanup_tasks.append(self.stop_realtime_monitoring(seq))
    
    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks)
        print("모든 실시간 조건검색이 정리되었습니다.")
```

## 전략 시스템 통합 전략

### 1. 통합 조건검색 관리 시스템

```python
class TumepokConditionSearchSystem:
    def __init__(self, websocket_client):
        self.ws_client = websocket_client
        self.condition_manager = TumepokConditionManager(websocket_client)
        self.realtime_monitor = RealTimeConditionMonitor(websocket_client)
        self.tumepok_strategy = TumepokStrategy()
        
    async def initialize(self):
        """시스템 초기화"""
        
        # 1. 조건검색 목록 로드
        await self.condition_manager.load_condition_list()
        
        # 2. 전략 관련 조건식 식별
        tumepok_conditions = self.condition_manager.get_tumepok_conditions()
        
        # 3. 주요 조건식들 실시간 모니터링 시작
        for seq, info in tumepok_conditions.items():
            if self.is_high_priority_condition(info['name']):
                await self.realtime_monitor.start_realtime_monitoring(seq)
        
        print(f"전략 조건검색 시스템 초기화 완료")
        print(f"모니터링 중인 조건: {len(tumepok_conditions)}개")
    
    def is_high_priority_condition(self, condition_name):
        """고우선순위 조건 판별"""
        high_priority_keywords = [
            '급등', '20%상승', '돌파', '볼륨급증', 
            '전략', '상승돌파', '가격급등'
        ]
        
        return any(keyword in condition_name for keyword in high_priority_keywords)
    
    async def periodic_scan(self):
        """주기적 조건검색 스캔"""
        
        while True:
            try:
                # 모든 전략 관련 조건으로 스캔
                tumepok_conditions = self.condition_manager.get_tumepok_conditions()
                
                scan_results = {}
                for seq in tumepok_conditions.keys():
                    candidates = await self.condition_manager.scan_condition_stocks(seq)
                    scan_results[seq] = candidates
                
                # 결과 분석 및 처리
                await self.process_scan_results(scan_results)
                
                # 30분마다 스캔
                await asyncio.sleep(1800)
                
            except Exception as e:
                print(f"주기적 스캔 오류: {e}")
                await asyncio.sleep(300)  # 5분 후 재시도
```

### 2. 조건검색 기반 신호 생성

```python
class ConditionBasedSignalGenerator:
    def __init__(self):
        self.signal_weights = {
            'condition_entry': 0.4,      # 조건 진입 신호
            'volume_surge': 0.3,         # 거래량 급증
            'price_momentum': 0.2,       # 가격 모멘텀
            'technical_pattern': 0.1     # 기술적 패턴
        }
    
    async def generate_comprehensive_signal(self, stock_code, trigger_condition):
        """종합 신호 생성"""
        
        signals = {}
        
        # 1. 조건 진입 신호 점수
        signals['condition_entry'] = self.calculate_condition_score(trigger_condition)
        
        # 2. 거래량 급증 확인
        signals['volume_surge'] = await self.check_volume_surge(stock_code)
        
        # 3. 가격 모멘텀 분석
        signals['price_momentum'] = await self.analyze_price_momentum(stock_code)
        
        # 4. 기술적 패턴 확인
        signals['technical_pattern'] = await self.check_technical_patterns(stock_code)
        
        # 가중 평균 점수 계산
        total_score = sum(
            signals[key] * self.signal_weights[key] 
            for key in signals.keys()
        )
        
        return {
            'stock_code': stock_code,
            'total_score': total_score,
            'individual_signals': signals,
            'recommendation': self.get_recommendation(total_score),
            'trigger_condition': trigger_condition
        }
    
    def get_recommendation(self, score):
        """점수 기반 추천"""
        if score >= 80:
            return "STRONG_BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 40:
            return "WATCH"
        else:
            return "IGNORE"
```

### 3. 조건검색 성과 분석

```python
class ConditionPerformanceAnalyzer:
    def __init__(self):
        self.condition_history = {}
        self.performance_metrics = {}
    
    def track_condition_signal(self, condition_seq, stock_code, signal_time, signal_type):
        """조건검색 신호 추적"""
        
        if condition_seq not in self.condition_history:
            self.condition_history[condition_seq] = []
        
        self.condition_history[condition_seq].append({
            'stock_code': stock_code,
            'signal_time': signal_time,
            'signal_type': signal_type,  # 'ENTRY' or 'EXIT'
            'price_at_signal': None,     # 나중에 업데이트
            'outcome': None              # 나중에 업데이트
        })
    
    async def analyze_condition_effectiveness(self, condition_seq, lookback_days=30):
        """조건검색 효과성 분석"""
        
        if condition_seq not in self.condition_history:
            return None
        
        recent_signals = self.get_recent_signals(condition_seq, lookback_days)
        
        if not recent_signals:
            return None
        
        # 성과 지표 계산
        total_signals = len(recent_signals)
        successful_signals = sum(
            1 for signal in recent_signals 
            if signal.get('outcome') == 'SUCCESS'
        )
        
        success_rate = successful_signals / total_signals if total_signals > 0 else 0
        
        # 평균 수익률 계산
        profitable_signals = [
            signal for signal in recent_signals 
            if signal.get('return_rate') is not None
        ]
        
        avg_return = (
            sum(signal['return_rate'] for signal in profitable_signals) / 
            len(profitable_signals) if profitable_signals else 0
        )
        
        analysis = {
            'condition_seq': condition_seq,
            'total_signals': total_signals,
            'success_rate': success_rate,
            'average_return': avg_return,
            'signal_frequency': total_signals / lookback_days,
            'effectiveness_score': self.calculate_effectiveness_score(
                success_rate, avg_return, total_signals
            )
        }
        
        self.performance_metrics[condition_seq] = analysis
        return analysis
    
    def get_best_performing_conditions(self, min_signals=10):
        """최고 성과 조건검색 식별"""
        
        valid_conditions = {
            seq: metrics for seq, metrics in self.performance_metrics.items()
            if metrics['total_signals'] >= min_signals
        }
        
        if not valid_conditions:
            return []
        
        # 효과성 점수 기준 정렬
        sorted_conditions = sorted(
            valid_conditions.items(),
            key=lambda x: x[1]['effectiveness_score'],
            reverse=True
        )
        
        return sorted_conditions[:5]  # 상위 5개 반환
```

### 4. 조건검색 기반 백테스팅

```python
class ConditionBacktester:
    def __init__(self):
        self.historical_conditions = {}
        self.backtest_results = {}
    
    async def backtest_condition_strategy(self, condition_seq, start_date, end_date):
        """조건검색 전략 백테스팅"""
        
        # 기간 내 조건검색 신호 수집
        condition_signals = await self.collect_historical_signals(
            condition_seq, start_date, end_date
        )
        
        if not condition_signals:
            return None
        
        # 백테스팅 실행
        portfolio_value = 10000000  # 1000만원 시작
        trades = []
        positions = {}
        
        for signal in condition_signals:
            if signal['signal_type'] == 'ENTRY':
                # 매수 신호 처리
                trade_result = await self.simulate_buy_trade(
                    signal, portfolio_value, positions
                )
                if trade_result:
                    trades.append(trade_result)
                    positions[signal['stock_code']] = trade_result
            
            elif signal['signal_type'] == 'EXIT':
                # 매도 신호 처리
                if signal['stock_code'] in positions:
                    trade_result = await self.simulate_sell_trade(
                        signal, positions[signal['stock_code']]
                    )
                    if trade_result:
                        trades.append(trade_result)
                        del positions[signal['stock_code']]
        
        # 백테스팅 결과 계산
        backtest_result = self.calculate_backtest_results(trades, portfolio_value)
        self.backtest_results[condition_seq] = backtest_result
        
        return backtest_result
    
    def calculate_backtest_results(self, trades, initial_capital):
        """백테스팅 결과 계산"""
        
        if not trades:
            return None
        
        # 수익률 계산
        total_trades = len([t for t in trades if t['type'] == 'SELL'])
        winning_trades = len([t for t in trades if t['type'] == 'SELL' and t['profit'] > 0])
        losing_trades = total_trades - winning_trades
        
        total_profit = sum(t['profit'] for t in trades if t['type'] == 'SELL')
        final_capital = initial_capital + total_profit
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_return = (final_capital - initial_capital) / initial_capital * 100
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'total_profit': total_profit,
            'final_capital': final_capital,
            'average_profit_per_trade': total_profit / total_trades if total_trades > 0 else 0
        }
```

## API 사용 시 주의사항

### 1. WebSocket 연결 관리
- 안정적인 연결 유지 필수
- 자동 재연결 메커니즘 구현
- PING/PONG 메시지 적절한 응답

### 2. 조건검색 제한사항
- 동시 실행 가능한 실시간 조건검색 개수 제한
- 조건검색식은 HTS에서 사전 등록 필요
- 검색 결과 연속조회 시 next_key 활용

### 3. 데이터 처리 최적화
```python
async def optimize_condition_processing(self):
    """조건검색 처리 최적화"""
    
    # 1. 중복 신호 필터링
    def filter_duplicate_signals(signals, time_window=60):
        filtered = []
        seen_stocks = {}
        
        for signal in signals:
            stock_code = signal['stock_code']
            signal_time = signal['timestamp']
            
            if stock_code in seen_stocks:
                last_signal_time = seen_stocks[stock_code]
                if signal_time - last_signal_time < time_window:
                    continue  # 중복 신호 제거
            
            seen_stocks[stock_code] = signal_time
            filtered.append(signal)
        
        return filtered
    
    # 2. 신호 우선순위 처리
    def prioritize_signals(signals):
        return sorted(signals, key=lambda x: (
            x.get('confidence_score', 0),
            -x.get('timestamp', 0)
        ), reverse=True)
```

### 4. 에러 처리 및 복구
```python
async def handle_condition_errors(self, error_response):
    """조건검색 에러 처리"""
    
    error_code = error_response.get('return_code')
    error_msg = error_response.get('return_msg', '')
    
    if error_code == 1:  # 일반 오류
        logger.error(f"조건검색 오류: {error_msg}")
        # 재시도 로직
        await asyncio.sleep(5)
        return "RETRY"
    
    elif "조건검색식" in error_msg:
        logger.error(f"조건검색식 문제: {error_msg}")
        # 조건검색식 재로드
        await self.condition_manager.load_condition_list()
        return "RELOAD_CONDITIONS"
    
    else:
        logger.error(f"알 수 없는 조건검색 오류: {error_msg}")
        return "UNKNOWN_ERROR"
```

## 전략 조건검색 최적화 전략

### 1. 조건식 설계 원칙
- **급등 조건**: 20% 이상 상승 + 거래량 급증
- **볼륨 조건**: 평균 거래량 대비 3배 이상
- **가격 조건**: 1,000원 ~ 50,000원 가격대
- **시가총액 조건**: 500억원 미만 중소형주

### 2. 실시간 모니터링 우선순위
1. **1순위**: 급등주 발굴 조건 (20%+ 상승)
2. **2순위**: 거래량 급증 조건 (볼륨 스파이크)
3. **3순위**: 기술적 돌파 조건 (저항선 돌파)
4. **4순위**: 테마주 관련 조건

### 3. 신호 검증 체계
- 조건 진입 후 추가 검증 로직 적용
- 가짜 신호 필터링 메커니즘
- 다중 조건 교차 검증

### 4. 성과 개선 방안
- 조건검색 결과의 지속적 성과 분석
- 효과적인 조건식 식별 및 집중 활용
- 비효과적인 조건검색 비활성화

이러한 조건검색 API들을 체계적으로 활용하면 전략 전략에서 수동 검색의 한계를 극복하고, 24시간 자동화된 종목 발굴 및 신호 감지 시스템을 구축할 수 있습니다.