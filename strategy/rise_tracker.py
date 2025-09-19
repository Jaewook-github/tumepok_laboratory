# -*- coding: utf-8 -*-
"""
연속상승 추적기 (Rise Tracker)
급등주의 연속상승 패턴을 추적하고 투매폭 진입 시점을 판단합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
import json

from config.constants import TUMEPOK_MATRIX
from utils.enhanced_logging import log_info, log_error, log_debug, log_warning


class TrackingInfo:
    """추적 정보 데이터 클래스"""
    
    def __init__(self, stock_code: str, start_price: float, start_date: str = None):
        self.stock_code = stock_code
        self.stock_name = ""  # 종목명
        self.start_date = start_date or datetime.now().strftime('%Y-%m-%d')
        self.start_price = start_price
        # 첫날에는 고점을 시작가로 초기화하되, 실시간 데이터로 적극 업데이트
        self.high_price = start_price
        self.current_price = start_price
        self.rise_days = 1
        self.rise_rate = 0.0  # 누적 상승률
        self.daily_change_rate = 0.0  # 당일 등락률
        self.drop_rate = 0.0
        self.target_drop_min = 0.0
        self.target_drop_max = 0.0
        self.target_drop_1st = 0.0  # 1차선
        self.target_drop_2nd = 0.0  # 2차선
        self.target_drop_3rd = 0.0  # 3차선
        self.status = "TRACKING"  # TRACKING, WAITING, READY, COMPLETED
        self.waiting_days = 0
        self.bought_stages = set()
        self.last_update = datetime.now()
        
        # 일별 가격 기록
        self.daily_prices = []
        self.add_daily_price(start_price, self.start_date)
        
        # 투매폭 계산
        self.update_tumepok_calculation()
    
    def add_daily_price(self, price: float, date: str = None):
        """일별 가격 추가"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        self.daily_prices.append({
            'date': date,
            'price': price,
            'is_high': False
        })
    
    def update_price(self, current_price: float, daily_change_rate: float = None, high_price: float = None) -> str:
        """가격 업데이트 및 상태 변경"""
        self.current_price = current_price
        if daily_change_rate is not None:
            self.daily_change_rate = daily_change_rate
        self.last_update = datetime.now()
        
        # 연속상승일 계산 (등록 날짜 기준)
        start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        today_date = datetime.now()
        self.rise_days = (today_date.date() - start_date.date()).days + 1
        
        # 고점 업데이트 로직 개선
        high_updated = False
        is_first_day = self.rise_days == 1

        # 고점 갱신 조건: 새로운 가격이 기존 고점보다 높을 때만
        # 1. 키움 API 실시간 고가 데이터 우선 사용
        if high_price is not None and high_price > 0:
            # 키움 API의 당일 고가가 기존 고점보다 높으면 업데이트
            if high_price > self.high_price:
                old_high = self.high_price
                self.high_price = high_price
                high_updated = True
                log_debug(f"{self.stock_code} 키움 고가 데이터로 고점 갱신: {old_high:,}원 → {high_price:,}원 ({'첫날' if is_first_day else '신고점'})")

            # 키움 고가와 현재가가 같고, 기존 고점보다 높으면 고점 갱신
            elif high_price == current_price and current_price > self.high_price:
                old_high = self.high_price
                self.high_price = current_price
                high_updated = True
                log_debug(f"{self.stock_code} 현재가=키움고가로 고점 갱신: {old_high:,}원 → {current_price:,}원")

            # 기존 고점보다 낮거나 같으면 고점 유지
            else:
                log_debug(f"{self.stock_code} 고점 유지: 키움고가 {high_price:,}원 <= 기존고점 {self.high_price:,}원")
        else:
            # 2. 키움 고가 데이터가 없으면 현재가로 고점 갱신 여부 확인
            if current_price > self.high_price:
                old_high = self.high_price
                self.high_price = current_price
                high_updated = True
                log_debug(f"{self.stock_code} 현재가로 고점 갱신: {old_high:,}원 → {current_price:,}원 ({'첫날' if is_first_day else '신고점'})")
            else:
                log_debug(f"{self.stock_code} 고점 유지: 현재가 {current_price:,}원 <= 기존고점 {self.high_price:,}원")
        
        # 당일 가격 기록 업데이트 (고점 갱신 여부와 관계없이)
        today = datetime.now().strftime('%Y-%m-%d')
        if not self.daily_prices or self.daily_prices[-1]['date'] != today:
            # 새로운 날의 첫 가격 기록
            self.add_daily_price(current_price, today)
            if high_updated:
                self.daily_prices[-1]['is_high'] = True
        else:
            # 같은 날의 가격 업데이트
            self.daily_prices[-1]['price'] = current_price
            if high_updated:
                self.daily_prices[-1]['is_high'] = True
        
        # 고점 갱신된 경우 추가 처리
        if high_updated:
            # 투매폭 재계산
            self.update_tumepok_calculation()
            
            log_debug(f"{self.stock_code} 고점 갱신: {current_price:,}원 ({self.rise_days}일차)")
            return "HIGH_UPDATED"
        
        # 하락률 계산: 시작가 기준으로 고점에서 현재가까지의 하락폭
        # 투매폭 전략의 핵심: 시작가 대비 상승률에서 현재 등락률을 뺀 값
        # 예: 30% 상승했다가 20%만 남았으면 10% 하락
        if self.start_price > 0:
            # 방법 1: 상승률 - 현재 등락률 (시작가 기준)
            current_rise_from_start = ((current_price - self.start_price) / self.start_price) * 100
            self.drop_rate = self.rise_rate - current_rise_from_start

            # 음수가 되면 0으로 처리 (상승 중인 경우)
            if self.drop_rate < 0:
                self.drop_rate = 0.0
        else:
            self.drop_rate = 0.0
        
        # 상태별 처리
        if self.status == "TRACKING":
            return self.check_tumepok_entry()
        elif self.status == "WAITING":
            return self.check_waiting_period()
        elif self.status == "READY":
            return "READY"
        
        return "CONTINUE"
    
    def update_tumepok_calculation(self):
        """투매폭 계산 업데이트 - 누적 상승률 기준"""
        # 누적 상승률 계산 (급등 시작점 대비)
        self.rise_rate = ((self.high_price - self.start_price) / self.start_price) * 100
        
        # 투매폭 매트릭스에서 적정 하락폭 찾기 (누적 상승률 기준)
        for matrix_row in TUMEPOK_MATRIX:
            if matrix_row['rise_min'] <= self.rise_rate <= matrix_row['rise_max']:
                self.target_drop_min = matrix_row['drop_min']
                self.target_drop_max = matrix_row['drop_max']
                
                # 1차선, 2차선, 3차선 계산
                self.target_drop_1st = self.target_drop_min  # 1차선 (약매수)
                self.target_drop_2nd = (self.target_drop_min + self.target_drop_max) / 2  # 2차선 (보통매수)
                self.target_drop_3rd = self.target_drop_max  # 3차선 (강매수)
                break
        else:
            # 범위를 벗어나는 경우 마지막 구간 사용
            last_row = TUMEPOK_MATRIX[-1]
            self.target_drop_min = last_row['drop_min']
            self.target_drop_max = last_row['drop_max']
            self.target_drop_1st = self.target_drop_min
            self.target_drop_2nd = (self.target_drop_min + self.target_drop_max) / 2
            self.target_drop_3rd = self.target_drop_max
        
        log_debug(f"{self.stock_code} 투매폭 계산: 누적상승률 {self.rise_rate:.1f}% -> 1차선 {self.target_drop_1st:.1f}%, 2차선 {self.target_drop_2nd:.1f}%, 3차선 {self.target_drop_3rd:.1f}%")
    
    def check_tumepok_entry(self) -> str:
        """투매폭 진입 조건 확인"""
        # 최대 연속상승일 초과 시 추적 종료
        if self.rise_days > 7:
            self.status = "COMPLETED"
            log_info(f"{self.stock_code} 최대 연속상승일 초과로 추적 종료")
            return "MAX_DAYS_EXCEEDED"
        
        # 적정 하락폭 도달 확인
        if self.drop_rate >= self.target_drop_min:
            self.status = "READY"
            log_info(f"{self.stock_code} 투매폭 진입 준비: 하락률 {self.drop_rate:.1f}% >= {self.target_drop_min}%")
            return "TUMEPOK_READY"
        
        # 3일 대기 시작 조건 확인 (고점 갱신 없이 하루 지남)
        if self.should_start_waiting():
            self.status = "WAITING"
            self.waiting_days = 1
            log_info(f"{self.stock_code} 반등 대기 시작")
            return "WAITING_STARTED"
        
        return "CONTINUE"
    
    def check_waiting_period(self) -> str:
        """대기 기간 확인"""
        # 대기 중 고점 갱신되면 추적으로 복귀
        if self.current_price > self.high_price:
            self.status = "TRACKING"
            self.waiting_days = 0
            log_info(f"{self.stock_code} 대기 중 고점 갱신으로 추적 재개")
            return "TRACKING_RESUMED"
        
        # 적정 하락폭 도달 시 진입 준비
        if self.drop_rate >= self.target_drop_min:
            self.status = "READY"
            log_info(f"{self.stock_code} 대기 중 투매폭 진입 준비")
            return "TUMEPOK_READY"
        
        # 3일 대기 완료 시 진입 준비
        if self.waiting_days >= 3:
            self.status = "READY"
            log_info(f"{self.stock_code} 3일 대기 완료로 투매폭 진입 준비")
            return "WAITING_COMPLETED"
        
        return "WAITING"
    
    def should_start_waiting(self) -> bool:
        """대기 시작 조건 확인"""
        # 마지막 고점 갱신 후 하루가 지났는지 확인
        if len(self.daily_prices) < 2:
            return False
        
        # 오늘 고점 갱신이 없었는지 확인
        today = datetime.now().strftime('%Y-%m-%d')
        for price_info in reversed(self.daily_prices):
            if price_info['date'] == today:
                return not price_info['is_high']
        
        return True
    
    def get_buy_stage(self, current_price: float) -> str:
        """매수 단계 판단"""
        if self.status != "READY":
            return "WAIT"
        
        # 하락률 계산: 상승률 - 현재 등락률 (일관된 계산 방식)
        current_change_rate = ((current_price - self.start_price) / self.start_price) * 100
        drop_rate = self.rise_rate - current_change_rate
        
        # 3차 매수 (강매수) - 최대 하락폭
        if drop_rate >= self.target_drop_max and "3차" not in self.bought_stages:
            return "3차"
        
        # 2차 매수 (보통매수) - 중간 하락폭
        mid_drop = (self.target_drop_min + self.target_drop_max) / 2
        if drop_rate >= mid_drop and "2차" not in self.bought_stages:
            return "2차"
        
        # 1차 매수 (약매수) - 최소 하락폭
        if drop_rate >= self.target_drop_min and "1차" not in self.bought_stages:
            return "1차"
        
        return "WAIT"
    
    def add_bought_stage(self, stage: str):
        """매수 단계 추가"""
        self.bought_stages.add(stage)
        log_debug(f"{self.stock_code} {stage} 매수 완료")
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'start_date': self.start_date,
            'start_price': self.start_price,
            'high_price': self.high_price,
            'current_price': self.current_price,
            'rise_days': self.rise_days,
            'rise_rate': self.rise_rate,
            'daily_change_rate': self.daily_change_rate,
            'drop_rate': self.drop_rate,
            'target_drop_min': self.target_drop_min,
            'target_drop_max': self.target_drop_max,
            'target_drop_1st': self.target_drop_1st,
            'target_drop_2nd': self.target_drop_2nd,
            'target_drop_3rd': self.target_drop_3rd,
            'status': self.status,
            'waiting_days': self.waiting_days,
            'bought_stages': list(self.bought_stages),
            'last_update': self.last_update.isoformat(),
            'daily_prices': self.daily_prices
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """딕셔너리에서 생성"""
        tracking_info = cls(
            stock_code=data['stock_code'],
            start_price=data['start_price'],
            start_date=data['start_date']
        )
        
        tracking_info.stock_name = data.get('stock_name', '')
        tracking_info.high_price = data['high_price']
        tracking_info.current_price = data['current_price']
        tracking_info.rise_days = data['rise_days']
        tracking_info.rise_rate = data['rise_rate']
        tracking_info.daily_change_rate = data.get('daily_change_rate', 0.0)
        tracking_info.drop_rate = data['drop_rate']
        tracking_info.target_drop_min = data['target_drop_min']
        tracking_info.target_drop_max = data['target_drop_max']
        tracking_info.target_drop_1st = data.get('target_drop_1st', data['target_drop_min'])
        tracking_info.target_drop_2nd = data.get('target_drop_2nd', (data['target_drop_min'] + data['target_drop_max']) / 2)
        tracking_info.target_drop_3rd = data.get('target_drop_3rd', data['target_drop_max'])
        tracking_info.status = data['status']
        tracking_info.waiting_days = data['waiting_days']
        tracking_info.bought_stages = set(data['bought_stages'])
        tracking_info.last_update = datetime.fromisoformat(data['last_update'])
        tracking_info.daily_prices = data.get('daily_prices', [])
        
        return tracking_info


class RiseTracker:
    """연속상승 추적기"""
    
    def __init__(self):
        self.tracking_stocks: Dict[str, TrackingInfo] = {}
        
        # 설정 파일에서 max_tracking_stocks 값 읽기
        try:
            from config.tumepok_config import TumepokConfig
            config = TumepokConfig()
            self.max_tracking_stocks = config.get('max_tracking_stocks', 20)
            log_info(f"연속상승 추적기 초기화 완료 - 최대 추적 종목: {self.max_tracking_stocks}개")
        except Exception as e:
            self.max_tracking_stocks = 20
            log_info(f"연속상승 추적기 초기화 완료 - 기본값 사용: {self.max_tracking_stocks}개")
    
    def add_stock(self, stock_code: str, start_price: float, start_date: str = None, stock_name: str = "", daily_change_rate: float = 0.0) -> bool:
        """추적 종목 추가"""
        try:
            # 최대 추적 종목 수 확인
            if len(self.tracking_stocks) >= self.max_tracking_stocks:
                log_warning(f"최대 추적 종목 수 초과: {len(self.tracking_stocks)}/{self.max_tracking_stocks}")
                return False
            
            # 이미 추적 중인 종목 확인
            if stock_code in self.tracking_stocks:
                log_warning(f"이미 추적 중인 종목: {stock_code}")
                return False
            
            # 추적 정보 생성
            tracking_info = TrackingInfo(stock_code, start_price, start_date)
            tracking_info.stock_name = stock_name
            tracking_info.daily_change_rate = daily_change_rate
            self.tracking_stocks[stock_code] = tracking_info
            
            log_info(f"추적 종목 추가: {stock_name}({stock_code}) (시작가: {start_price:,}원, 등락률: {daily_change_rate:.1f}%)")
            return True
            
        except Exception as e:
            log_error(f"추적 종목 추가 실패 {stock_code}: {str(e)}")
            return False
    
    def remove_stock(self, stock_code: str) -> bool:
        """추적 종목 제거"""
        try:
            if stock_code in self.tracking_stocks:
                del self.tracking_stocks[stock_code]
                log_info(f"추적 종목 제거: {stock_code}")
                return True
            else:
                log_warning(f"추적 중이지 않은 종목: {stock_code}")
                return False
                
        except Exception as e:
            log_error(f"추적 종목 제거 실패 {stock_code}: {str(e)}")
            return False
    
    def update_price(self, stock_code: str, current_price: float, daily_change_rate: float = None, high_price: float = None) -> str:
        """실시간 가격 업데이트"""
        try:
            if stock_code not in self.tracking_stocks:
                return "NOT_TRACKING"
            
            tracking_info = self.tracking_stocks[stock_code]
            result = tracking_info.update_price(current_price, daily_change_rate, high_price)
            
            # 추적 완료된 종목 자동 제거
            if tracking_info.status == "COMPLETED":
                self.remove_stock(stock_code)
            
            return result
            
        except Exception as e:
            log_error(f"가격 업데이트 실패 {stock_code}: {str(e)}")
            return "ERROR"
    
    def get_tracking_info(self, stock_code: str) -> Optional[TrackingInfo]:
        """추적 정보 조회"""
        return self.tracking_stocks.get(stock_code)
    
    def get_all_tracking_info(self) -> Dict[str, TrackingInfo]:
        """모든 추적 정보 조회"""
        return self.tracking_stocks.copy()
    
    def get_ready_stocks(self) -> List[str]:
        """투매폭 진입 준비된 종목 목록"""
        ready_stocks = []
        for stock_code, tracking_info in self.tracking_stocks.items():
            if tracking_info.status == "READY":
                ready_stocks.append(stock_code)
        return ready_stocks
    
    def get_buy_stage(self, stock_code: str, current_price: float) -> str:
        """매수 단계 판단"""
        if stock_code not in self.tracking_stocks:
            return "NOT_TRACKING"
        
        return self.tracking_stocks[stock_code].get_buy_stage(current_price)
    
    def add_bought_stage(self, stock_code: str, stage: str) -> bool:
        """매수 단계 추가"""
        try:
            if stock_code in self.tracking_stocks:
                self.tracking_stocks[stock_code].add_bought_stage(stage)
                return True
            return False
        except Exception as e:
            log_error(f"매수 단계 추가 실패: {stock_code}, {e}")
            return False
    
    def update_bought_stages(self, stock_code: str, stage: str) -> bool:
        """매수 단계 업데이트 및 JSON 저장"""
        try:
            if stock_code in self.tracking_stocks:
                # 메모리 업데이트
                self.tracking_stocks[stock_code].add_bought_stage(stage)
                # JSON 파일에 즉시 저장
                self.save_data()
                log_debug(f"매수 단계 영구 저장 완료: {stock_code} - {stage}")
                return True
            return False
        except Exception as e:
            log_error(f"매수 단계 저장 실패: {stock_code}, {e}")
            return False
    
    def get_tracking_dataframe(self) -> pd.DataFrame:
        """추적 정보를 DataFrame으로 변환"""
        try:
            if not self.tracking_stocks:
                return pd.DataFrame(columns=[
                    '종목코드', '종목명', '시작가', '고점', '현재가', '등락률', 
                    '상승률', '하락률', '연속상승일', '1차선', '2차선', '3차선', '매수단계', '상태', '매도'
                ])
            
            data = []
            for stock_code, tracking_info in self.tracking_stocks.items():
                # 매도여부 확인 (DataManager에서 확인)
                is_sold = False
                try:
                    # 전역적으로 접근할 수 있는 방법이 없으므로, 일단 False로 설정
                    # TumepokEngine에서 필터링하여 매도된 종목은 제외됨
                    is_sold = False
                except:
                    is_sold = False
                
                data.append({
                    '종목코드': stock_code,
                    '종목명': tracking_info.stock_name if hasattr(tracking_info, 'stock_name') else '',
                    '등록날짜': tracking_info.start_date,
                    '시작가': int(tracking_info.start_price),
                    '고점': int(tracking_info.high_price),
                    '현재가': int(tracking_info.current_price),
                    '등락률': tracking_info.daily_change_rate,  # TumepokTrackingModel에서 포맷팅
                    '상승률': tracking_info.rise_rate,
                    '하락률': tracking_info.drop_rate,
                    '연속상승일': tracking_info.rise_days,
                    '1차선': tracking_info.target_drop_1st,
                    '2차선': tracking_info.target_drop_2nd,
                    '3차선': tracking_info.target_drop_3rd,
                    '매수단계': ','.join(tracking_info.bought_stages) if tracking_info.bought_stages else '-',
                    '상태': tracking_info.status,
                    '매도': '매도' if is_sold else '-'
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            log_error(f"추적 DataFrame 생성 실패: {str(e)}")
            return pd.DataFrame()
    
    def get_statistics(self) -> dict:
        """추적 통계 조회"""
        try:
            total_count = len(self.tracking_stocks)
            status_counts = {}
            
            for tracking_info in self.tracking_stocks.values():
                status = tracking_info.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                'total_tracking': total_count,
                'max_tracking': self.max_tracking_stocks,
                'status_counts': status_counts,
                'ready_count': status_counts.get('READY', 0),
                'tracking_count': status_counts.get('TRACKING', 0),
                'waiting_count': status_counts.get('WAITING', 0)
            }
            
        except Exception as e:
            log_error(f"추적 통계 조회 실패: {str(e)}")
            return {}
    
    def save_tracking_data(self, filepath: str) -> bool:
        """추적 데이터 저장"""
        try:
            data = {}
            for stock_code, tracking_info in self.tracking_stocks.items():
                data[stock_code] = tracking_info.to_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            log_info(f"추적 데이터 저장 완료: {filepath}")
            return True
            
        except Exception as e:
            log_error(f"추적 데이터 저장 실패: {str(e)}")
            return False
    
    def load_tracking_data(self, filepath: str) -> bool:
        """추적 데이터 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.tracking_stocks.clear()
            
            for stock_code, tracking_data in data.items():
                tracking_info = TrackingInfo.from_dict(tracking_data)
                self.tracking_stocks[stock_code] = tracking_info
            
            log_info(f"추적 데이터 로드 완료: {len(self.tracking_stocks)}개 종목")
            return True
            
        except FileNotFoundError:
            log_info("추적 데이터 파일이 없습니다")
            return True
        except Exception as e:
            log_error(f"추적 데이터 로드 실패: {str(e)}")
            return False
    
    def cleanup_old_tracking(self, days: int = 7) -> int:
        """오래된 추적 데이터 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            removed_count = 0
            
            stocks_to_remove = []
            for stock_code, tracking_info in self.tracking_stocks.items():
                if tracking_info.last_update < cutoff_date:
                    stocks_to_remove.append(stock_code)
            
            for stock_code in stocks_to_remove:
                self.remove_stock(stock_code)
                removed_count += 1
            
            if removed_count > 0:
                log_info(f"오래된 추적 데이터 {removed_count}개 정리 완료")
            
            return removed_count
            
        except Exception as e:
            log_error(f"추적 데이터 정리 실패: {str(e)}")
            return 0
    
    def update_config(self, new_config):
        """연속상승 추적 설정 업데이트"""
        try:
            # 설정 관련 속성들 업데이트
            if hasattr(self, 'config'):
                self.config = new_config
            
            # 추적 관련 설정 즉시 반영
            old_max_tracking = self.max_tracking_stocks
            self.max_tracking_stocks = new_config.get('max_tracking_stocks', 20)
            rise_threshold = new_config.get('rise_threshold', 30.0)
            max_rise_days = new_config.get('max_rise_days', 7)
            
            # 기타 설정 속성 업데이트
            self.rise_threshold = rise_threshold
            self.max_rise_days = max_rise_days
            
            log_info(f"RiseTracker 설정 업데이트: 최대추적={old_max_tracking}->{self.max_tracking_stocks}개, "
                    f"급등기준={rise_threshold}%, 최대연속상승일={max_rise_days}일")
            
        except Exception as e:
            log_error(f"RiseTracker 설정 업데이트 실패: {str(e)}")