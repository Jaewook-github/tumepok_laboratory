# 실시간시세_TR API 요약

## 개요

실시간시세_TR 폴더는 키움증권 REST API의 WebSocket 기반 실시간 시세 정보 API들을 포함합니다. 이 API들은 자동매매 시스템에서 실시간 시장 모니터링, 즉각적인 매매 신호 감지, 포지션 관리에 핵심적인 역할을 합니다.

## WebSocket 기본 구조

### 연결 정보
- **실전 URL**: `wss://api.kiwoom.com:10000/api/dostk/websocket`
- **모의 URL**: `wss://mockapi.kiwoom.com:10000/api/dostk/websocket`
- **인증**: Bearer 토큰 필요
- **프로토콜**: JSON 메시지 기반 비동기 통신

### 기본 WebSocket 클라이언트 구조
```python
import asyncio
import websockets
import json

class TumepokWebSocketClient:
    def __init__(self, uri, access_token):
        self.uri = uri
        self.access_token = access_token
        self.websocket = None
        self.connected = False
        self.keep_running = True
        self.subscribed_stocks = set()
        
    async def connect(self):
        """WebSocket 연결 및 로그인"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            
            # 로그인 패킷
            login_packet = {
                'trnm': 'LOGIN',
                'token': self.access_token
            }
            await self.send_message(login_packet)
            
        except Exception as e:
            print(f'Connection error: {e}')
            self.connected = False
    
    async def send_message(self, message):
        """메시지 전송"""
        if not self.connected:
            await self.connect()
        
        if self.connected:
            if not isinstance(message, str):
                message = json.dumps(message)
            await self.websocket.send(message)
    
    async def receive_messages(self):
        """실시간 메시지 수신"""
        while self.keep_running:
            try:
                response = json.loads(await self.websocket.recv())
                await self.handle_message(response)
                
            except websockets.ConnectionClosed:
                print('Connection closed')
                self.connected = False
                break
    
    async def handle_message(self, response):
        """메시지 타입별 처리"""
        msg_type = response.get('trnm')
        
        if msg_type == 'LOGIN':
            await self.handle_login_response(response)
        elif msg_type == 'PING':
            await self.send_message(response)  # PING에 응답
        elif msg_type == 'REAL':
            await self.handle_real_data(response)
    
    async def handle_login_response(self, response):
        """로그인 응답 처리"""
        if response.get('return_code') == 0:
            print('로그인 성공')
        else:
            print(f'로그인 실패: {response.get("return_msg")}')
            await self.disconnect()
    
    async def handle_real_data(self, response):
        """실시간 데이터 처리"""
        for data in response.get('data', []):
            data_type = data.get('type')
            item = data.get('item')
            values = data.get('values', {})
            
            # 데이터 타입별 처리
            if data_type == '0A':
                await self.process_stock_quote(item, values)
            elif data_type == '0B':
                await self.process_stock_execution(item, values)
            elif data_type == '0D':
                await self.process_bid_ask(item, values)
            elif data_type == '00':
                await self.process_order_execution(values)
```

## 주요 실시간 데이터 타입

### 1. 00 - 주문체결 (핵심)

#### 기본 정보
- **목적**: 사용자 주문의 실시간 체결 정보
- **전략 활용**: 주문 상태 추적, 포지션 관리, 자동 재주문

#### 주요 필드
```python
ORDER_EXECUTION_FIELDS = {
    '9201': '계좌번호',
    '9203': '주문번호', 
    '9001': '종목코드',
    '912': '주문업무분류',
    '913': '주문상태',
    '302': '종목명',
    '900': '주문수량',
    '901': '주문가격',
    '902': '미체결수량',
    '903': '체결누계금액',
    '910': '체결가',
    '911': '체결량',
    '906': '매매구분',
    '908': '주문/체결시간'
}
```

#### 활용 예시
```python
async def process_order_execution(self, values):
    """주문체결 데이터 처리"""
    order_status = values.get('913')  # 주문상태
    stock_code = values.get('9001')   # 종목코드
    executed_quantity = int(values.get('911', 0))  # 체결량
    executed_price = float(values.get('910', 0))   # 체결가
    
    if order_status == '2':  # 체결
        await self.update_position(stock_code, executed_quantity, executed_price)
        await self.check_exit_conditions(stock_code)
    elif order_status == '4':  # 확인
        await self.log_order_confirmed(values)
```

### 2. 0A - 주식시세 (핵심)

#### 기본 정보
- **목적**: 실시간 주식 시세 정보
- **전략 활용**: 실시간 가격 모니터링, 진입/청산 신호 생성

#### 주요 필드
```python
STOCK_QUOTE_FIELDS = {
    '10': '현재가',
    '11': '전일대비',
    '12': '등락율',
    '27': '매도호가',
    '28': '매수호가',
    '13': '누적거래량',
    '14': '누적거래대금',
    '16': '시가',
    '17': '고가',
    '18': '저가',
    '25': '전일대비기호',
    '26': '전일거래량대비',
    '31': '거래회전율',
    '311': '시가총액(억)'
}
```

#### 활용 예시
```python
async def process_stock_quote(self, stock_code, values):
    """실시간 주식시세 처리"""
    current_price = float(values.get('10', 0))
    change_rate = float(values.get('12', 0))
    volume = int(values.get('13', 0))
    high_price = float(values.get('17', 0))
    
    # 전략 진입 조건 확인
    if self.is_tracking_stock(stock_code):
        tracking_info = self.get_tracking_info(stock_code)
        
        # 하락폭 계산
        drop_rate = ((tracking_info['high_price'] - current_price) 
                    / tracking_info['high_price']) * 100
        
        # 전략 매트릭스 확인
        if self.check_tumepok_entry_condition(tracking_info['rise_rate'], drop_rate):
            await self.generate_buy_signal(stock_code, current_price)
    
    # 20% 이상 급등주 새로 발견
    elif change_rate >= 20.0 and volume >= 100000:
        await self.add_tracking_stock(stock_code, current_price, high_price)
```

### 3. 0B - 주식체결 (핵심)

#### 기본 정보
- **목적**: 실시간 주식 체결 정보
- **전략 활용**: 체결강도 분석, 매매 압력 감지

#### 주요 필드
```python
STOCK_EXECUTION_FIELDS = {
    '20': '체결시간',
    '10': '현재가',
    '15': '거래량',  # +매수체결, -매도체결
    '228': '체결강도',
    '1030': '매도체결량',
    '1031': '매수체결량',
    '1032': '매수비율',
    '1314': '순매수체결량',
    '851': '전일 동시간 거래량 비율'
}
```

#### 활용 예시
```python
async def process_stock_execution(self, stock_code, values):
    """실시간 주식체결 처리"""
    execution_time = values.get('20')
    execution_strength = float(values.get('228', 0))
    buy_volume = int(values.get('1031', 0))
    sell_volume = int(values.get('1030', 0))
    net_buy_volume = int(values.get('1314', 0))
    
    # 체결강도 급상승 감지
    if execution_strength > 200:
        await self.alert_high_execution_strength(stock_code, execution_strength)
    
    # 순매수 우세 감지
    if net_buy_volume > 0 and buy_volume > sell_volume * 1.5:
        await self.signal_buying_pressure(stock_code)
    
    # 전략 진입 후 매도압력 감지
    if self.has_position(stock_code) and sell_volume > buy_volume * 2:
        await self.check_exit_signal(stock_code)
```

### 4. 0D - 주식호가잔량

#### 기본 정보
- **목적**: 실시간 호가 및 잔량 정보
- **전략 활용**: 호가 불균형 분석, 진입/청산 타이밍

#### 활용 예시
```python
async def process_bid_ask(self, stock_code, values):
    """실시간 호가잔량 처리"""
    # 호가별 잔량 분석
    bid_imbalance = self.calculate_bid_imbalance(values)
    
    if bid_imbalance['ratio'] > 0.6:  # 매수 우세
        await self.signal_buy_pressure(stock_code)
    elif bid_imbalance['ratio'] < 0.4:  # 매도 우세
        await self.signal_sell_pressure(stock_code)
```

### 5. 0C - 주식우선호가

#### 기본 정보
- **목적**: 실시간 우선호가 정보
- **활용**: 호가 스프레드 분석

### 6. 0E - 주식시간외호가

#### 기본 정보
- **목적**: 시간외 거래 호가 정보
- **활용**: 장외 거래 동향 파악

### 7. 0F - 주식당일거래원

#### 기본 정보
- **목적**: 실시간 거래원별 매매 정보
- **활용**: 세력 분석, 기관 동향 파악

### 8. 1h - VI발동해제 (중요)

#### 기본 정보
- **목적**: 변동성완화장치(VI) 발동/해제 알림
- **활용**: 급변동 감지, 거래 중단 대응

#### 활용 예시
```python
async def process_vi_trigger(self, stock_code, vi_status):
    """VI 발동/해제 처리"""
    if vi_status == 'TRIGGERED':
        # VI 발동 시 주문 대기
        await self.pause_trading(stock_code)
        await self.alert_vi_triggered(stock_code)
    elif vi_status == 'RELEASED':
        # VI 해제 시 거래 재개
        await self.resume_trading(stock_code)
        await self.check_price_gap(stock_code)
```

### 9. 기타 데이터 타입

#### 0G - ETF_NAV
- ETF 순자산가치 실시간 정보

#### 0g - 주식종목정보
- 종목 기본 정보 변경 알림

#### 0H - 주식예상체결
- 장전/장후 예상체결 정보

#### 0J - 업종지수
- 업종별 지수 실시간 정보

#### 0m - ELW이론가
- ELW 이론가격 정보

#### 0s - 장시작시간
- 장 시작 시간 알림

#### 0u - ELW지표
- ELW 관련 지표

#### 0U - 업종등락
- 업종별 등락 정보

#### 0w - 종목프로그램매매
- 종목별 프로그램 매매 정보

## 시스템 통합 전략

### 1. 통합 실시간 모니터링 시스템

```python
class TumepokRealTimeMonitor:
    def __init__(self, websocket_client):
        self.ws_client = websocket_client
        self.tracking_stocks = {}
        self.positions = {}
        self.signal_queue = asyncio.Queue()
        
    async def start_monitoring(self, initial_stocks=None):
        """실시간 모니터링 시작"""
        # 핵심 데이터 타입 구독
        essential_types = ['0A', '0B', '0D', '00', '1h']
        
        if initial_stocks:
            await self.subscribe_stocks(initial_stocks, essential_types)
        
        # 메시지 처리 루프 시작
        await asyncio.gather(
            self.ws_client.receive_messages(),
            self.process_signals(),
            self.monitor_positions(),
            self.scan_new_stocks()
        )
    
    async def subscribe_stocks(self, stock_codes, data_types):
        """종목별 실시간 데이터 구독"""
        subscription_data = {
            'trnm': 'REG',
            'grp_no': '1',
            'refresh': '1',
            'data': [{'item': stock_codes, 'type': data_types}]
        }
        
        await self.ws_client.send_message(subscription_data)
        
        for stock_code in stock_codes:
            self.tracking_stocks[stock_code] = {
                'status': 'MONITORING',
                'start_time': datetime.now(),
                'data_types': data_types
            }
    
    async def process_signals(self):
        """신호 처리 루프"""
        while True:
            try:
                signal = await asyncio.wait_for(self.signal_queue.get(), timeout=1.0)
                await self.handle_trading_signal(signal)
            except asyncio.TimeoutError:
                continue
    
    async def handle_trading_signal(self, signal):
        """거래 신호 처리"""
        signal_type = signal['type']
        stock_code = signal['stock_code']
        
        if signal_type == 'BUY_ENTRY':
            await self.execute_tumepok_buy(signal)
        elif signal_type == 'SELL_EXIT':
            await self.execute_tumepok_sell(signal)
        elif signal_type == 'STOP_LOSS':
            await self.execute_stop_loss(signal)
        elif signal_type == 'VI_ALERT':
            await self.handle_vi_event(signal)
```

### 2. 실시간 신호 생성 시스템

```python
class TumepokSignalGenerator:
    def __init__(self):
        self.tumepok_matrix = self.load_tumepok_matrix()
        self.signal_conditions = {}
        
    async def analyze_real_time_data(self, data_type, stock_code, values):
        """실시간 데이터 분석"""
        if data_type == '0A':
            await self.analyze_price_movement(stock_code, values)
        elif data_type == '0B':
            await self.analyze_execution_pattern(stock_code, values)
        elif data_type == '0D':
            await self.analyze_bid_ask_imbalance(stock_code, values)
    
    async def analyze_price_movement(self, stock_code, values):
        """가격 움직임 분석"""
        current_price = float(values.get('10', 0))
        change_rate = float(values.get('12', 0))
        volume = int(values.get('13', 0))
        
        # 새로운 급등주 발견
        if change_rate >= 20.0 and volume >= 100000:
            if stock_code not in self.tracking_stocks:
                await self.start_tracking_stock(stock_code, current_price)
        
        # 기존 추적 종목의 하락폭 확인
        elif stock_code in self.tracking_stocks:
            tracking_info = self.tracking_stocks[stock_code]
            drop_rate = self.calculate_drop_rate(tracking_info, current_price)
            
            if self.check_tumepok_entry_condition(tracking_info, drop_rate):
                await self.generate_buy_signal(stock_code, current_price)
    
    async def generate_buy_signal(self, stock_code, current_price):
        """매수 신호 생성"""
        # 지지 조건 확인
        support_conditions = await self.check_support_conditions(stock_code)
        
        if support_conditions['count'] >= 2:
            signal = {
                'type': 'BUY_ENTRY',
                'stock_code': stock_code,
                'price': current_price,
                'confidence': support_conditions['confidence'],
                'timestamp': datetime.now(),
                'conditions': support_conditions
            }
            
            await self.signal_queue.put(signal)
```

### 3. 포지션 실시간 관리

```python
class TumepokPositionManager:
    def __init__(self):
        self.positions = {}
        self.stop_loss_rate = -2.0
        self.trailing_trigger_rate = 2.0
        
    async def monitor_positions(self):
        """포지션 실시간 모니터링"""
        while True:
            for stock_code, position in self.positions.items():
                await self.check_position_conditions(stock_code, position)
            await asyncio.sleep(1)
    
    async def check_position_conditions(self, stock_code, position):
        """포지션 조건 확인"""
        current_price = await self.get_current_price(stock_code)
        profit_rate = self.calculate_profit_rate(position, current_price)
        
        # 손절 조건
        if profit_rate <= self.stop_loss_rate:
            await self.generate_stop_loss_signal(stock_code)
        
        # 트레일링 스톱 조건
        elif profit_rate >= self.trailing_trigger_rate:
            await self.activate_trailing_stop(stock_code, current_price)
        
        # 기타 청산 조건
        elif await self.check_exit_conditions(stock_code):
            await self.generate_exit_signal(stock_code)
```

### 4. 실시간 리스크 관리

```python
class TumepokRiskManager:
    def __init__(self):
        self.daily_loss_limit = -200000
        self.max_concurrent_trades = 20
        self.daily_pnl = 0
        
    async def monitor_risk_limits(self):
        """리스크 한도 모니터링"""
        while True:
            # 일일 손실 한도 확인
            if self.daily_pnl <= self.daily_loss_limit:
                await self.emergency_close_all_positions()
            
            # 동시 거래 한도 확인
            if len(self.positions) >= self.max_concurrent_trades:
                await self.pause_new_entries()
            
            await asyncio.sleep(10)
    
    async def handle_vi_trigger(self, stock_code):
        """VI 발동 시 리스크 관리"""
        if stock_code in self.positions:
            # VI 발동 종목 주문 중단
            await self.cancel_pending_orders(stock_code)
            await self.mark_position_risk(stock_code, 'VI_TRIGGERED')
```

## API 사용 시 주의사항

### 1. 연결 관리
- WebSocket 연결 상태 지속 모니터링
- 자동 재연결 메커니즘 구현
- PING/PONG 메시지 적절한 응답

### 2. 데이터 처리
- 비동기 처리로 메시지 처리 지연 방지
- 중요 데이터 타입 우선순위 설정
- 메시지 큐 오버플로우 방지

### 3. 에러 처리
```python
async def handle_websocket_error(self, error):
    """WebSocket 에러 처리"""
    if isinstance(error, websockets.ConnectionClosed):
        await self.reconnect_with_backoff()
    elif isinstance(error, json.JSONDecodeError):
        logger.error(f"JSON 파싱 에러: {error}")
    else:
        logger.error(f"예상치 못한 에러: {error}")
```

### 4. 성능 최적화
- 불필요한 종목 구독 해제
- 메모리 사용량 모니터링
- 데이터 처리 병목지점 식별

## 전략 실시간 전략 최적화

### 1. 지연시간 최소화
- 핵심 데이터만 선별 구독
- 로컬 캐싱으로 중복 처리 방지
- 병렬 처리로 응답 속도 향상

### 2. 신뢰성 향상
- 중복 신호 필터링
- 데이터 무결성 검증
- 장애 시 자동 복구

### 3. 확장성 고려
- 모듈별 독립적 확장 가능
- 다중 WebSocket 연결 지원
- 부하 분산 메커니즘

이러한 실시간 시세 API들을 체계적으로 활용하면 전략의 핵심인 실시간 모니터링과 즉각적인 반응이 가능하며, 시장 변화에 신속하게 대응할 수 있는 자동매매 시스템을 구축할 수 있습니다.