# -*- coding: utf-8 -*-
"""
지지 조건 분석기 (Support Analyzer)
RSI, 지지선, 거래량 3가지 지지 조건을 분석합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

from utils.enhanced_logging import log_info, log_error, log_debug, log_warning


class SupportAnalyzer:
    """지지 조건 분석기"""
    
    def __init__(self, main_window=None):
        self.main_window = main_window
        
        # 기본 설정값
        self.rsi_threshold = 30.0
        self.volume_ratio_threshold = 0.25
        self.support_tolerance = 0.01
        
        # 캐시
        self.rsi_cache = {}
        self.support_cache = {}
        self.volume_cache = {}
        
        log_info("지지 조건 분석기 초기화 완료")

    def update_config(self, new_config: dict):
        """설정 업데이트"""
        try:
            if 'rsi_threshold' in new_config:
                self.rsi_threshold = float(new_config['rsi_threshold'])
                log_info(f"RSI 임계값 업데이트: {self.rsi_threshold}")

            if 'volume_ratio_threshold' in new_config:
                self.volume_ratio_threshold = float(new_config['volume_ratio_threshold'])
                log_info(f"거래량 비율 임계값 업데이트: {self.volume_ratio_threshold}")

            if 'support_tolerance' in new_config:
                self.support_tolerance = float(new_config['support_tolerance'])
                log_info(f"지지선 허용 오차 업데이트: {self.support_tolerance}")

            # 캐시 초기화
            self.rsi_cache.clear()
            self.support_cache.clear()
            self.volume_cache.clear()

            log_info(f"SupportAnalyzer 설정 업데이트 완료")

        except Exception as e:
            log_error(f"SupportAnalyzer 설정 업데이트 실패: {str(e)}")
    
    def check_all_conditions(self, stock_code: str, tracking_info: dict, condition_confirmed: bool = False) -> dict:
        """3가지 지지 조건 종합 확인"""
        try:
            results = {
                'rsi_oversold': False,
                'support_level': False,
                'volume_dried': False,
                'satisfied_count': 0,
                'details': {}
            }
            
            # 1. RSI 과매도 확인
            rsi_result = self.check_rsi_oversold(stock_code)
            results['rsi_oversold'] = rsi_result['is_oversold']
            results['details']['rsi'] = rsi_result
            
            # 2. 지지선 확인
            support_result = self.check_support_level(stock_code, tracking_info.get('current_price', 0))
            results['support_level'] = support_result['has_support']
            results['details']['support'] = support_result
            
            # 3. 거래량 급감 확인
            volume_result = self.check_volume_dried(stock_code, tracking_info)
            results['volume_dried'] = volume_result['is_dried']
            results['details']['volume'] = volume_result
            
            # 만족된 조건 수 계산
            satisfied_conditions = [
                results['rsi_oversold'],
                results['support_level'],
                results['volume_dried']
            ]
            results['satisfied_count'] = sum(satisfied_conditions)
            
            # 조건식 확인 시 지지 조건 완화 적용
            if condition_confirmed:
                # 조건식 신호가 있으면 지지 조건을 더 관대하게 적용
                results['condition_confirmed'] = True
                results['original_satisfied_count'] = results['satisfied_count']
                
                # 조건식 확인 보너스: 만족 조건 수에 0.5 추가 (반올림으로 1개 조건 완화 효과)
                results['satisfied_count'] = min(3, results['satisfied_count'] + 0.5)
                
                log_debug(f"{stock_code} 조건식 확인 지지조건 완화: "
                         f"{results['original_satisfied_count']} → {results['satisfied_count']}/3개")
            else:
                results['condition_confirmed'] = False
                log_debug(f"{stock_code} 지지조건 확인: {results['satisfied_count']}/3개 만족")
            
            return results
            
        except Exception as e:
            log_error(f"지지 조건 확인 실패 {stock_code}: {str(e)}")
            return {
                'rsi_oversold': False,
                'support_level': False,
                'volume_dried': False,
                'satisfied_count': 0,
                'details': {'error': str(e)}
            }
    
    def check_rsi_oversold(self, stock_code: str) -> dict:
        """RSI 과매도 확인"""
        try:
            # 캐시 확인
            cache_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            if cache_key in self.rsi_cache:
                return self.rsi_cache[cache_key]
            
            # 분봉 데이터 요청 (실제로는 TR 요청)
            minute_data = self.get_minute_data(stock_code, period=30)
            
            if minute_data is None or len(minute_data) < 14:
                result = {
                    'is_oversold': False,
                    'rsi_value': None,
                    'threshold': self.rsi_threshold,
                    'error': '데이터 부족'
                }
            else:
                # RSI 계산
                rsi_value = self.calculate_rsi(minute_data['close'], period=14)
                
                result = {
                    'is_oversold': rsi_value <= self.rsi_threshold,
                    'rsi_value': rsi_value,
                    'threshold': self.rsi_threshold,
                    'error': None
                }
            
            # 캐시 저장 (1분간 유효)
            self.rsi_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            log_error(f"RSI 과매도 확인 실패 {stock_code}: {str(e)}")
            return {
                'is_oversold': False,
                'rsi_value': None,
                'threshold': self.rsi_threshold,
                'error': str(e)
            }
    
    def check_support_level(self, stock_code: str, current_price: float) -> dict:
        """분봉 지지선 확인"""
        try:
            # 캐시 확인
            cache_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            if cache_key in self.support_cache:
                cached_result = self.support_cache[cache_key]
                # 현재가 기준으로 지지선 재확인
                cached_result['has_support'] = self.is_near_support_level(
                    current_price, cached_result.get('support_levels', [])
                )
                return cached_result
            
            # 5분봉과 15분봉 데이터 요청
            minute5_data = self.get_minute_data(stock_code, period=100, interval=5)
            minute15_data = self.get_minute_data(stock_code, period=50, interval=15)
            
            support_levels = []
            
            # 5분봉 지지선 찾기
            if minute5_data is not None and len(minute5_data) > 20:
                support5 = self.find_support_levels(minute5_data, lookback=20)
                support_levels.extend(support5)
            
            # 15분봉 지지선 찾기
            if minute15_data is not None and len(minute15_data) > 20:
                support15 = self.find_support_levels(minute15_data, lookback=20)
                support_levels.extend(support15)
            
            # 중복 제거 및 정렬
            support_levels = sorted(list(set(support_levels)))
            
            # 현재가 근처 지지선 확인
            has_support = self.is_near_support_level(current_price, support_levels)
            
            result = {
                'has_support': has_support,
                'support_levels': support_levels,
                'current_price': current_price,
                'tolerance': self.support_tolerance,
                'error': None
            }
            
            # 캐시 저장 (5분간 유효)
            self.support_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            log_error(f"지지선 확인 실패 {stock_code}: {str(e)}")
            return {
                'has_support': False,
                'support_levels': [],
                'current_price': current_price,
                'tolerance': self.support_tolerance,
                'error': str(e)
            }
    
    def check_volume_dried(self, stock_code: str, tracking_info: dict) -> dict:
        """거래량 급감 확인"""
        try:
            # 캐시 확인
            cache_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            if cache_key in self.volume_cache:
                return self.volume_cache[cache_key]
            
            # 현재 거래량 조회
            current_volume = self.get_current_volume(stock_code)
            
            if current_volume is None:
                result = {
                    'is_dried': False,
                    'current_volume': None,
                    'max_volume': None,
                    'ratio': None,
                    'threshold': self.volume_ratio_threshold,
                    'error': '거래량 데이터 없음'
                }
            else:
                # 급등 기간 최대 거래량 계산
                max_volume = self.get_max_volume_during_rise(stock_code, tracking_info)
                
                if max_volume is None or max_volume == 0:
                    volume_ratio = 0
                else:
                    volume_ratio = current_volume / max_volume
                
                result = {
                    'is_dried': volume_ratio <= self.volume_ratio_threshold,
                    'current_volume': current_volume,
                    'max_volume': max_volume,
                    'ratio': volume_ratio,
                    'threshold': self.volume_ratio_threshold,
                    'error': None
                }
            
            # 캐시 저장 (1분간 유효)
            self.volume_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            log_error(f"거래량 급감 확인 실패 {stock_code}: {str(e)}")
            return {
                'is_dried': False,
                'current_volume': None,
                'max_volume': None,
                'ratio': None,
                'threshold': self.volume_ratio_threshold,
                'error': str(e)
            }
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        try:
            if len(prices) < period + 1:
                return 50.0  # 기본값
            
            # 가격 변화 계산
            delta = prices.diff()
            
            # 상승분과 하락분 분리
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # 평균 계산
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # RS 계산
            rs = avg_gain / avg_loss
            
            # RSI 계산
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception as e:
            log_error(f"RSI 계산 실패: {str(e)}")
            return 50.0
    
    def find_support_levels(self, data: pd.DataFrame, lookback: int = 20) -> List[float]:
        """지지선 찾기"""
        try:
            if len(data) < lookback:
                return []
            
            support_levels = []
            lows = data['low'].values
            
            for i in range(lookback, len(lows) - lookback):
                # 현재 저점이 앞뒤 구간의 최저점인지 확인
                left_min = min(lows[i-lookback:i])
                right_min = min(lows[i+1:i+lookback+1])
                current_low = lows[i]
                
                if current_low <= left_min and current_low <= right_min:
                    # 지지선으로 인정되는 조건 확인
                    if self.is_valid_support_level(data, i, lookback):
                        support_levels.append(current_low)
            
            return support_levels
            
        except Exception as e:
            log_error(f"지지선 찾기 실패: {str(e)}")
            return []
    
    def is_valid_support_level(self, data: pd.DataFrame, index: int, lookback: int) -> bool:
        """유효한 지지선인지 확인"""
        try:
            # 지지선 근처에서 반등이 있었는지 확인
            support_price = data['low'].iloc[index]
            
            # 이후 데이터에서 반등 확인
            future_data = data.iloc[index+1:index+lookback+1]
            if len(future_data) == 0:
                return False
            
            # 반등률 확인 (지지선 대비 2% 이상 상승)
            max_bounce = future_data['high'].max()
            bounce_rate = (max_bounce - support_price) / support_price
            
            return bounce_rate >= 0.02
            
        except Exception as e:
            log_error(f"지지선 유효성 확인 실패: {str(e)}")
            return False
    
    def is_near_support_level(self, current_price: float, support_levels: List[float]) -> bool:
        """현재가가 지지선 근처인지 확인"""
        try:
            if not support_levels:
                return False
            
            for support_level in support_levels:
                # 지지선 대비 허용 오차 내에 있는지 확인
                price_diff = abs(current_price - support_level) / support_level
                if price_diff <= self.support_tolerance:
                    return True
            
            return False
            
        except Exception as e:
            log_error(f"지지선 근처 확인 실패: {str(e)}")
            return False
    
    def get_minute_data(self, stock_code: str, period: int = 30, interval: int = 1) -> Optional[pd.DataFrame]:
        """분봉 데이터 조회"""
        try:
            # 실제로는 TR 요청을 통해 데이터 조회
            # 여기서는 모의 데이터 생성
            if self.main_window is None:
                return self.generate_mock_minute_data(period)
            
            # TR 요청 (실제 구현에서는 키움 API 호출)
            # self.main_window.request_minute_chart(stock_code, period, interval)
            
            # 임시로 모의 데이터 반환
            return self.generate_mock_minute_data(period)
            
        except Exception as e:
            log_error(f"분봉 데이터 조회 실패 {stock_code}: {str(e)}")
            return None
    
    def generate_mock_minute_data(self, period: int) -> pd.DataFrame:
        """모의 분봉 데이터 생성 (테스트용)"""
        try:
            import random
            
            # 기준가 설정
            base_price = 10000
            
            data = []
            current_price = base_price
            
            for i in range(period):
                # 랜덤한 가격 변동
                change_rate = random.uniform(-0.02, 0.02)
                
                open_price = current_price
                high_price = open_price * (1 + abs(change_rate) + random.uniform(0, 0.01))
                low_price = open_price * (1 - abs(change_rate) - random.uniform(0, 0.01))
                close_price = open_price * (1 + change_rate)
                
                volume = random.randint(1000, 10000)
                
                data.append({
                    'datetime': datetime.now() - timedelta(minutes=period-i),
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
                
                current_price = close_price
            
            return pd.DataFrame(data)
            
        except Exception as e:
            log_error(f"모의 분봉 데이터 생성 실패: {str(e)}")
            return None
    
    def get_current_volume(self, stock_code: str) -> Optional[int]:
        """현재 거래량 조회"""
        try:
            # 실제로는 실시간 데이터에서 조회
            # 여기서는 모의 데이터 반환
            import random
            return random.randint(1000, 5000)
            
        except Exception as e:
            log_error(f"현재 거래량 조회 실패 {stock_code}: {str(e)}")
            return None
    
    def get_max_volume_during_rise(self, stock_code: str, tracking_info: dict) -> Optional[int]:
        """급등 기간 최대 거래량 조회"""
        try:
            # 실제로는 추적 시작일부터 현재까지의 최대 거래량 조회
            # 여기서는 모의 데이터 반환
            import random
            return random.randint(10000, 50000)
            
        except Exception as e:
            log_error(f"급등 기간 최대 거래량 조회 실패 {stock_code}: {str(e)}")
            return None
    
    def update_settings(self, rsi_threshold: float = None, 
                       volume_ratio_threshold: float = None,
                       support_tolerance: float = None):
        """설정값 업데이트"""
        try:
            if rsi_threshold is not None:
                self.rsi_threshold = rsi_threshold
            
            if volume_ratio_threshold is not None:
                self.volume_ratio_threshold = volume_ratio_threshold
            
            if support_tolerance is not None:
                self.support_tolerance = support_tolerance
            
            # 캐시 초기화
            self.clear_cache()
            
            log_info("지지 조건 분석기 설정 업데이트 완료")
            
        except Exception as e:
            log_error(f"설정 업데이트 실패: {str(e)}")
    
    def clear_cache(self):
        """캐시 초기화"""
        try:
            self.rsi_cache.clear()
            self.support_cache.clear()
            self.volume_cache.clear()
            
            log_debug("지지 조건 분석기 캐시 초기화 완료")
            
        except Exception as e:
            log_error(f"캐시 초기화 실패: {str(e)}")
    
    def get_analysis_summary(self, stock_code: str) -> dict:
        """분석 요약 정보 조회"""
        try:
            # 최근 분석 결과 요약
            summary = {
                'stock_code': stock_code,
                'last_analysis_time': datetime.now().isoformat(),
                'cache_status': {
                    'rsi_cached': len([k for k in self.rsi_cache.keys() if stock_code in k]),
                    'support_cached': len([k for k in self.support_cache.keys() if stock_code in k]),
                    'volume_cached': len([k for k in self.volume_cache.keys() if stock_code in k])
                },
                'settings': {
                    'rsi_threshold': self.rsi_threshold,
                    'volume_ratio_threshold': self.volume_ratio_threshold,
                    'support_tolerance': self.support_tolerance
                }
            }
            
            return summary
            
        except Exception as e:
            log_error(f"분석 요약 조회 실패 {stock_code}: {str(e)}")
            return {}
    
    def cleanup_old_cache(self, hours: int = 1):
        """오래된 캐시 정리"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=hours)
            
            # 시간 기반 캐시 키 정리
            for cache_dict in [self.rsi_cache, self.support_cache, self.volume_cache]:
                keys_to_remove = []
                
                for key in cache_dict.keys():
                    try:
                        # 캐시 키에서 시간 정보 추출
                        time_part = key.split('_')[-1]  # HHMM 형식
                        cache_hour = int(time_part[:2])
                        cache_minute = int(time_part[2:])
                        
                        cache_time = current_time.replace(hour=cache_hour, minute=cache_minute, second=0, microsecond=0)
                        
                        if cache_time < cutoff_time:
                            keys_to_remove.append(key)
                            
                    except (ValueError, IndexError):
                        # 잘못된 형식의 키는 제거
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del cache_dict[key]
            
            log_debug(f"오래된 캐시 정리 완료: {hours}시간 이전 데이터 제거")
            
        except Exception as e:
            log_error(f"캐시 정리 실패: {str(e)}")
    
    def get_statistics(self) -> dict:
        """분석기 통계 조회"""
        try:
            return {
                'cache_sizes': {
                    'rsi_cache': len(self.rsi_cache),
                    'support_cache': len(self.support_cache),
                    'volume_cache': len(self.volume_cache)
                },
                'settings': {
                    'rsi_threshold': self.rsi_threshold,
                    'volume_ratio_threshold': self.volume_ratio_threshold,
                    'support_tolerance': self.support_tolerance
                },
                'last_cleanup': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(f"통계 조회 실패: {str(e)}")
            return {}