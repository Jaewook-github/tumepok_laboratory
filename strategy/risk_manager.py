# -*- coding: utf-8 -*-
"""
리스크 관리자 (Risk Manager)
연속상승일수별 포지션 크기 조정 및 전체 리스크 관리를 담당합니다.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from utils.enhanced_logging import log_info, log_error, log_debug, log_warning


class RiskManager:
    """리스크 관리자"""
    
    def __init__(self):
        # 기본 리스크 설정
        self.daily_loss_limit = -200000  # 일일 손실 한도 (원)
        self.max_tracking_stocks = 100    # 최대 추적 종목 수
        self.max_position_stocks = 30    # 최대 포지션 종목 수
        self.max_single_position = 500000  # 종목별 최대 투자금액 (원)
        
        # 연속상승일수별 포지션 축소율
        self.position_ratios = {
            1: 1.0,    # 1일 상승: 100%
            2: 1.0,    # 2일 연속: 100%
            3: 0.8,    # 3일 연속: 80%
            4: 0.5,    # 4일 연속: 50%
            5: 0.0,    # 5일 이상: 진입 금지
        }
        
        # 상승률별 추가 축소율
        self.rise_rate_ratios = {
            50: 1.0,   # 50% 미만: 100%
            70: 0.8,   # 50-70%: 80%
            100: 0.5,  # 70-100%: 50%
            999: 0.3   # 100% 이상: 30%
        }
        
        # 일일 통계
        self.daily_stats = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_profit': 0.0,
            'total_loss': 0.0,
            'trade_count': 0,
            'buy_count': 0,
            'sell_count': 0
        }
        
        # 거래 기록
        self.trade_history = []
        
        log_info("리스크 관리자 초기화 완료")
    
    def calculate_position_size(self, base_amount: float, rise_days: int, 
                              rise_rate: float, current_positions: int = 0) -> dict:
        """포지션 크기 계산"""
        try:
            # 기본 정보
            result = {
                'base_amount': base_amount,
                'rise_days': rise_days,
                'rise_rate': rise_rate,
                'current_positions': current_positions,
                'day_ratio': 1.0,
                'rise_ratio': 1.0,
                'position_ratio': 1.0,
                'final_ratio': 1.0,
                'final_amount': 0,
                'risk_level': 'LOW',
                'allowed': True,
                'reason': ''
            }
            
            # 1. 연속상승일수별 축소
            day_ratio = self.get_day_ratio(rise_days)
            result['day_ratio'] = day_ratio
            
            # 2. 상승률별 축소
            rise_ratio = self.get_rise_rate_ratio(rise_rate)
            result['rise_ratio'] = rise_ratio
            
            # 3. 포지션 수별 축소
            position_ratio = self.get_position_ratio(current_positions)
            result['position_ratio'] = position_ratio
            
            # 4. 최종 비율 계산
            final_ratio = day_ratio * rise_ratio * position_ratio
            result['final_ratio'] = final_ratio
            
            # 5. 최종 금액 계산
            final_amount = int(base_amount * final_ratio)
            result['final_amount'] = final_amount
            
            # 6. 리스크 레벨 판단
            result['risk_level'] = self.get_risk_level(rise_days, rise_rate, final_ratio)
            
            # 7. 진입 허용 여부 확인
            allowed, reason = self.check_entry_allowed(rise_days, rise_rate, final_amount, current_positions)
            result['allowed'] = allowed
            result['reason'] = reason
            
            log_debug(f"포지션 크기 계산: {base_amount} * {final_ratio:.2f} = {final_amount}")
            
            return result
            
        except Exception as e:
            log_error(f"포지션 크기 계산 실패: {str(e)}")
            return {
                'base_amount': base_amount,
                'final_amount': 0,
                'allowed': False,
                'reason': f'계산 오류: {str(e)}'
            }
    
    def get_day_ratio(self, rise_days: int) -> float:
        """연속상승일수별 비율"""
        try:
            # 설정된 구간에서 찾기
            for max_days in sorted(self.position_ratios.keys()):
                if rise_days <= max_days:
                    return self.position_ratios[max_days]
            
            # 최대 구간을 초과하면 0 (진입 금지)
            return 0.0
            
        except Exception as e:
            log_error(f"연속상승일수별 비율 계산 실패: {str(e)}")
            return 0.0
    
    def get_rise_rate_ratio(self, rise_rate: float) -> float:
        """상승률별 비율"""
        try:
            # 설정된 구간에서 찾기
            for max_rate in sorted(self.rise_rate_ratios.keys()):
                if rise_rate < max_rate:
                    return self.rise_rate_ratios[max_rate]
            
            # 최대 구간을 초과하면 최소 비율
            return min(self.rise_rate_ratios.values())
            
        except Exception as e:
            log_error(f"상승률별 비율 계산 실패: {str(e)}")
            return 1.0
    
    def get_position_ratio(self, current_positions: int) -> float:
        """포지션 수별 비율"""
        try:
            # 포지션이 많을수록 축소
            if current_positions >= 8:
                return 0.5
            elif current_positions >= 5:
                return 0.7
            elif current_positions >= 3:
                return 0.9
            else:
                return 1.0
                
        except Exception as e:
            log_error(f"포지션 수별 비율 계산 실패: {str(e)}")
            return 1.0
    
    def get_risk_level(self, rise_days: int, rise_rate: float, final_ratio: float) -> str:
        """리스크 레벨 판단"""
        try:
            # 고위험 조건
            if rise_days >= 5 or rise_rate >= 100 or final_ratio <= 0.3:
                return 'HIGH'
            
            # 중위험 조건
            elif rise_days >= 3 or rise_rate >= 70 or final_ratio <= 0.6:
                return 'MEDIUM'
            
            # 저위험
            else:
                return 'LOW'
                
        except Exception as e:
            log_error(f"리스크 레벨 판단 실패: {str(e)}")
            return 'HIGH'
    
    def check_entry_allowed(self, rise_days: int, rise_rate: float, 
                           amount: int, current_positions: int) -> Tuple[bool, str]:
        """진입 허용 여부 확인"""
        try:
            # 1. 연속상승일수 확인
            if rise_days >= 5:
                return False, f"연속상승일수 초과 ({rise_days}일)"
            
            # 2. 최대 포지션 수 확인
            if current_positions >= self.max_position_stocks:
                return False, f"최대 포지션 수 초과 ({current_positions}/{self.max_position_stocks})"
            
            # 3. 종목별 최대 투자금액 확인
            if amount > self.max_single_position:
                return False, f"종목별 최대 투자금액 초과 ({amount:,}/{self.max_single_position:,})"
            
            # 4. 일일 손실 한도 확인
            if self.daily_stats['total_profit'] <= self.daily_loss_limit:
                return False, f"일일 손실 한도 도달 ({self.daily_stats['total_profit']:,}/{self.daily_loss_limit:,})"
            
            # 5. 최소 투자금액 확인
            if amount < 50000:  # 5만원 미만
                return False, f"최소 투자금액 미달 ({amount:,})"
            
            return True, "진입 허용"
            
        except Exception as e:
            log_error(f"진입 허용 여부 확인 실패: {str(e)}")
            return False, f"확인 오류: {str(e)}"
    
    def should_stop_trading(self) -> Tuple[bool, str]:
        """거래 중단 여부 판단"""
        try:
            # 1. 일일 손실 한도 확인
            if self.daily_stats['total_profit'] <= self.daily_loss_limit:
                return True, f"일일 손실 한도 도달 ({self.daily_stats['total_profit']:,})"
            
            # 2. 연속 손실 확인
            recent_trades = self.trade_history[-5:] if len(self.trade_history) >= 5 else self.trade_history
            if len(recent_trades) >= 3:
                recent_losses = [trade for trade in recent_trades if trade.get('profit', 0) < 0]
                if len(recent_losses) >= 3:
                    return True, "연속 손실 발생 (3회 이상)"
            
            # 3. 시간대 확인 (장 마감 30분 전)
            current_time = datetime.now().time()
            if current_time.hour == 15 and current_time.minute >= 0:  # 15:00 이후
                return True, "장 마감 시간 접근"
            
            return False, "거래 계속"
            
        except Exception as e:
            log_error(f"거래 중단 여부 판단 실패: {str(e)}")
            return True, f"판단 오류: {str(e)}"
    
    def record_trade(self, trade_type: str, stock_code: str, amount: float, 
                    profit: float = 0, **kwargs):
        """거래 기록"""
        try:
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'type': trade_type,  # BUY, SELL
                'stock_code': stock_code,
                'amount': amount,
                'profit': profit,
                **kwargs
            }
            
            self.trade_history.append(trade_record)
            
            # 일일 통계 업데이트
            self.update_daily_stats(trade_type, amount, profit)
            
            log_debug(f"거래 기록: {trade_type} {stock_code} {amount:,}원 (수익: {profit:+,.0f}원)")
            
        except Exception as e:
            log_error(f"거래 기록 실패: {str(e)}")
    
    def update_daily_stats(self, trade_type: str, amount: float, profit: float):
        """일일 통계 업데이트"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 날짜가 바뀌면 통계 초기화
            if self.daily_stats['date'] != today:
                self.reset_daily_stats()
            
            # 거래 수 증가
            self.daily_stats['trade_count'] += 1
            
            if trade_type == 'BUY':
                self.daily_stats['buy_count'] += 1
            elif trade_type == 'SELL':
                self.daily_stats['sell_count'] += 1
                
                # 수익/손실 누적
                if profit > 0:
                    self.daily_stats['total_profit'] += profit
                else:
                    self.daily_stats['total_loss'] += abs(profit)
                    self.daily_stats['total_profit'] += profit  # 전체 수익에는 음수로 반영
            
        except Exception as e:
            log_error(f"일일 통계 업데이트 실패: {str(e)}")
    
    def reset_daily_stats(self):
        """일일 통계 초기화"""
        try:
            self.daily_stats = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_profit': 0.0,
                'total_loss': 0.0,
                'trade_count': 0,
                'buy_count': 0,
                'sell_count': 0
            }
            
            log_info("일일 통계 초기화 완료")
            
        except Exception as e:
            log_error(f"일일 통계 초기화 실패: {str(e)}")
    
    def get_daily_summary(self) -> dict:
        """일일 요약 정보"""
        try:
            summary = self.daily_stats.copy()
            
            # 추가 계산
            if summary['sell_count'] > 0:
                summary['avg_profit'] = summary['total_profit'] / summary['sell_count']
                summary['win_rate'] = len([t for t in self.trade_history 
                                         if t.get('date') == summary['date'] and t.get('profit', 0) > 0]) / summary['sell_count'] * 100
            else:
                summary['avg_profit'] = 0.0
                summary['win_rate'] = 0.0
            
            # 손실 한도 대비 비율
            summary['loss_ratio'] = abs(summary['total_profit'] / self.daily_loss_limit) * 100 if self.daily_loss_limit != 0 else 0
            
            return summary
            
        except Exception as e:
            log_error(f"일일 요약 조회 실패: {str(e)}")
            return {}
    
    def update_settings(self, **kwargs):
        """설정 업데이트"""
        try:
            if 'daily_loss_limit' in kwargs:
                self.daily_loss_limit = kwargs['daily_loss_limit']
            
            if 'max_tracking_stocks' in kwargs:
                self.max_tracking_stocks = kwargs['max_tracking_stocks']
            
            if 'max_position_stocks' in kwargs:
                self.max_position_stocks = kwargs['max_position_stocks']
            
            if 'max_single_position' in kwargs:
                self.max_single_position = kwargs['max_single_position']
            
            if 'position_ratios' in kwargs:
                self.position_ratios.update(kwargs['position_ratios'])
            
            if 'rise_rate_ratios' in kwargs:
                self.rise_rate_ratios.update(kwargs['rise_rate_ratios'])
            
            log_info("리스크 관리자 설정 업데이트 완료")
            
        except Exception as e:
            log_error(f"설정 업데이트 실패: {str(e)}")
    
    def get_risk_statistics(self) -> dict:
        """리스크 통계 조회"""
        try:
            # 최근 거래 분석
            recent_trades = self.trade_history[-20:] if len(self.trade_history) >= 20 else self.trade_history
            
            if not recent_trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'avg_profit': 0.0,
                    'max_loss': 0.0,
                    'risk_level': 'LOW'
                }
            
            # 통계 계산
            sell_trades = [t for t in recent_trades if t.get('type') == 'SELL']
            
            if sell_trades:
                profits = [t.get('profit', 0) for t in sell_trades]
                win_count = len([p for p in profits if p > 0])
                
                stats = {
                    'total_trades': len(sell_trades),
                    'win_rate': (win_count / len(sell_trades)) * 100,
                    'avg_profit': sum(profits) / len(profits),
                    'max_loss': min(profits) if profits else 0,
                    'max_profit': max(profits) if profits else 0,
                    'total_profit': sum(profits)
                }
                
                # 리스크 레벨 판단
                if stats['win_rate'] < 40 or stats['avg_profit'] < -1:
                    stats['risk_level'] = 'HIGH'
                elif stats['win_rate'] < 60 or stats['avg_profit'] < 1:
                    stats['risk_level'] = 'MEDIUM'
                else:
                    stats['risk_level'] = 'LOW'
            else:
                stats = {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'avg_profit': 0.0,
                    'max_loss': 0.0,
                    'risk_level': 'LOW'
                }
            
            return stats
            
        except Exception as e:
            log_error(f"리스크 통계 조회 실패: {str(e)}")
            return {}
    
    def save_risk_data(self, filepath: str) -> bool:
        """리스크 데이터 저장"""
        try:
            data = {
                'settings': {
                    'daily_loss_limit': self.daily_loss_limit,
                    'max_tracking_stocks': self.max_tracking_stocks,
                    'max_position_stocks': self.max_position_stocks,
                    'max_single_position': self.max_single_position,
                    'position_ratios': self.position_ratios,
                    'rise_rate_ratios': self.rise_rate_ratios
                },
                'daily_stats': self.daily_stats,
                'trade_history': self.trade_history[-100:],  # 최근 100건만 저장
                'save_time': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            log_info(f"리스크 데이터 저장 완료: {filepath}")
            return True
            
        except Exception as e:
            log_error(f"리스크 데이터 저장 실패: {str(e)}")
            return False
    
    def load_risk_data(self, filepath: str) -> bool:
        """리스크 데이터 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 설정 복원
            settings = data.get('settings', {})
            self.daily_loss_limit = settings.get('daily_loss_limit', self.daily_loss_limit)
            self.max_tracking_stocks = settings.get('max_tracking_stocks', self.max_tracking_stocks)
            self.max_position_stocks = settings.get('max_position_stocks', self.max_position_stocks)
            self.max_single_position = settings.get('max_single_position', self.max_single_position)
            self.position_ratios = settings.get('position_ratios', self.position_ratios)
            self.rise_rate_ratios = settings.get('rise_rate_ratios', self.rise_rate_ratios)
            
            # 일일 통계 복원 (같은 날짜인 경우만)
            daily_stats = data.get('daily_stats', {})
            if daily_stats.get('date') == datetime.now().strftime('%Y-%m-%d'):
                self.daily_stats = daily_stats
            
            # 거래 기록 복원
            self.trade_history = data.get('trade_history', [])
            
            log_info(f"리스크 데이터 로드 완료: {len(self.trade_history)}건 거래 기록")
            return True
            
        except FileNotFoundError:
            log_info("리스크 데이터 파일이 없습니다")
            return True
        except Exception as e:
            log_error(f"리스크 데이터 로드 실패: {str(e)}")
            return False
    
    def cleanup_old_trades(self, days: int = 30) -> int:
        """오래된 거래 기록 정리"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            original_count = len(self.trade_history)
            self.trade_history = [
                trade for trade in self.trade_history 
                if trade.get('date', '') >= cutoff_date
            ]
            
            removed_count = original_count - len(self.trade_history)
            
            if removed_count > 0:
                log_info(f"오래된 거래 기록 {removed_count}건 정리 완료")
            
            return removed_count
            
        except Exception as e:
            log_error(f"거래 기록 정리 실패: {str(e)}")
            return 0
    
    def get_position_recommendation(self, rise_days: int, rise_rate: float, 
                                  current_positions: int) -> dict:
        """포지션 추천 정보"""
        try:
            # 포지션 크기 계산
            base_amount = 200000  # 기본 금액
            position_info = self.calculate_position_size(base_amount, rise_days, rise_rate, current_positions)
            
            # 추천 메시지 생성
            recommendations = []
            
            if not position_info['allowed']:
                recommendations.append(f"❌ 진입 불가: {position_info['reason']}")
            else:
                risk_level = position_info['risk_level']
                if risk_level == 'HIGH':
                    recommendations.append("⚠️ 고위험: 신중한 진입 필요")
                elif risk_level == 'MEDIUM':
                    recommendations.append("⚡ 중위험: 적정 수준의 리스크")
                else:
                    recommendations.append("✅ 저위험: 안전한 진입 가능")
                
                # 포지션 크기 추천
                final_ratio = position_info['final_ratio']
                if final_ratio <= 0.3:
                    recommendations.append("📉 포지션 크기: 매우 작게")
                elif final_ratio <= 0.6:
                    recommendations.append("📊 포지션 크기: 작게")
                elif final_ratio <= 0.8:
                    recommendations.append("📈 포지션 크기: 보통")
                else:
                    recommendations.append("📊 포지션 크기: 정상")
            
            return {
                'position_info': position_info,
                'recommendations': recommendations,
                'risk_score': self.calculate_risk_score(rise_days, rise_rate, current_positions)
            }
            
        except Exception as e:
            log_error(f"포지션 추천 생성 실패: {str(e)}")
            return {}
    
    def calculate_risk_score(self, rise_days: int, rise_rate: float, 
                           current_positions: int) -> int:
        """리스크 점수 계산 (0-100, 높을수록 위험)"""
        try:
            score = 0
            
            # 연속상승일수 (0-40점)
            score += min(rise_days * 8, 40)
            
            # 상승률 (0-30점)
            if rise_rate >= 100:
                score += 30
            elif rise_rate >= 70:
                score += 20
            elif rise_rate >= 50:
                score += 10
            
            # 포지션 수 (0-20점)
            score += min(current_positions * 2, 20)
            
            # 일일 손실 (0-10점)
            if self.daily_stats['total_profit'] < 0:
                loss_ratio = abs(self.daily_stats['total_profit'] / self.daily_loss_limit)
                score += min(loss_ratio * 10, 10)
            
            return min(score, 100)
            
        except Exception as e:
            log_error(f"리스크 점수 계산 실패: {str(e)}")
            return 100  # 오류 시 최대 위험으로 설정