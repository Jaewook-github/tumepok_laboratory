# 신용주문_TR API 요약

## 개요

신용주문_TR 폴더는 키움증권 REST API의 신용거래 주문 관련 API들을 포함합니다. 신용거래는 증권회사로부터 자금(융자) 또는 주식(대주)을 빌려서 매매하는 거래로, 전략(tumepok) 자동매매 시스템에서 레버리지를 활용한 수익 극대화에 사용됩니다.

## 신용거래 기본 개념

### 신용거래 유형
- **융자거래**: 증권회사에서 자금을 빌려 주식을 매수
- **대주거래**: 증권회사에서 주식을 빌려 매도 (공매도)
- **융자합**: 융자거래와 일반거래를 합쳐서 매도

### 신용거래 특징
- **레버리지 효과**: 자기자본보다 큰 금액으로 거래 가능
- **이자 부담**: 빌린 자금/주식에 대한 이자 발생
- **위험도 증가**: 손실 시 원금 이상의 손실 가능
- **기간 제한**: 융자 기간 내 반드시 상환 필요

## 주요 API 분류

### 1. kt10006 - 신용 매수주문

#### 기본 정보
- **목적**: 신용을 이용한 주식 매수 주문
- **엔드포인트**: `/api/dostk/crdordr`
- **전략 활용**: 급등 후보주에 대한 레버리지 매수

#### 주요 파라미터
```python
{
    'dmst_stex_tp': 'KRX',    # 국내거래소구분 (KRX/NXT/SOR)
    'stk_cd': '005930',       # 종목코드
    'ord_qty': '1',           # 주문수량
    'ord_uv': '2580',         # 주문단가
    'trde_tp': '0',           # 매매구분
    'cond_uv': ''             # 조건단가
}
```

#### 매매구분 코드
- `0`: 보통 지정가
- `3`: 시장가
- `5`: 조건부지정가
- `6`: 최유리지정가
- `7`: 최우선지정가
- `10`: 보통(IOC)
- `13`: 시장가(IOC)
- `20`: 보통(FOK)
- `28`: 스톱지정가

#### 전략 활용 예시
```python
def credit_buy_order_tumepok(stock_code, quantity, price):
    """전략 전략 신용 매수 주문"""
    params = {
        'dmst_stex_tp': 'KRX',
        'stk_cd': stock_code,
        'ord_qty': str(quantity),
        'ord_uv': str(price),
        'trde_tp': '0',  # 지정가
        'cond_uv': ''
    }
    
    response = fn_kt10006(ACCESS_TOKEN, params)
    
    if response['status'] == 'success':
        return {
            'order_no': response['body']['ord_no'],
            'exchange': response['body']['dmst_stex_tp'],
            'status': 'ORDER_PLACED'
        }
    else:
        return {'status': 'ORDER_FAILED', 'error': response['error']}
```

### 2. kt10007 - 신용 매도주문

#### 기본 정보
- **목적**: 신용거래로 매수한 주식의 매도 또는 신용 공매도
- **전략 활용**: 목표가 도달 시 신용 포지션 청산

#### 주요 파라미터 (추가)
```python
{
    'crd_deal_tp': '99',      # 신용거래구분 (33:융자, 99:융자합)
    'crd_loan_dt': '',        # 대출일 (융자일 경우 필수)
}
```

#### 신용거래구분
- `33`: 융자 - 빌린 자금으로 매수한 주식 매도
- `99`: 융자합 - 융자거래와 일반거래 합쳐서 매도

#### 전략 활용 예시
```python
def credit_sell_order_tumepok(stock_code, quantity, price, loan_date=None):
    """전략 전략 신용 매도 주문"""
    params = {
        'dmst_stex_tp': 'KRX',
        'stk_cd': stock_code,
        'ord_qty': str(quantity),
        'ord_uv': str(price),
        'trde_tp': '0',
        'crd_deal_tp': '99',  # 융자합
        'crd_loan_dt': loan_date or '',
        'cond_uv': ''
    }
    
    response = fn_kt10007(ACCESS_TOKEN, params)
    return process_order_response(response)
```

### 3. kt10008 - 신용 정정주문

#### 기본 정보
- **목적**: 기존 신용 주문의 수량 또는 가격 변경
- **전략 활용**: 시장 상황 변화에 따른 주문 조정

#### 주요 파라미터
```python
{
    'orig_ord_no': '0000455',  # 원주문번호
    'mdfy_qty': '1',           # 정정수량
    'mdfy_uv': '2590',         # 정정단가
    'mdfy_cond_uv': ''         # 정정조건단가
}
```

#### 전략 활용 예시
```python
def modify_credit_order_tumepok(original_order_no, new_quantity, new_price):
    """전략 전략 신용 주문 정정"""
    params = {
        'dmst_stex_tp': 'KRX',
        'orig_ord_no': original_order_no,
        'stk_cd': get_stock_code_from_order(original_order_no),
        'mdfy_qty': str(new_quantity),
        'mdfy_uv': str(new_price),
        'mdfy_cond_uv': ''
    }
    
    response = fn_kt10008(ACCESS_TOKEN, params)
    
    if response['status'] == 'success':
        return {
            'new_order_no': response['body']['ord_no'],
            'original_order_no': response['body']['base_orig_ord_no'],
            'modified_quantity': response['body']['mdfy_qty'],
            'status': 'ORDER_MODIFIED'
        }
```

### 4. kt10009 - 신용 취소주문

#### 기본 정보
- **목적**: 기존 신용 주문의 취소
- **전략 활용**: 급변하는 시장 상황에서 주문 철회

#### 주요 파라미터
```python
{
    'orig_ord_no': '0001615',  # 원주문번호
    'cncl_qty': '1'            # 취소수량 ('0' 입력시 잔량 전부 취소)
}
```

#### 전략 활용 예시
```python
def cancel_credit_order_tumepok(original_order_no, cancel_quantity=0):
    """전략 전략 신용 주문 취소"""
    params = {
        'dmst_stex_tp': 'KRX',
        'orig_ord_no': original_order_no,
        'stk_cd': get_stock_code_from_order(original_order_no),
        'cncl_qty': str(cancel_quantity)  # 0이면 전량 취소
    }
    
    response = fn_kt10009(ACCESS_TOKEN, params)
    
    if response['status'] == 'success':
        return {
            'cancelled_order_no': response['body']['ord_no'],
            'original_order_no': response['body']['base_orig_ord_no'],
            'cancelled_quantity': response['body']['cncl_qty'],
            'status': 'ORDER_CANCELLED'
        }
```

## 전략 시스템 통합 전략

### 1. 신용거래 포지션 관리 시스템

```python
class CreditPositionManager:
    def __init__(self):
        self.credit_positions = {}
        self.max_leverage_ratio = 2.0  # 최대 레버리지 비율
        self.interest_rate = 0.08  # 연 8% 이자율
    
    def calculate_max_credit_amount(self, available_cash):
        """최대 신용거래 가능 금액 계산"""
        return available_cash * self.max_leverage_ratio
    
    def execute_credit_buy_strategy(self, stock_code, tumepok_signal):
        """전략 신용 매수 전략 실행"""
        if tumepok_signal['confidence'] < 0.7:
            return {"status": "SKIP", "reason": "Low confidence signal"}
        
        # 포지션 크기 계산
        position_size = self.calculate_position_size(tumepok_signal)
        entry_price = tumepok_signal['entry_price']
        
        # 신용 매수 주문
        order_result = credit_buy_order_tumepok(
            stock_code, position_size, entry_price
        )
        
        if order_result['status'] == 'ORDER_PLACED':
            # 포지션 기록
            self.credit_positions[stock_code] = {
                'order_no': order_result['order_no'],
                'quantity': position_size,
                'entry_price': entry_price,
                'entry_time': datetime.now(),
                'position_type': 'CREDIT_LONG',
                'interest_start_date': datetime.now().date()
            }
        
        return order_result
    
    def monitor_credit_positions(self):
        """신용 포지션 모니터링"""
        for stock_code, position in self.credit_positions.items():
            # 현재가 조회
            current_price = get_current_price(stock_code)
            
            # 수익률 계산
            profit_rate = ((current_price - position['entry_price']) 
                          / position['entry_price']) * 100
            
            # 이자 비용 계산
            interest_cost = self.calculate_interest_cost(position)
            
            # 청산 조건 확인
            exit_signal = self.check_exit_conditions(
                stock_code, profit_rate, interest_cost
            )
            
            if exit_signal['action'] == 'SELL':
                self.execute_credit_sell(stock_code, exit_signal)
    
    def execute_credit_sell(self, stock_code, exit_signal):
        """신용 매도 실행"""
        position = self.credit_positions[stock_code]
        
        sell_result = credit_sell_order_tumepok(
            stock_code, 
            position['quantity'], 
            exit_signal['price'],
            position['entry_time'].strftime('%Y%m%d')
        )
        
        if sell_result['status'] == 'ORDER_PLACED':
            position['exit_order_no'] = sell_result['order_no']
            position['exit_signal'] = exit_signal
            position['status'] = 'SELLING'
```

### 2. 전략 신용거래 리스크 관리

```python
class CreditRiskManager:
    def __init__(self):
        self.max_credit_exposure = 50000000  # 5천만원 최대 신용 노출
        self.stop_loss_rate = -15.0  # -15% 손절
        self.interest_rate_threshold = 5.0  # 이자 부담 5% 초과시 경고
    
    def assess_credit_risk(self, stock_code, position_info):
        """신용거래 리스크 평가"""
        risks = {
            'leverage_risk': self.assess_leverage_risk(position_info),
            'interest_risk': self.assess_interest_risk(position_info),
            'liquidity_risk': self.assess_liquidity_risk(stock_code),
            'market_risk': self.assess_market_risk(stock_code)
        }
        
        overall_risk = self.calculate_overall_risk(risks)
        
        return {
            'individual_risks': risks,
            'overall_risk_level': overall_risk,
            'recommendations': self.generate_risk_recommendations(risks)
        }
    
    def calculate_interest_cost(self, position):
        """이자 비용 계산"""
        days_held = (datetime.now().date() - position['interest_start_date']).days
        if days_held == 0:
            days_held = 1
        
        position_value = position['quantity'] * position['entry_price']
        daily_interest_rate = self.interest_rate / 365
        total_interest = position_value * daily_interest_rate * days_held
        
        return {
            'daily_interest': position_value * daily_interest_rate,
            'total_interest': total_interest,
            'interest_rate_percentage': (total_interest / position_value) * 100
        }
    
    def emergency_position_close(self, stock_code, reason):
        """긴급 포지션 청산"""
        position = self.credit_positions.get(stock_code)
        if not position:
            return {"status": "NO_POSITION"}
        
        # 시장가 매도
        emergency_sell = credit_sell_order_tumepok(
            stock_code,
            position['quantity'],
            0,  # 시장가
            position['entry_time'].strftime('%Y%m%d')
        )
        
        emergency_sell['trde_tp'] = '3'  # 시장가 설정
        
        logger.warning(f"Emergency position close for {stock_code}: {reason}")
        
        return emergency_sell
```

### 3. 스마트 주문 관리 시스템

```python
class SmartCreditOrderManager:
    def __init__(self):
        self.pending_orders = {}
        self.order_history = []
    
    def smart_order_execution(self, stock_code, strategy_signal):
        """스마트 신용 주문 실행"""
        # 1. 시장 상황 분석
        market_condition = self.analyze_market_condition()
        
        # 2. 최적 주문 타입 결정
        optimal_order_type = self.determine_optimal_order_type(
            strategy_signal, market_condition
        )
        
        # 3. 분할 주문 전략
        if strategy_signal['position_size'] > 10000000:  # 1천만원 이상
            return self.execute_split_orders(stock_code, strategy_signal)
        else:
            return self.execute_single_order(stock_code, strategy_signal)
    
    def execute_split_orders(self, stock_code, signal):
        """대량 주문 분할 실행"""
        total_quantity = signal['quantity']
        split_count = min(5, max(2, total_quantity // 1000))  # 2~5회 분할
        
        split_results = []
        quantity_per_split = total_quantity // split_count
        
        for i in range(split_count):
            # 마지막 분할에서 나머지 수량 처리
            if i == split_count - 1:
                current_quantity = total_quantity - (quantity_per_split * i)
            else:
                current_quantity = quantity_per_split
            
            # 가격 조정 (시장 충격 최소화)
            adjusted_price = self.adjust_price_for_split(
                signal['entry_price'], i, split_count
            )
            
            order_result = credit_buy_order_tumepok(
                stock_code, current_quantity, adjusted_price
            )
            
            split_results.append(order_result)
            
            # 분할 주문 간 간격
            time.sleep(2)
        
        return {
            'strategy': 'SPLIT_ORDER',
            'split_count': split_count,
            'results': split_results
        }
    
    def manage_partial_fills(self):
        """부분체결 주문 관리"""
        for order_no, order_info in self.pending_orders.items():
            # 주문 상태 확인
            order_status = self.check_order_status(order_no)
            
            if order_status['fill_ratio'] > 0 and order_status['fill_ratio'] < 1:
                # 부분체결 발생
                self.handle_partial_fill(order_no, order_status)
            elif order_status['status'] == 'FILLED':
                # 완전체결
                self.handle_complete_fill(order_no, order_status)
    
    def dynamic_order_adjustment(self, stock_code):
        """동적 주문 조정"""
        current_orders = self.get_pending_orders(stock_code)
        market_data = get_real_time_market_data(stock_code)
        
        for order in current_orders:
            # 호가 스프레드 분석
            spread_analysis = analyze_bid_ask_spread(market_data)
            
            # 주문가격이 시장과 괴리 시 정정
            if spread_analysis['adjustment_needed']:
                new_price = spread_analysis['recommended_price']
                
                modify_result = modify_credit_order_tumepok(
                    order['order_no'], 
                    order['quantity'], 
                    new_price
                )
                
                logger.info(f"Order {order['order_no']} adjusted to {new_price}")
```

### 4. 전략 신용거래 백테스팅

```python
class CreditTradingBacktester:
    def __init__(self):
        self.initial_capital = 10000000  # 1천만원
        self.credit_ratio = 1.5  # 1.5배 레버리지
        self.interest_rate = 0.08
        
    def backtest_credit_tumepok_strategy(self, start_date, end_date):
        """신용거래 전략 전략 백테스팅"""
        results = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_return': 0,
            'max_drawdown': 0,
            'interest_costs': 0,
            'net_profit': 0
        }
        
        # 역사적 데이터 로드
        historical_data = self.load_historical_data(start_date, end_date)
        
        for date, market_data in historical_data.items():
            # 전략 신호 생성
            signals = generate_tumepok_signals(market_data)
            
            for signal in signals:
                if signal['action'] == 'BUY':
                    trade_result = self.simulate_credit_trade(signal, market_data)
                    self.update_backtest_results(results, trade_result)
        
        return self.finalize_backtest_results(results)
    
    def simulate_credit_trade(self, signal, market_data):
        """신용거래 시뮬레이션"""
        position_value = signal['position_size'] * self.credit_ratio
        entry_price = signal['entry_price']
        
        # 보유기간 동안 수익률 계산
        holding_period = signal.get('holding_days', 3)
        exit_price = self.calculate_exit_price(signal, market_data, holding_period)
        
        # 거래 수익률
        trading_return = ((exit_price - entry_price) / entry_price) * 100
        
        # 이자 비용
        interest_cost = self.calculate_interest_for_period(
            position_value, holding_period
        )
        
        # 순수익
        net_return = (trading_return * self.credit_ratio) - interest_cost
        
        return {
            'entry_price': entry_price,
            'exit_price': exit_price,
            'trading_return': trading_return,
            'interest_cost': interest_cost,
            'net_return': net_return,
            'holding_period': holding_period
        }
```

## API 사용 시 주의사항

### 1. 공통 설정
- **엔드포인트**: `/api/dostk/crdordr`
- **인증**: Bearer 토큰 필수
- **Content-Type**: `application/json;charset=UTF-8`

### 2. 신용거래 제한사항
- 신용거래 가능 종목 확인 필수
- 융자 비율 및 한도 확인
- 이자율 및 수수료 고려
- 반대매매 조건 숙지

### 3. 리스크 관리
```python
def validate_credit_order(order_params):
    """신용 주문 유효성 검사"""
    validations = {
        'credit_eligible': check_credit_eligible_stock(order_params['stk_cd']),
        'margin_sufficient': check_margin_sufficiency(order_params),
        'position_limit': check_position_limit(order_params),
        'interest_impact': calculate_interest_impact(order_params)
    }
    
    return all(validations.values()), validations
```

### 4. 에러 처리
```python
def handle_credit_order_error(error_response):
    """신용 주문 에러 처리"""
    error_code = error_response.get('error_code')
    
    error_handlers = {
        'INSUFFICIENT_MARGIN': lambda: increase_margin_deposit(),
        'CREDIT_LIMIT_EXCEEDED': lambda: reduce_position_size(),
        'NON_CREDIT_STOCK': lambda: switch_to_cash_order(),
        'MARKET_CLOSED': lambda: queue_for_next_session()
    }
    
    if error_code in error_handlers:
        return error_handlers[error_code]()
    else:
        logger.error(f"Unhandled credit order error: {error_code}")
        return {"status": "ERROR", "action": "MANUAL_REVIEW"}
```

## 전략 신용거래 최적화 전략

### 1. 레버리지 최적화
- 시장 변동성에 따른 동적 레버리지 조절
- 종목별 신용 등급에 따른 차등 적용
- 포트폴리오 전체 리스크 고려

### 2. 이자 비용 최소화
- 단기 보유 전략으로 이자 부담 축소
- 수익률 대비 이자 비용 효율성 분석
- 조기 청산을 통한 이자 절약

### 3. 청산 타이밍 최적화
- 기술적 지표 기반 청산 신호
- 수익률 목표 대비 이자 비용 고려
- 시장 상황 변화에 따른 유연한 청산

이러한 신용주문 API들을 체계적으로 활용하면 전략 전략에서 레버리지 효과를 극대화하면서도 리스크를 효과적으로 관리할 수 있습니다.