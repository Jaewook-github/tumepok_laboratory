# 주문_TR API 요약

## 개요
키움증권 REST API의 주식 주문 관련 TR(Transaction Request) 코드들로, 매수/매도/정정/취소 등 모든 주문 실행 기능을 제공합니다. 전략 자동매매 시스템에서 실제 거래 실행의 핵심이 되는 API 그룹으로, 정확하고 안정적인 주문 처리가 시스템의 성패를 좌우합니다.

## 주요 API 구성

### 1. kt10000 - 주식 매수주문
- **용도**: 주식 매수 주문 실행
- **지원 주문 유형**: 보통, 시장가, 조건부지정가, 최유리지정가, IOC, FOK, 스톱지정가 등
- **핵심 파라미터**: 
  - `stk_cd`: 종목코드
  - `ord_qty`: 주문수량  
  - `ord_uv`: 주문단가
  - `trde_tp`: 매매구분 코드

### 2. kt10001 - 주식 매도주문
- **용도**: 주식 매도 주문 실행
- **지원 주문 유형**: 매수 주문과 동일한 모든 주문 유형
- **스톱로스**: 스톱지정가(28) 활용한 자동 손절 기능
- **응답**: 생성된 주문번호 반환

### 3. kt10002 - 주식 정정주문
- **용도**: 기존 주문의 수량/단가 정정
- **정정 가능 항목**: 수량, 단가, 조건단가
- **핵심 파라미터**: `orig_ord_no` (원주문번호) 필수
- **제약사항**: 부분체결 시 잔량에 대해서만 정정 가능

### 4. kt10003 - 주식 취소주문  
- **용도**: 기존 주문의 전체/부분 취소
- **취소 방식**: 전체 취소(`cncl_qty`: '0') 또는 부분 취소
- **제약사항**: 체결된 수량은 취소 불가

## 매매구분 코드 체계

### 기본 주문 유형
- **0**: 보통 (지정가)
- **3**: 시장가
- **5**: 조건부지정가
- **6**: 최유리지정가
- **7**: 최우선지정가
- **28**: 스톱지정가 (손절매 활용)

### IOC/FOK 주문 (즉시 처리 주문)
- **10**: 보통(IOC)
- **13**: 시장가(IOC) 
- **16**: 최유리(IOC)
- **20**: 보통(FOK)
- **23**: 시장가(FOK)
- **26**: 최유리(FOK)

### 시간외 거래
- **61**: 장시작전시간외
- **62**: 시간외단일가  
- **81**: 장마감후시간외

## 전략 시스템 통합 전략

### 1. 스마트 주문 실행 엔진
```python
class TumepokOrderEngine:
    def __init__(self):
        self.order_queue = []
        self.active_orders = {}
        
    def execute_tumepok_buy(self, stock_code, stage, drop_rate):
        """전략 매수 주문 실행"""
        # 단계별 투자 비율 계산
        position_ratio = self.STAGE_RATIOS[stage]  # 1차:30%, 2차:40%, 3차:30%
        order_amount = self.base_amount * position_ratio
        
        # 수량 계산
        current_price = self.get_current_price(stock_code)
        quantity = int(order_amount / current_price)
        
        # 매수 주문 실행
        order_params = {
            'dmst_stex_tp': 'KRX',
            'stk_cd': stock_code,
            'ord_qty': str(quantity),
            'ord_uv': str(current_price),
            'trde_tp': '0',  # 지정가
            'cond_uv': ''
        }
        
        order_result = self.send_buy_order(order_params)
        self.track_order(order_result['ord_no'], stock_code, stage)
        
        return order_result
    
    def execute_stop_loss(self, stock_code, position_info):
        """손절매 주문 실행"""
        stop_price = int(position_info['avg_price'] * 0.98)  # -2% 손절
        
        order_params = {
            'dmst_stex_tp': 'KRX',
            'stk_cd': stock_code,
            'ord_qty': str(position_info['quantity']),
            'ord_uv': str(stop_price),
            'trde_tp': '28',  # 스톱지정가
            'cond_uv': str(stop_price + 100)  # 조건가격
        }
        
        return self.send_sell_order(order_params)
```

### 2. 지능형 주문 관리 시스템
```python
class OrderManager:
    def __init__(self):
        self.pending_orders = {}
        self.executed_orders = {}
        
    def manage_active_orders(self):
        """활성 주문 관리 및 조정"""
        for order_no, order_info in self.pending_orders.items():
            # 시장 상황 변화 시 주문 조정
            if self.should_modify_order(order_info):
                self.modify_order(order_no, order_info)
            
            # 조건 불충족 시 주문 취소
            elif self.should_cancel_order(order_info):
                self.cancel_order(order_no)
    
    def modify_order(self, orig_order_no, new_params):
        """주문 정정 실행"""
        modify_params = {
            'dmst_stex_tp': 'KRX',
            'orig_ord_no': orig_order_no,
            'stk_cd': new_params['stock_code'],
            'mdfy_qty': new_params['quantity'],
            'mdfy_uv': new_params['price'],
            'mdfy_cond_uv': ''
        }
        
        return self.send_modify_order(modify_params)
    
    def cancel_order(self, orig_order_no):
        """주문 취소 실행"""
        cancel_params = {
            'dmst_stex_tp': 'KRX',
            'orig_ord_no': orig_order_no,
            'stk_cd': self.pending_orders[orig_order_no]['stock_code'],
            'cncl_qty': '0'  # 전체 취소
        }
        
        return self.send_cancel_order(cancel_params)
```

### 3. 리스크 관리 주문 시스템
```python
class RiskManagedOrderSystem:
    def __init__(self):
        self.daily_loss_limit = -200000  # 일일 손실 한도
        self.max_position_per_stock = 2000000  # 종목당 최대 투자금
        
    def validate_order(self, order_params):
        """주문 전 리스크 검증"""
        # 1. 일일 손실 한도 확인
        if self.get_daily_pnl() <= self.daily_loss_limit:
            return False, "일일 손실 한도 초과"
        
        # 2. 종목당 투자 한도 확인
        current_position = self.get_position_value(order_params['stk_cd'])
        order_value = int(order_params['ord_qty']) * int(order_params['ord_uv'])
        
        if current_position + order_value > self.max_position_per_stock:
            return False, "종목당 투자 한도 초과"
        
        # 3. 시장 시간 확인
        if not self.is_market_open():
            return False, "장 마감 시간"
            
        return True, "주문 가능"
    
    def execute_protected_order(self, order_params, order_type):
        """안전장치가 적용된 주문 실행"""
        # 주문 전 검증
        is_valid, message = self.validate_order(order_params)
        if not is_valid:
            return {'success': False, 'message': message}
        
        try:
            # 주문 실행
            if order_type == 'buy':
                result = self.send_buy_order(order_params)
            elif order_type == 'sell':
                result = self.send_sell_order(order_params)
            
            # 주문 후 추적 등록
            if result.get('ord_no'):
                self.register_order_tracking(result['ord_no'], order_params)
            
            return {'success': True, 'result': result}
            
        except Exception as e:
            self.log_error(f"주문 실행 오류: {e}")
            return {'success': False, 'message': str(e)}
```

### 4. 전략 특화 주문 전략
```python
class TumepokOrderStrategy:
    def __init__(self):
        self.STAGE_RATIOS = {'1차': 0.30, '2차': 0.40, '3차': 0.30}
        
    def execute_tumepok_sequence(self, stock_code, market_data):
        """전략 3단계 매수 시퀀스"""
        # 1차 매수 (약한 지지 조건)
        if market_data['support_conditions'] >= 1:
            self.execute_stage_buy(stock_code, '1차', market_data)
        
        # 2차 매수 (중간 하락폭 + 강한 지지)
        if market_data['drop_rate'] >= 15 and market_data['support_conditions'] >= 2:
            self.execute_stage_buy(stock_code, '2차', market_data)
        
        # 3차 매수 (최대 하락폭 + 강한 지지)
        if market_data['drop_rate'] >= 20 and market_data['support_conditions'] >= 2:
            self.execute_stage_buy(stock_code, '3차', market_data)
    
    def execute_smart_exit(self, position_info):
        """스마트 청산 전략"""
        profit_rate = position_info['profit_rate']
        
        # 손절매 (-2%)
        if profit_rate <= -2.0:
            return self.execute_market_sell(position_info, "손절매")
        
        # 트레일링 스톱 (+2% 이상에서 -1% 하락)
        if position_info['trailing_activated'] and profit_rate <= position_info['trailing_high'] - 1.0:
            return self.execute_market_sell(position_info, "트레일링 스톱")
        
        # 목표 수익 달성 (+7%)
        if profit_rate >= 7.0:
            return self.execute_limit_sell(position_info, "목표 수익")
    
    def execute_market_sell(self, position_info, reason):
        """시장가 매도 (긴급 상황)"""
        sell_params = {
            'dmst_stex_tp': 'KRX',
            'stk_cd': position_info['stock_code'],
            'ord_qty': str(position_info['quantity']),
            'ord_uv': '',
            'trde_tp': '3',  # 시장가
            'cond_uv': ''
        }
        
        self.log_trade(f"{reason}: {position_info['stock_code']} 시장가 매도")
        return self.send_sell_order(sell_params)
```

## 주문 실행 최적화 전략

### 1. 호가 분석 기반 주문
```python
def get_optimal_order_price(stock_code, order_type):
    """호가 분석을 통한 최적 주문가 결정"""
    orderbook = get_current_orderbook(stock_code)
    
    if order_type == 'buy':
        # 매수: 매수1호가와 현재가 사이의 적정가
        return min(orderbook['buy_price1'], orderbook['current_price'])
    else:
        # 매도: 매도1호가와 현재가 사이의 적정가
        return max(orderbook['sell_price1'], orderbook['current_price'])
```

### 2. 시간대별 주문 전략
```python
def get_time_based_order_type(current_time):
    """시간대별 최적 주문 유형"""
    if current_time < '09:30':
        return '61'  # 장시작전시간외
    elif current_time > '15:20':
        return '81'  # 장마감후시간외  
    elif current_time > '15:00':
        return '3'   # 시장가 (빠른 체결 우선)
    else:
        return '0'   # 일반 지정가
```

### 3. 거래량 기반 주문 수량 조절
```python
def calculate_optimal_quantity(stock_code, target_amount):
    """거래량 기반 최적 주문 수량"""
    volume_info = get_volume_analysis(stock_code)
    
    # 일평균 거래량의 1% 이하로 제한
    max_shares = volume_info['avg_daily_volume'] * 0.01
    
    current_price = get_current_price(stock_code)
    target_shares = target_amount / current_price
    
    return min(target_shares, max_shares)
```

## 에러 처리 및 재시도 로직

### 1. 주문 실패 시 재시도 전략
```python
class OrderRetryHandler:
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = [1, 3, 5]  # 초 단위
        
    async def execute_with_retry(self, order_func, params):
        """재시도 로직이 적용된 주문 실행"""
        for attempt in range(self.max_retries):
            try:
                result = await order_func(params)
                if self.is_order_success(result):
                    return result
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                    
                await asyncio.sleep(self.retry_delay[attempt])
                self.log_retry(f"주문 재시도 {attempt + 1}/{self.max_retries}")
        
        raise Exception("최대 재시도 횟수 초과")
```

### 2. 주문 상태 모니터링
```python
def monitor_order_status(order_no):
    """주문 상태 실시간 모니터링"""
    timeout = 30  # 30초 타임아웃
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = get_order_status(order_no)
        
        if status == 'FILLED':
            return '체결완료'
        elif status == 'CANCELLED':
            return '취소됨'
        elif status == 'REJECTED':
            return '거부됨'
            
        time.sleep(1)
    
    return '타임아웃'
```

## 성능 최적화 및 안정성

### 1. 주문 큐 관리
- 동시 주문 수 제한 (최대 10개)
- 종목별 주문 간격 제어 (3초)
- 우선순위 기반 주문 처리

### 2. 네트워크 안정성
- 연결 끊김 자동 재연결
- 주문 중복 방지 로직
- 타임아웃 설정 및 처리

### 3. 데이터 정합성
- 주문 전 계좌 잔고 확인
- 보유 수량 실시간 동기화
- 주문 내역 로컬 백업

## 결론

주문_TR API 그룹은 전략 자동매매 시스템의 실행 엔진으로, 정확하고 신속한 주문 처리가 전략의 성공을 좌우합니다. 특히 kt10000(매수)과 kt10001(매도)를 중심으로 한 스마트 주문 시스템과, kt10002(정정), kt10003(취소)를 활용한 동적 주문 관리가 핵심입니다. 리스크 관리와 에러 처리를 철저히 구현하여 안정적인 자동매매 시스템을 구축해야 합니다.