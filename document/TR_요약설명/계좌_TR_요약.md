# 계좌 TR 문서 요약

## 개요
계좌 TR은 키움증권 REST API를 통해 계좌 관련 모든 정보를 조회하고 관리하는 기능을 제공합니다. 예수금, 잔고, 주문/체결 내역, 손익 현황, 주문 가능 금액 등 투자에 필요한 핵심 계좌 정보를 실시간으로 확인할 수 있습니다.

## 공통 사항

### API 설정
- **엔드포인트**: `/api/dostk/acnt`
- **메서드**: POST
- **인증**: Bearer 토큰 필요
- **서버**:
  - 실전: `https://api.kiwoom.com`
  - 모의: `https://mockapi.kiwoom.com`

### 거래소 구분
- 0: 통합
- 1: KRX (한국거래소)
- 2: NXT (넥스트트레이드)

## 주요 기능 분류

### 1. 예수금 및 자산 현황

#### KT00001 - 예수금상세현황요청
- **목적**: 계좌의 전체 예수금 및 출금/주문 가능 금액 조회
- **주요 정보**:
  - 예수금, 증거금 현금
  - 출금가능금액, 주문가능금액
  - 증거금률별 주문가능금액 (20%, 30%, 40%, 50%, 60%, 100%)
  - D+1, D+2 추정예수금
  - 미수금, 신용이자미납, 융자금
  - 신용담보비율
  - 외화예수금 (통화별)
- **활용**: 자금 현황 파악, 주문 가능 여부 확인

#### KT00002 - 일별추정예탁자산현황요청
- **목적**: 일자별 예탁자산 변동 추이
- **활용**: 자산 증감 분석

#### KT00003 - 추정자산조회요청
- **목적**: 현재 시점 추정 자산 총액
- **활용**: 실시간 자산 평가

### 2. 계좌 평가 및 잔고

#### KT00004 - 계좌평가현황요청
- **목적**: 계좌 전체 평가 현황 및 보유 종목별 상세
- **주요 정보**:
  - 예수금, D+2 추정예수금
  - 유가잔고평가액, 예탁자산평가액
  - 총매입금액, 추정예탁자산
  - 투자손익 (당일/당월/누적)
  - 손익률 (당일/당월/누적)
  - **종목별 상세**:
    - 보유수량, 평균단가, 현재가
    - 평가금액, 손익금액, 손익률
    - 매입금액, 결제잔고
    - 전일/금일 매수/매도 수량
- **활용**: 포트폴리오 전체 성과 평가

#### KT00005 - 체결잔고요청
- **목적**: 체결 기준 잔고 현황
- **활용**: 실제 보유 수량 확인

#### KT00018 - 계좌평가잔고내역요청
- **목적**: 평가 기준 잔고 상세
- **활용**: 종목별 평가 손익 분석

### 3. 주문 및 체결 관리

#### KA10075 - 미체결요청
- **목적**: 미체결 주문 내역 조회
- **검색 조건**:
  - 전체/종목별
  - 매매구분 (전체/매도/매수)
  - 거래소별
- **주요 정보**:
  - 주문번호, 종목코드/명
  - 주문수량, 주문가격
  - 미체결수량
  - 체결누계금액
  - 현재가, 매도/매수 호가
  - 스톱가 (스톱지정가 주문)
- **활용**: 대기 주문 관리, 주문 취소/정정

#### KA10076 - 체결요청
- **목적**: 체결 완료 내역 조회
- **주요 정보**:
  - 체결가, 체결량
  - 당일매매수수료, 세금
  - 주문상태, 매매구분
  - 주문시간
- **활용**: 체결 확인, 매매 내역 관리

#### KA10088 - 미체결 분할주문 상세
- **목적**: 분할 주문의 미체결 상세
- **활용**: 대량 주문 추적

#### KT00007 - 계좌별주문체결내역상세요청
- **목적**: 주문부터 체결까지 전체 이력
- **활용**: 주문 프로세스 추적

### 4. 손익 분석

#### KA10072 - 일자별종목별실현손익요청(일자)
- **목적**: 특정 일자의 종목별 실현손익
- **활용**: 일별 매매 성과 분석

#### KA10073 - 일자별종목별실현손익요청(기간)
- **목적**: 기간별 종목별 실현손익
- **활용**: 기간 성과 분석

#### KA10074 - 일자별실현손익요청
- **목적**: 일자별 전체 실현손익
- **활용**: 일별 수익률 추이

#### KA10077 - 당일실현손익상세요청
- **목적**: 당일 실현손익 상세
- **활용**: 당일 매매 결과 확인

#### KA10085 - 계좌수익률요청
- **목적**: 계좌 전체 수익률 통계
- **활용**: 투자 성과 평가

#### KT00016 - 일별계좌수익률상세현황요청
- **목적**: 일별 수익률 상세 추이
- **활용**: 수익률 변동 분석

### 5. 주문 가능 금액 조회

#### KT00010 - 주문인출가능금액요청
- **목적**: 특정 종목 주문 시 가능 금액/수량
- **입력 정보**:
  - 종목코드
  - 매매구분 (매도/매수)
  - 매수가격
- **응답 정보**:
  - 증거금률별 주문가능금액/수량
  - 예수금, 대용금, 미수금
  - 인출가능금액
  - D+2 추정예수금
- **활용**: 주문 전 가능 수량 확인

#### KT00011 - 증거금율별주문가능수량조회요청
- **목적**: 증거금률별 주문 가능 수량
- **활용**: 증거금 종목 매매 계획

#### KT00012 - 신용보증금율별주문가능수량조회요청
- **목적**: 신용거래 주문 가능 수량
- **활용**: 신용매매 계획

### 6. 거래 내역 및 분석

#### KA10170 - 당일매매일지요청
- **목적**: 당일 전체 매매 활동 기록
- **활용**: 매매 일지 작성

#### KT00008 - 계좌별익일결제예정내역요청
- **목적**: 다음날 결제 예정 내역
- **활용**: 자금 계획 수립

#### KT00013 - 증거금세부내역조회요청
- **목적**: 증거금 상세 내역
- **활용**: 증거금 관리

#### KT00015 - 위탁종합거래내역요청
- **목적**: 종합 거래 내역
- **활용**: 거래 이력 관리

#### KT00017 - 계좌별당일현황요청
- **목적**: 당일 계좌 활동 요약
- **활용**: 일일 리포트

## 시스템 활용 가이드

### 1. 계좌 상태 모니터링
```python
class AccountMonitor:
    def __init__(self):
        self.account_info = {}
        
    def update_account_status(self):
        """계좌 현황 업데이트"""
        # KT00001: 예수금 조회
        deposit_info = self.get_deposit_status()
        
        # KT00004: 계좌평가 조회
        evaluation = self.get_account_evaluation()
        
        # KA10075: 미체결 조회
        pending_orders = self.get_pending_orders()
        
        return {
            'cash': deposit_info['entr'],
            'order_available': deposit_info['ord_alow_amt'],
            'total_assets': evaluation['aset_evlt_amt'],
            'profit_rate': evaluation['lspft_rt'],
            'pending_count': len(pending_orders)
        }
```

### 2. 주문 가능 여부 체크
```python
def check_order_possibility(stock_code, price, quantity):
    """주문 가능 여부 및 수량 확인"""
    # KT00010 호출
    params = {
        'stk_cd': stock_code,
        'trde_tp': '2',  # 매수
        'uv': str(price),
        'trde_qty': str(quantity)
    }
    
    result = call_kt00010(params)
    
    # 증거금률별 체크
    if result['profa_100ord_alowq'] >= quantity:
        return True, '100%'
    elif result['profa_40ord_alowq'] >= quantity:
        return True, '40%'
    else:
        return False, None
```

### 3. 실시간 손익 관리
```python
class ProfitLossManager:
    def __init__(self, daily_loss_limit=-200000):
        self.daily_loss_limit = daily_loss_limit
        
    def check_daily_loss(self):
        """일일 손실 한도 체크"""
        # KA10077: 당일 실현손익
        daily_pl = self.get_daily_realized_pl()
        
        if daily_pl <= self.daily_loss_limit:
            return False, "일일 손실 한도 도달"
        
        return True, daily_pl
    
    def get_position_pl(self, stock_code):
        """포지션별 손익률"""
        # KT00004: 계좌평가현황
        positions = self.get_account_positions()
        
        for pos in positions['stk_acnt_evlt_prst']:
            if pos['stk_cd'] == stock_code:
                return float(pos['pl_rt'])
        
        return 0.0
```

### 4. 주문 실행 및 추적
```python
class OrderManager:
    def execute_buy_order(self, stock_code, price, quantity):
        """매수 주문 실행"""
        # 1. 주문 가능 확인 (KT00010)
        can_order, margin_rate = check_order_possibility(
            stock_code, price, quantity
        )
        
        if not can_order:
            return False, "주문 가능 금액 부족"
        
        # 2. 주문 실행 (주문 TR 호출)
        order_result = place_order(stock_code, price, quantity)
        
        # 3. 체결 확인 (KA10076)
        execution = self.check_execution(order_result['ord_no'])
        
        return True, execution
    
    def track_pending_orders(self):
        """미체결 주문 추적"""
        # KA10075: 미체결 조회
        pending = self.get_pending_orders()
        
        for order in pending:
            # 현재가 대비 주문가 체크
            if self.should_cancel_order(order):
                self.cancel_order(order['ord_no'])
```

### 5. 포트폴리오 분석
```python
def analyze_portfolio():
    """포트폴리오 성과 분석"""
    # KT00004: 계좌평가현황
    evaluation = get_account_evaluation()
    
    portfolio = {
        'total_investment': evaluation['tot_pur_amt'],
        'current_value': evaluation['tot_est_amt'],
        'total_profit': evaluation['lspft'],
        'profit_rate': evaluation['lspft_rt'],
        'positions': []
    }
    
    # 종목별 분석
    for stock in evaluation['stk_acnt_evlt_prst']:
        position = {
            'code': stock['stk_cd'],
            'name': stock['stk_nm'],
            'quantity': stock['rmnd_qty'],
            'avg_price': stock['avg_prc'],
            'current_price': stock['cur_prc'],
            'profit_rate': stock['pl_rt'],
            'weight': float(stock['evlt_amt']) / float(evaluation['tot_est_amt']) * 100
        }
        portfolio['positions'].append(position)
    
    return portfolio
```

## 주요 지표 설명

### 예수금 관련
- **예수금**: 계좌에 입금된 현금
- **D+1/D+2 추정예수금**: 결제일 기준 예상 예수금
- **출금가능금액**: 즉시 출금 가능한 금액
- **주문가능금액**: 주식 매수에 사용 가능한 금액

### 평가 관련
- **유가잔고평가액**: 보유 주식의 현재가 평가액
- **예탁자산평가액**: 예수금 + 유가잔고평가액
- **총매입금액**: 보유 주식 매입 총액
- **평가손익**: 현재가 - 매입가

### 손익률
- **당일손익률**: 당일 매매로 인한 손익률
- **당월손익률**: 당월 누적 손익률
- **누적손익률**: 전체 기간 손익률

### 증거금
- **증거금률**: 주식 매수 시 필요한 현금 비율
- **20%/30%/40%/50%/60%/100%**: 각 증거금률별 주문 가능 금액

## 주의사항

### API 호출 제한
- 초당 호출 횟수 제한
- 연속조회 시 cont-yn, next-key 활용

### 데이터 정합성
- 실시간 시세와 계좌 정보 간 시차 존재
- 체결 직후 잔고 반영까지 지연 가능

### 거래소별 차이
- KRX/NXT 거래소별 수수료 차이
- 거래 시간 및 제한 사항 상이

### 세금 및 수수료
- 매매수수료: 증권사별 상이
- 거래세: 매도 시 0.23%
- 양도소득세: 대주주 해당 시

## 구현 시 고려사항

### 실시간 업데이트
- 주요 계좌 정보 주기적 갱신
- 체결 발생 시 즉시 잔고 업데이트

### 에러 처리
- API 응답 실패 시 재시도
- 잔고 부족, 주문 실패 등 예외 처리

### 로깅
- 모든 주문/체결 이력 기록
- 손익 변동 추적
- 오류 발생 시 상세 로그

### 성능 최적화
- 필요한 정보만 선택적 조회
- 캐싱 전략 구현
- 배치 처리 활용