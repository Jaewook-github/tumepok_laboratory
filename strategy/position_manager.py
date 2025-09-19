# -*- coding: utf-8 -*-
"""
포지션 관리자 (Position Manager)
투매폭 매수 후 포지션의 손절/익절을 관리합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from utils.enhanced_logging import log_info, log_error, log_debug, log_warning


class BuyStageInfo:
    """매수 단계 정보"""
    
    def __init__(self, stage: str, price: float, quantity: int, amount: float):
        self.stage = stage  # 1차, 2차, 3차
        self.price = price
        self.quantity = quantity
        self.amount = amount
        self.buy_time = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            'stage': self.stage,
            'price': self.price,
            'quantity': self.quantity,
            'amount': self.amount,
            'buy_time': self.buy_time.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        stage_info = cls(
            stage=data['stage'],
            price=data['price'],
            quantity=data['quantity'],
            amount=data['amount']
        )
        stage_info.buy_time = datetime.fromisoformat(data['buy_time'])
        return stage_info


class PositionInfo:
    """포지션 정보"""
    
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.buy_stages: List[BuyStageInfo] = []
        self.total_quantity = 0
        self.total_amount = 0.0
        self.weighted_avg_price = 0.0
        self.current_price = 0.0
        self.profit_rate = 0.0
        self.profit_amount = 0.0
        
        # 트레일링 스탑 관련
        self.trailing_activated = False
        self.trailing_high = 0.0
        self.trailing_trigger_rate = 2.0  # 2% 수익 시 트레일링 발동
        self.trailing_sell_rate = -1.0    # 고점 대비 -1% 하락 시 매도
        
        # 손절 관련
        self.stop_loss_rate = -2.0  # -2% 손절
        
        # 상태
        self.status = "HOLDING"  # HOLDING, TRAILING, SOLD
        self.create_time = datetime.now()
        self.last_update = datetime.now()
    
    def add_buy_stage(self, stage_info: BuyStageInfo):
        """매수 단계 추가"""
        self.buy_stages.append(stage_info)
        self.total_quantity += stage_info.quantity
        self.total_amount += stage_info.amount
        
        # 가중평균 매입가 재계산
        self.calculate_weighted_avg_price()
        
        log_debug(f"{self.stock_code} {stage_info.stage} 매수 추가: {stage_info.quantity}주 @ {stage_info.price:,}원")
    
    def calculate_weighted_avg_price(self):
        """가중평균 매입가 계산"""
        if self.total_amount > 0:
            self.weighted_avg_price = self.total_amount / self.total_quantity
        else:
            self.weighted_avg_price = 0.0
    
    def update_current_price(self, current_price: float):
        """현재가 업데이트"""
        self.current_price = current_price
        self.last_update = datetime.now()
        
        # 수익률 계산 (수수료 포함)
        if self.weighted_avg_price > 0:
            from utils.calculator import TumepokCalculator
            self.profit_rate = TumepokCalculator.calculate_profit_rate(self.weighted_avg_price, current_price)
            self.profit_amount = (current_price - self.weighted_avg_price) * self.total_quantity
        
        # 트레일링 스탑 관리
        self.update_trailing_stop()
    
    def update_trailing_stop(self):
        """트레일링 스탑 업데이트"""
        # 트레일링 발동 조건 확인
        if not self.trailing_activated and self.profit_rate >= self.trailing_trigger_rate:
            self.trailing_activated = True
            self.trailing_high = self.current_price
            log_info(f"{self.stock_code} 트레일링 스탑 발동: {self.profit_rate:.2f}%")
        
        # 트레일링 고점 업데이트
        if self.trailing_activated and self.current_price > self.trailing_high:
            self.trailing_high = self.current_price
    
    def check_sell_conditions(self) -> Optional[str]:
        """매도 조건 확인"""
        # 손절 확인
        if self.profit_rate <= self.stop_loss_rate:
            return "STOP_LOSS"
        
        # 트레일링 매도 확인
        if self.trailing_activated:
            trailing_drop_rate = ((self.trailing_high - self.current_price) / self.trailing_high) * 100
            if trailing_drop_rate >= abs(self.trailing_sell_rate):
                return "TRAILING_SELL"
        
        return None
    
    def get_sell_quantity(self) -> int:
        """매도 수량 반환"""
        return self.total_quantity
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'stock_code': self.stock_code,
            'buy_stages': [stage.to_dict() for stage in self.buy_stages],
            'total_quantity': self.total_quantity,
            'total_amount': self.total_amount,
            'weighted_avg_price': self.weighted_avg_price,
            'current_price': self.current_price,
            'profit_rate': self.profit_rate,
            'profit_amount': self.profit_amount,
            'trailing_activated': self.trailing_activated,
            'trailing_high': self.trailing_high,
            'trailing_trigger_rate': self.trailing_trigger_rate,
            'trailing_sell_rate': self.trailing_sell_rate,
            'stop_loss_rate': self.stop_loss_rate,
            'status': self.status,
            'create_time': self.create_time.isoformat(),
            'last_update': self.last_update.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """딕셔너리에서 생성"""
        position = cls(data['stock_code'])
        
        # 매수 단계 복원
        for stage_data in data['buy_stages']:
            stage_info = BuyStageInfo.from_dict(stage_data)
            position.buy_stages.append(stage_info)
        
        position.total_quantity = data['total_quantity']
        position.total_amount = data['total_amount']
        position.weighted_avg_price = data['weighted_avg_price']
        position.current_price = data['current_price']
        position.profit_rate = data['profit_rate']
        position.profit_amount = data['profit_amount']
        position.trailing_activated = data['trailing_activated']
        position.trailing_high = data['trailing_high']
        position.trailing_trigger_rate = data['trailing_trigger_rate']
        position.trailing_sell_rate = data['trailing_sell_rate']
        position.stop_loss_rate = data['stop_loss_rate']
        position.status = data['status']
        position.create_time = datetime.fromisoformat(data['create_time'])
        position.last_update = datetime.fromisoformat(data['last_update'])
        
        return position


class PositionManager:
    """포지션 관리자"""
    
    def __init__(self):
        self.positions: Dict[str, PositionInfo] = {}
        
        # 기본 설정
        self.stop_loss_rate = -2.0
        self.trailing_trigger_rate = 2.0
        self.trailing_sell_rate = -1.0
        
        log_info("포지션 관리자 초기화 완료")
    
    def add_position(self, stock_code: str, stage: str, price: float, 
                    quantity: int, amount: float) -> bool:
        """포지션 추가 또는 기존 포지션에 매수 단계 추가"""
        try:
            # 기존 포지션이 있는지 확인
            if stock_code not in self.positions:
                self.positions[stock_code] = PositionInfo(stock_code)
            
            position = self.positions[stock_code]
            
            # 설정값 적용
            position.stop_loss_rate = self.stop_loss_rate
            position.trailing_trigger_rate = self.trailing_trigger_rate
            position.trailing_sell_rate = self.trailing_sell_rate
            
            # 매수 단계 정보 생성
            stage_info = BuyStageInfo(stage, price, quantity, amount)
            
            # 포지션에 추가
            position.add_buy_stage(stage_info)
            
            log_info(f"포지션 추가: {stock_code} {stage} {quantity}주 @ {price:,}원")
            return True
            
        except Exception as e:
            log_error(f"포지션 추가 실패 {stock_code}: {str(e)}")
            return False
    
    def update_position(self, stock_code: str, current_price: float) -> Optional[str]:
        """포지션 업데이트 및 매도 신호 확인"""
        try:
            if stock_code not in self.positions:
                return None
            
            position = self.positions[stock_code]
            position.update_current_price(current_price)
            
            # 매도 조건 확인
            sell_signal = position.check_sell_conditions()
            
            if sell_signal:
                log_info(f"{stock_code} 매도 신호: {sell_signal} (수익률: {position.profit_rate:.2f}%)")
            
            return sell_signal
            
        except Exception as e:
            log_error(f"포지션 업데이트 실패 {stock_code}: {str(e)}")
            return None
    
    def remove_position(self, stock_code: str, reason: str = "SOLD") -> bool:
        """포지션 제거"""
        try:
            if stock_code in self.positions:
                position = self.positions[stock_code]
                position.status = reason
                
                log_info(f"포지션 제거: {stock_code} (사유: {reason}, 수익률: {position.profit_rate:.2f}%)")
                
                del self.positions[stock_code]
                return True
            else:
                log_warning(f"제거할 포지션이 없음: {stock_code}")
                return False
                
        except Exception as e:
            log_error(f"포지션 제거 실패 {stock_code}: {str(e)}")
            return False
    
    def get_position(self, stock_code: str) -> Optional[PositionInfo]:
        """포지션 정보 조회"""
        return self.positions.get(stock_code)
    
    def get_all_positions(self) -> Dict[str, PositionInfo]:
        """모든 포지션 조회"""
        return self.positions.copy()
    
    def get_positions_dataframe(self) -> pd.DataFrame:
        """포지션을 DataFrame으로 변환"""
        try:
            if not self.positions:
                return pd.DataFrame(columns=[
                    '종목코드', '매입가', '현재가', '수량', '수익률(%)', 
                    '수익금액', '트레일링', '상태'
                ])
            
            data = []
            for stock_code, position in self.positions.items():
                data.append({
                    '종목코드': stock_code,
                    '매입가': f"{position.weighted_avg_price:,.0f}",
                    '현재가': f"{position.current_price:,.0f}",
                    '수량': f"{position.total_quantity:,}",
                    '수익률(%)': f"{position.profit_rate:+.2f}",
                    '수익금액': f"{position.profit_amount:+,.0f}",
                    '트레일링': "활성" if position.trailing_activated else "대기",
                    '상태': position.status
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            log_error(f"포지션 DataFrame 생성 실패: {str(e)}")
            return pd.DataFrame()
    
    def get_total_profit(self) -> dict:
        """전체 수익 정보"""
        try:
            total_profit_amount = 0.0
            total_profit_rate = 0.0
            total_positions = len(self.positions)
            
            if total_positions > 0:
                for position in self.positions.values():
                    total_profit_amount += position.profit_amount
                    total_profit_rate += position.profit_rate
                
                avg_profit_rate = total_profit_rate / total_positions
            else:
                avg_profit_rate = 0.0
            
            return {
                'total_profit_amount': total_profit_amount,
                'avg_profit_rate': avg_profit_rate,
                'total_positions': total_positions,
                'profitable_positions': len([p for p in self.positions.values() if p.profit_rate > 0]),
                'loss_positions': len([p for p in self.positions.values() if p.profit_rate < 0])
            }
            
        except Exception as e:
            log_error(f"전체 수익 계산 실패: {str(e)}")
            return {}
    
    def get_statistics(self) -> dict:
        """포지션 관리 통계"""
        try:
            total_positions = len(self.positions)
            trailing_positions = len([p for p in self.positions.values() if p.trailing_activated])
            
            profit_info = self.get_total_profit()
            
            return {
                'total_positions': total_positions,
                'trailing_positions': trailing_positions,
                'profit_positions': profit_info.get('profitable_positions', 0),
                'loss_positions': profit_info.get('loss_positions', 0),
                'total_profit_amount': profit_info.get('total_profit_amount', 0),
                'avg_profit_rate': profit_info.get('avg_profit_rate', 0),
                'settings': {
                    'stop_loss_rate': self.stop_loss_rate,
                    'trailing_trigger_rate': self.trailing_trigger_rate,
                    'trailing_sell_rate': self.trailing_sell_rate
                }
            }
            
        except Exception as e:
            log_error(f"포지션 통계 조회 실패: {str(e)}")
            return {}
    
    def update_settings(self, stop_loss_rate: float = None,
                       trailing_trigger_rate: float = None,
                       trailing_sell_rate: float = None):
        """설정 업데이트"""
        try:
            if stop_loss_rate is not None:
                self.stop_loss_rate = stop_loss_rate
            
            if trailing_trigger_rate is not None:
                self.trailing_trigger_rate = trailing_trigger_rate
            
            if trailing_sell_rate is not None:
                self.trailing_sell_rate = trailing_sell_rate
            
            # 기존 포지션에도 설정 적용
            for position in self.positions.values():
                if stop_loss_rate is not None:
                    position.stop_loss_rate = stop_loss_rate
                if trailing_trigger_rate is not None:
                    position.trailing_trigger_rate = trailing_trigger_rate
                if trailing_sell_rate is not None:
                    position.trailing_sell_rate = trailing_sell_rate
            
            log_info("포지션 관리자 설정 업데이트 완료")
            
        except Exception as e:
            log_error(f"설정 업데이트 실패: {str(e)}")
    
    def force_sell_position(self, stock_code: str, reason: str = "MANUAL") -> bool:
        """강제 매도"""
        try:
            if stock_code in self.positions:
                position = self.positions[stock_code]
                
                log_info(f"강제 매도: {stock_code} (사유: {reason}, 수익률: {position.profit_rate:.2f}%)")
                
                self.remove_position(stock_code, reason)
                return True
            else:
                log_warning(f"강제 매도할 포지션이 없음: {stock_code}")
                return False
                
        except Exception as e:
            log_error(f"강제 매도 실패 {stock_code}: {str(e)}")
            return False
    
    def save_positions(self, filepath: str) -> bool:
        """포지션 데이터 저장"""
        try:
            data = {}
            for stock_code, position in self.positions.items():
                data[stock_code] = position.to_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            log_info(f"포지션 데이터 저장 완료: {filepath}")
            return True
            
        except Exception as e:
            log_error(f"포지션 데이터 저장 실패: {str(e)}")
            return False
    
    def load_positions(self, filepath: str) -> bool:
        """포지션 데이터 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.positions.clear()
            
            for stock_code, position_data in data.items():
                position = PositionInfo.from_dict(position_data)
                self.positions[stock_code] = position
            
            log_info(f"포지션 데이터 로드 완료: {len(self.positions)}개 포지션")
            return True
            
        except FileNotFoundError:
            log_info("포지션 데이터 파일이 없습니다")
            return True
        except Exception as e:
            log_error(f"포지션 데이터 로드 실패: {str(e)}")
            return False
    
    def cleanup_old_positions(self, days: int = 30) -> int:
        """오래된 포지션 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            removed_count = 0
            
            positions_to_remove = []
            for stock_code, position in self.positions.items():
                if position.last_update < cutoff_date:
                    positions_to_remove.append(stock_code)
            
            for stock_code in positions_to_remove:
                self.remove_position(stock_code, "EXPIRED")
                removed_count += 1
            
            if removed_count > 0:
                log_info(f"오래된 포지션 {removed_count}개 정리 완료")
            
            return removed_count
            
        except Exception as e:
            log_error(f"포지션 정리 실패: {str(e)}")
            return 0
    
    def get_position_summary(self, stock_code: str) -> dict:
        """포지션 요약 정보"""
        try:
            if stock_code not in self.positions:
                return {}
            
            position = self.positions[stock_code]
            
            return {
                'stock_code': stock_code,
                'buy_stages_count': len(position.buy_stages),
                'buy_stages': [stage.stage for stage in position.buy_stages],
                'total_quantity': position.total_quantity,
                'weighted_avg_price': position.weighted_avg_price,
                'current_price': position.current_price,
                'profit_rate': position.profit_rate,
                'profit_amount': position.profit_amount,
                'trailing_activated': position.trailing_activated,
                'trailing_high': position.trailing_high,
                'status': position.status,
                'holding_days': (datetime.now() - position.create_time).days
            }
            
        except Exception as e:
            log_error(f"포지션 요약 조회 실패 {stock_code}: {str(e)}")
            return {}
    
    def check_all_positions(self) -> List[Tuple[str, str]]:
        """모든 포지션의 매도 조건 확인"""
        try:
            sell_signals = []
            
            for stock_code, position in self.positions.items():
                sell_signal = position.check_sell_conditions()
                if sell_signal:
                    sell_signals.append((stock_code, sell_signal))
            
            return sell_signals
            
        except Exception as e:
            log_error(f"전체 포지션 확인 실패: {str(e)}")
            return []