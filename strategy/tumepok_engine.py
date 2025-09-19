# 투매폭 자동매매 시스템 - 투매폭 전략 엔진
"""
Tumepok Engine for Tumepok Trading System
투매폭 매매 전략의 메인 엔진입니다.
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from utils.enhanced_logging import log_info, log_error, log_debug, log_trading, log_warning
from utils.calculator import TumepokCalculator
from utils.sold_stocks_manager import SoldStocksManager
from config.constants import TRACKING_STATUS, BUY_STAGES, SELL_REASONS, TUMEPOK_MATRIX
from .rise_tracker import RiseTracker
from .support_analyzer import SupportAnalyzer


class TumepokEngine:
    """투매폭 전략 메인 엔진 (기존 큐 시스템 통합)"""
    
    def __init__(self, main_window, queue_manager=None):
        """투매폭 엔진 초기화"""
        self.main_window = main_window
        self.config = main_window.tumepok_config if hasattr(main_window, 'tumepok_config') else None
        
        # 큐 시스템 연결
        self.queue_manager = queue_manager
        if queue_manager:
            self.tr_req_queue = queue_manager.tr_req_queue
            self.tr_result_queue = queue_manager.tr_result_queue
            self.order_tr_req_queue = queue_manager.order_tr_req_queue
            self.websocket_req_queue = queue_manager.websocket_req_queue
            self.websocket_result_queue = queue_manager.websocket_result_queue
            log_info("투매폭 엔진 - 큐 시스템 연결됨")
        else:
            # 기존 main_window의 큐 시스템 사용
            if hasattr(main_window, 'tr_req_queue'):
                self.tr_req_queue = main_window.tr_req_queue
                self.tr_result_queue = main_window.tr_result_queue
                self.order_tr_req_queue = main_window.order_tr_req_queue
                self.websocket_req_queue = main_window.websocket_req_queue
                self.websocket_result_queue = main_window.websocket_result_queue
                log_info("투매폭 엔진 - 기존 main_window 큐 시스템 사용")
            else:
                log_error("큐 시스템을 찾을 수 없음")
        
        # 연속상승 추적기
        self.rise_tracker = RiseTracker()
        
        # 지지 조건 분석기
        self.support_analyzer = SupportAnalyzer(main_window)
        
        # 기존 연속상승 추적 데이터 로드
        rise_tracker_file = "rise_tracker_data.json"
        try:
            self.rise_tracker.load_tracking_data(rise_tracker_file)
            log_info(f"연속상승 추적 데이터 로드 완료: {len(self.rise_tracker.tracking_stocks)}개 종목")
        except Exception as e:
            log_info(f"연속상승 추적 데이터 로드 실패 (새로 시작): {str(e)}")
        
        # 매수 이력 데이터 로드
        self.load_bought_history()
        
        # 매도 종목 관리자 초기화 (재매수 금지 기능)
        self.sold_stocks_manager = SoldStocksManager()
        log_info("매도 종목 관리자 초기화 완료")
        
        # 추적 중인 종목들 (기존 호환성 유지)
        self.tracking_stocks = {}  # {종목코드: TrackingInfo}
        
        # 포지션 관리 중인 종목들
        self.positions = {}  # {종목코드: PositionInfo}
        
        # 매수 이력 추적 (추적->매수->매도 과정을 거친 종목들)
        self.bought_stocks_history = set()  # {종목코드}
        
        # 엔진 상태
        self.is_active = False
        self.last_scan_time = None
        self.scanned_stocks = set()  # 이미 스캔된 종목 (중복 방지)
        
        # 성능 통계
        self.stats = {
            'total_scanned': 0,
            'total_tracked': 0,
            'total_bought': 0,
            'total_sold': 0,
            'success_rate': 0.0
        }
        
        log_info("투매폭 엔진 초기화 완료")
    
    def start_engine(self):
        """투매폭 엔진 시작"""
        try:
            self.is_active = True
            self.scanned_stocks.clear()
            
            # 기존 추적 종목들에 대해 실시간 등록 재요청
            self.register_existing_stocks_for_realtime()
            
            # 급등주 스캔 시작
            self.start_rising_stock_scan()
            
            log_info("투매폭 엔진 시작됨")
            
        except Exception as e:
            log_error(f"투매폭 엔진 시작 실패: {str(e)}")
    
    def register_existing_stocks_for_realtime(self):
        """기존 추적 종목들에 대해 실시간 등록 재요청 (제한적으로)"""
        try:
            if not self.websocket_req_queue:
                log_debug("WebSocket 큐가 없어 실시간 등록 불가")
                return
            
            total_stocks = 0
            registered_stocks = 0
            max_realtime_stocks = 8  # 실시간 등록 최대 종목 수 제한 (과부하 방지 강화)
            
            # 연속상승 추적기의 추적 종목들 (상위 몇 개만)
            if self.rise_tracker:
                tracking_stocks = self.rise_tracker.tracking_stocks
                total_stocks += len(tracking_stocks)
                
                # 중요한 상태(BUYING, TRACKING) 종목 우선 등록
                priority_stocks = []
                normal_stocks = []
                
                for stock_code, data in tracking_stocks.items():
                    status = getattr(data, 'status', 'READY')
                    if status in ['BUYING', 'TRACKING']:
                        priority_stocks.append(stock_code)
                    else:
                        normal_stocks.append(stock_code)
                
                # 우선순위 종목 먼저 등록
                for stock_code in priority_stocks[:max_realtime_stocks]:
                    if registered_stocks >= max_realtime_stocks:
                        break
                    self.websocket_req_queue.put({
                        'action_id': '실시간등록',
                        '종목코드': stock_code,
                        'data_type': '0B'  # 주식체결
                    })
                    log_info(f"기존 추적 종목 실시간 등록 재요청: {stock_code}")
                    registered_stocks += 1
                
                # 남은 자리에 일반 종목 등록
                remaining_slots = max_realtime_stocks - registered_stocks
                for stock_code in normal_stocks[:remaining_slots]:
                    self.websocket_req_queue.put({
                        'action_id': '실시간등록',
                        '종목코드': stock_code,
                        'data_type': '0B'  # 주식체결
                    })
                    log_info(f"기존 추적 종목 실시간 등록 재요청: {stock_code}")
                    registered_stocks += 1
            
            # 투매폭 추적 종목들 (이미 등록된 것 제외)
            for stock_code in list(self.tracking_stocks.keys())[:5]:  # 최대 5개만
                if registered_stocks >= max_realtime_stocks:
                    break
                self.websocket_req_queue.put({
                    'action_id': '실시간등록',
                    '종목코드': stock_code,
                    'data_type': '0B'  # 주식체결
                })
                log_info(f"투매폭 추적 종목 실시간 등록 재요청: {stock_code}")
                registered_stocks += 1
            
            log_info(f"기존 추적 종목 실시간 등록 재요청 완료: {registered_stocks}개 (전체 {total_stocks}개 중)")
            
            if total_stocks > max_realtime_stocks:
                log_warning(f"실시간 등록 제한으로 {total_stocks - registered_stocks}개 종목 제외됨")
            
        except Exception as e:
            log_error(f"실시간 등록 재요청 실패: {str(e)}")
    
    def stop_engine(self):
        """투매폭 엔진 중지"""
        try:
            self.is_active = False
            
            # 연속상승 추적 데이터 최종 저장
            self.save_rise_tracker_data()
            
            log_info("투매폭 엔진 중지됨")
            
        except Exception as e:
            log_error(f"투매폭 엔진 중지 실패: {str(e)}")
    

    def start_rising_stock_scan(self):
        """급등주 스캔 시작 (큐 시스템 활용)"""
        try:
            if not self.is_active:
                return
            
            # 큐 시스템을 통한 등락률 상위 종목 조회
            if self.queue_manager:
                self.queue_manager.send_tr_request(
                    action_id="등락률상위조회",
                    purpose="TUMEPOK_SCAN",
                    mrkt_tp="000",      # 시장구분 (전체)
                    sort_tp="1",        # 정렬구분 (등락률 상위)
                    updown_incls="1"    # 상승종목만
                )
            elif hasattr(self, 'tr_req_queue') and self.tr_req_queue:
                # 기존 방식 호환
                self.tr_req_queue.put({
                    'action_id': '등락률상위조회',
                    'purpose': 'TUMEPOK_SCAN',
                    'mrkt_tp': '000',
                    'sort_tp': '1',
                    'updown_incls': '1'
                })
            else:
                log_error("TR 요청 시스템을 사용할 수 없음")
            
            self.last_scan_time = datetime.now()
            log_debug("급등주 스캔 요청 전송")
            
        except Exception as e:
            log_error(f"급등주 스캔 시작 실패: {str(e)}")
    
    def on_realtime_data(self, data):
        """실시간 데이터 처리"""
        try:
            if not self.is_active:
                log_debug(f"[DEBUG] 투매폭 엔진 비활성 상태로 실시간 데이터 스킵: {data.get('종목코드')}")
                return
            
            stock_code = data.get('종목코드')
            current_price = data.get('현재가', 0)
            change_rate = data.get('등락률', data.get('전일대비율', 0))  # WebSocket에서 등락률로 전송됨
            high_price = data.get('고가', None)  # 당일 고가 (키움 API 필드 17)
            
            # 디버그: 모든 실시간 데이터 수신 확인
            log_debug(f"[DEBUG] 실시간 데이터 수신: {stock_code}, 현재가: {current_price}, 등락률: {change_rate}, 고가: {high_price}, 활성: {self.is_active}")
            
            if not stock_code or current_price <= 0:
                log_debug(f"[DEBUG] 유효하지 않은 데이터로 스킵: stock_code={stock_code}, current_price={current_price}")
                return
            
            # 디버그: 보유 포지션 실시간 데이터 수신 확인
            if stock_code in self.positions:
                log_info(f"[포지션] 실시간 데이터 수신: {stock_code}, 현재가: {current_price:,}원, 등락률: {change_rate:.2f}%")
            
            # 타입 변환 (필요시)
            if isinstance(change_rate, str):
                change_rate = change_rate.replace('+', '').replace('%', '')
                try:
                    change_rate = float(change_rate)
                except ValueError:
                    change_rate = 0.0
            
            # 급등주 감지 (20% 이상) - 신규 추적 추가 (재매수 제한 확인 포함)
            rise_threshold = self.config.get_rise_threshold() if self.config else 20.0
            if change_rate >= rise_threshold and stock_code not in self.tracking_stocks:
                if self.add_to_tracking(stock_code, current_price, change_rate):
                    log_info(f"신규 급등주 발견: {stock_code}, 등락률: {change_rate:.2f}%")
                # add_to_tracking에서 재매수 제한 확인하므로 실패 시 자동으로 스킵됨
            
            # 연속상승 추적기 데이터 업데이트 (우선순위)
            if self.rise_tracker and stock_code in self.rise_tracker.tracking_stocks:
                update_result = self.rise_tracker.update_price(stock_code, current_price, change_rate, high_price)
                tracking_info = self.rise_tracker.get_tracking_info(stock_code)
                
                if tracking_info:
                    stock_name = tracking_info.stock_name or f"종목{stock_code}"
                    
                    # 주요 업데이트만 로깅 (5분마다)
                    import time
                    current_minute = int(time.time()) // 300  # 5분 단위
                    cache_key = f"{stock_code}_{current_minute}"
                    
                    if not hasattr(self, 'last_log_cache'):
                        self.last_log_cache = {}
                    
                    if cache_key not in self.last_log_cache:
                        log_info(f"연속상승 업데이트: {stock_name}({stock_code}) - "
                                f"현재가: {current_price:,}원, 등락률: {change_rate:.2f}%, "
                                f"상승률: {tracking_info.rise_rate:.1f}%, 하락률: {tracking_info.drop_rate:.1f}%, "
                                f"상태: {tracking_info.status}")
                        self.last_log_cache[cache_key] = True
                    
                    # 고점 갱신 시 데이터 저장
                    if update_result == "HIGH_UPDATED":
                        self.save_rise_tracker_data()
                        log_info(f"고점 갱신: {stock_name}({stock_code}) - 새 고점: {current_price:,}원")
                    
                    # 투매폭 연동 처리 - 연속상승 추적기 데이터 기반
                    if tracking_info.status in ['READY', 'WAITING']:
                        self.process_tumepok_signal(stock_code, tracking_info)
                    
                    # RiseTracker 업데이트 시 추적현황 테이블 즉시 업데이트
                    if hasattr(self.main_window, 'tumepok_panel') and self.main_window.tumepok_panel:
                        try:
                            tracking_df = self.get_tracking_dataframe()
                            self.main_window.tumepok_panel.update_tracking_data(tracking_df)
                        except Exception as update_error:
                            log_debug(f"RiseTracker 추적현황 테이블 즉시 업데이트 실패: {update_error}")
            
            # 전용 추적 종목 업데이트 (하위 호환성)
            elif stock_code in self.tracking_stocks:
                self.update_tracking_stock(stock_code, current_price, change_rate)
                
                # 추적 종목 테이블 즉시 업데이트
                if hasattr(self.main_window, 'tumepok_panel') and self.main_window.tumepok_panel:
                    try:
                        tracking_df = self.get_tracking_dataframe()
                        self.main_window.tumepok_panel.update_tracking_data(tracking_df)
                    except Exception as update_error:
                        log_debug(f"추적 테이블 즉시 업데이트 실패: {update_error}")
            
            # 포지션 관리 중인 종목 업데이트
            if stock_code in self.positions:
                log_debug(f"포지션 업데이트 호출: {stock_code}, 현재가: {current_price:,}원, 등락률: {change_rate:.2f}%")
                self.update_position(stock_code, current_price)
                
                # 즉시 테이블 업데이트 (베이스코드 방식)
                if hasattr(self.main_window, 'update_account_table'):
                    try:
                        self.main_window.update_account_table()
                    except Exception as update_error:
                        log_debug(f"계좌 테이블 즉시 업데이트 실패: {update_error}")
                
                # 포지션 테이블은 0.5초 정기 업데이트에서 처리 (포트폴리오 방식)
                log_debug(f"포지션 업데이트 완료: {stock_code} (정기 업데이트에서 테이블 반영)")
                
        except Exception as e:
            log_error(f"실시간 데이터 처리 실패: {stock_code}, {str(e)}")
    
    def on_condition_signal(self, data):
        """조건식 편입/편출 신호 처리 - 비활성화"""
        try:
            # 조건식 신호 처리 완전 차단
            rebuy_config = self.config.get_rebuy_restriction_config() if self.config else {}
            if rebuy_config.get('enabled', True):
                log_debug("조건식 신호 차단됨 - 재매수 금지 설정 활성화")
                return
            
            if not self.is_active:
                return
            
            stock_code = data.get('종목코드')
            condition_idx = data.get('조건식idx')
            entry_exit = data.get('편입편출')  # I: 편입, E: 편출
            
            log_debug(f"조건식 신호 무시됨: {stock_code}, {entry_exit}")
            # 모든 조건식 신호 무시
            return
                
        except Exception as e:
            log_error(f"조건식 신호 처리 실패: {str(e)}")
    
    def on_condition_entry(self, stock_code, condition_idx):
        """조건식 편입 처리"""
        try:
            # 조건식 연동 관리자를 통한 처리
            if hasattr(self.main_window, 'condition_integration_manager'):
                integration_manager = self.main_window.condition_integration_manager
                
                # 투매폭 스캔용 조건식인지 확인
                if integration_manager.is_tumepok_scan_condition(condition_idx):
                    self.on_condition_scan_result(stock_code, condition_idx)
                    return
                
                # 투매폭 확인용 조건식인지 확인
                if integration_manager.is_tumepok_confirm_condition(condition_idx):
                    self.on_condition_buy_signal(stock_code, condition_idx)
                    return
            
            # 기본 처리: 급등주로 간주하여 추적 시작
            self._start_tracking_from_condition(stock_code, condition_idx)
            
        except Exception as e:
            log_error(f"조건식 추적 시작 실패: {str(e)}")
    
    def _process_condition_confirmed_buy(self, stock_code, condition_idx):
        """조건식 확인된 매수 처리"""
        try:
            tracking_info = self.tracking_stocks[stock_code]
            
            # 현재 가격 정보 확인
            current_price = tracking_info.get('current_price', 0)
            if current_price <= 0:
                log_debug(f"유효하지 않은 현재가: {stock_code}")
                return
            
            # 투매폭 매수 단계 확인
            buy_stage = self._get_buy_stage(stock_code, current_price)
            if buy_stage == 'WAIT':
                log_debug(f"투매폭 매수 대기 상태: {stock_code}")
                return
            
            # 조건식 신호를 추가 확신 요소로 활용하여 매수 실행
            log_info(f"조건식 확인 매수: {stock_code} - {buy_stage}단계 (조건식: {condition_idx})")
            
            # 지지 조건 확인 (조건식 신호가 있으므로 완화된 조건 적용)
            support_result = self.support_analyzer.check_all_conditions(
                stock_code, tracking_info, condition_confirmed=True
            )
            
            # 조건식 확인이 있으므로 지지 조건 요구사항 완화
            required_conditions = max(1, self.config.get_condition_requirements(buy_stage) - 1)
            
            if support_result['satisfied_count'] >= required_conditions:
                self.execute_buy_order(stock_code, buy_stage, condition_confirmed=condition_idx)
            else:
                log_debug(f"지지 조건 미충족: {stock_code} "
                         f"({support_result['satisfied_count']}/{required_conditions})")
            
        except Exception as e:
            log_error(f"조건식 확인 매수 처리 실패: {str(e)}")
    
    def on_condition_scan_result(self, stock_code, condition_idx):
        """조건식 스캔 결과 처리 (급등주 확인용)"""
        try:
            log_debug(f"조건식 스캔 결과: {stock_code} (조건식: {condition_idx})")
            
            # 이미 추적 중인지 확인
            if stock_code in self.tracking_stocks:
                log_debug(f"이미 추적 중인 종목: {stock_code}")
                return
            
            # 최대 추적 종목 수 확인
            max_tracking = self.config.get_max_tracking_stocks()
            if len(self.tracking_stocks) >= max_tracking:
                log_debug(f"최대 추적 종목 수 초과: {len(self.tracking_stocks)}/{max_tracking}")
                return
            
            # 조건식에서 감지된 종목을 급등주로 간주하여 추적 시작
            self._start_tracking_from_condition(stock_code, condition_idx)
            
        except Exception as e:
            log_error(f"조건식 스캔 결과 처리 실패: {str(e)}")
    
    def on_condition_buy_signal(self, stock_code, condition_idx):
        """조건식 매수 신호 처리 (투매폭 확인용)"""
        try:
            log_debug(f"조건식 매수 신호: {stock_code} (조건식: {condition_idx})")
            
            # 투매폭 추적 중인 종목인지 확인
            if stock_code not in self.tracking_stocks:
                log_debug(f"투매폭 추적 중이 아닌 종목: {stock_code}")
                return
            
            tracking_info = self.tracking_stocks[stock_code]
            
            # 투매폭 진입 조건 확인
            if tracking_info.get('status') == 'READY':
                # 조건식 신호를 추가 확인 요소로 활용
                self._process_condition_confirmed_buy(stock_code, condition_idx)
            else:
                log_debug(f"투매폭 진입 대기 상태가 아님: {stock_code} (상태: {tracking_info.get('status')})")
            
        except Exception as e:
            log_error(f"조건식 매수 신호 처리 실패: {str(e)}")
    
    def _start_tracking_from_condition(self, stock_code, condition_idx):
        """조건식에서 감지된 종목 추적 시작"""
        try:
            # 종목 기본정보 요청 (큐 시스템 활용)
            if self.queue_manager:
                self.queue_manager.send_tr_request(
                    action_id="주식기본정보",
                    종목코드=stock_code,
                    purpose="TUMEPOK_TRACKING",
                    condition_idx=condition_idx
                )
            elif hasattr(self, 'tr_req_queue') and self.tr_req_queue:
                self.tr_req_queue.put({
                    'action_id': '주식기본정보',
                    '종목코드': stock_code,
                    'purpose': 'TUMEPOK_TRACKING',
                    'condition_idx': condition_idx
                })
            else:
                log_error("TR 요청 시스템을 사용할 수 없음")
            
            log_debug(f"조건식 편입 - 기본정보 요청: {stock_code}")
            
        except Exception as e:
            log_error(f"조건식 편입 처리 실패: {stock_code}, {str(e)}")
    
    def on_condition_exit(self, stock_code, condition_idx):
        """조건식 편출 처리"""
        try:
            # 포지션이 있으면 매도 신호 발생
            if stock_code in self.positions:
                self.execute_sell_order(stock_code, SELL_REASONS['CONDITION_EXIT'])
                log_trading(f"조건식 편출 매도: {stock_code}")
            
            # 추적 중이면 추적 중단
            if stock_code in self.tracking_stocks:
                self.remove_tracking(stock_code)
                log_debug(f"조건식 편출 - 추적 중단: {stock_code}")
                
        except Exception as e:
            log_error(f"조건식 편출 처리 실패: {stock_code}, {str(e)}")
    
    def on_stock_basic_info(self, data):
        """종목 기본정보 수신 처리"""
        try:
            purpose = data.get('purpose')

            if purpose == "TUMEPOK_TRACKING":
                self.add_tracking_from_basic_info(data)
            elif purpose == "TUMEPOK_SCAN":
                self.process_scan_result(data)

        except Exception as e:
            log_error(f"종목 기본정보 처리 실패: {str(e)}")


    def add_tracking_from_basic_info(self, data):
        """기본정보로부터 추적 추가"""
        try:
            stock_code = data.get('종목코드')
            stock_name = data.get('종목명')
            current_price = data.get('현재가', 0)
            condition_idx = data.get('condition_idx', 0)
            
            if not stock_code or current_price <= 0:
                log_error(f"잘못된 기본정보: {stock_code}, {current_price}")
                return
            
            # 필터링 조건 확인
            if not self.is_valid_tracking_stock(data):
                log_debug(f"추적 조건 미충족: {stock_name}({stock_code})")
                return
            
            # 추적 정보 생성
            tracking_info = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'start_date': datetime.now().strftime('%Y%m%d'),
                'start_price': current_price,
                'high_price': current_price,
                'current_price': current_price,
                'rise_days': 1,
                'rise_rate': 0.0,
                'drop_rate': 0.0,
                'status': TRACKING_STATUS['TRACKING'],
                'condition_name': self.main_window.get_condition_name(condition_idx),
                'condition_idx': condition_idx,
                'waiting_days': 0,
                'bought_stages': set(),
                'target_drop_info': None,
                'created_time': datetime.now()
            }
            
            self.tracking_stocks[stock_code] = tracking_info
            
            # 실시간 등록
            self.main_window.queue_manager.send_websocket_request(
                "실시간등록",
                종목코드=stock_code
            )
            
            log_trading(f"투매폭 추적 시작: {stock_name}({stock_code}), 시작가: {current_price:,}원")
            
        except Exception as e:
            log_error(f"추적 추가 실패: {str(e)}")
    
    def on_realtime_price_update(self, stock_code, price_data):
        """실시간 가격 업데이트 처리"""
        try:
            if not self.is_active:
                return
            
            current_price = price_data.get('현재가', 0)
            change_rate = price_data.get('등락률', 0.0)
            high_price = price_data.get('고가', 0)  # 실시간 고가 정보
            
            # 등락률 숫자 변환
            if isinstance(change_rate, str):
                change_rate = change_rate.replace('+', '').replace('%', '')
                try:
                    change_rate = float(change_rate)
                except ValueError:
                    change_rate = 0.0
            
            # 추적 중이 아닌 종목이면 자동 추가 (실시간 체결 기반) - 재매수 제한 확인 포함
            if stock_code not in self.tracking_stocks:
                # 등락률이 15% 이상인 종목을 자동 추적에 추가 (강한 상승세)
                if change_rate >= 15.0:  # 15% 이상 상승
                    if self.add_to_tracking(stock_code, current_price, change_rate):
                        log_info(f"실시간 자동 추적 추가: {stock_code}, 현재가: {current_price:,}원, 등락률: {change_rate:.1f}%")
                    # add_to_tracking에서 재매수 제한 확인하므로 실패 시 자동으로 스킵됨
            
            # 추적 중인 종목 업데이트
            if stock_code in self.tracking_stocks:
                self.update_tracking_stock(stock_code, current_price, change_rate, high_price)
            
            # 포지션 관리 중인 종목 업데이트
            if stock_code in self.positions:
                log_debug(f"포지션 업데이트 호출: {stock_code}, 현재가: {current_price:,}원, 등락률: {change_rate:.2f}%")
                self.update_position(stock_code, current_price)
                
                # 포지션 테이블은 0.5초 정기 업데이트에서 처리 (포트폴리오 방식)
                
        except Exception as e:
            log_error(f"실시간 가격 업데이트 실패: {stock_code}, {str(e)}")
    
    def update_tracking_stock(self, stock_code, current_price, change_rate=None, high_price=None):
        """추적 종목 업데이트"""
        try:
            tracking_info = self.tracking_stocks[stock_code]
            tracking_info['current_price'] = current_price

            # 실시간 등락률이 있으면 업데이트 (당일 등락률만 저장)
            if change_rate is not None:
                tracking_info['daily_change_rate'] = change_rate
                # 상승률은 누적 계산이므로 여기서는 업데이트하지 않음

            base_price = tracking_info.get('base_price', tracking_info.get('start_price', 0))

            # 고가 갱신 로직 통합
            high_updated = False
            final_high_price = tracking_info['high_price']

            # 실시간 고가 정보가 있으면 우선 사용
            if high_price is not None and high_price > 0:
                # 키움 고가가 현재 고점보다 높으면 업데이트
                if high_price > tracking_info['high_price']:
                    old_high = tracking_info['high_price']
                    tracking_info['high_price'] = high_price
                    final_high_price = high_price
                    high_updated = True
                    log_info(f"실시간 고가 갱신: {stock_code} {old_high:,}원 → {high_price:,}원")
                # 현재가가 키움 고가보다도 높으면 현재가로 갱신
                elif current_price > high_price and current_price > tracking_info['high_price']:
                    old_high = tracking_info['high_price']
                    tracking_info['high_price'] = current_price
                    final_high_price = current_price
                    high_updated = True
                    log_info(f"현재가가 키움고가 초과: {stock_code} {old_high:,}원 → {current_price:,}원 (키움고가: {high_price:,}원)")
            else:
                # 고가 정보가 없으면 현재가로만 고점 갱신
                if current_price > tracking_info['high_price']:
                    old_high = tracking_info['high_price']
                    tracking_info['high_price'] = current_price
                    final_high_price = current_price
                    high_updated = True
                    log_info(f"현재가 고점 갱신: {stock_code} {old_high:,}원 → {current_price:,}원")

            # 고가가 갱신되었으면 상승일수 증가
            if high_updated:
                tracking_info['rise_days'] += 1
                tracking_info.setdefault('waiting_days', 0)
                tracking_info['waiting_days'] = 0
                tracking_info['status'] = TRACKING_STATUS['TRACKING']
            
            # 하락률 계산 (고점 대비)
            final_high_price = tracking_info['high_price']
            if final_high_price > 0:
                drop_rate = (final_high_price - current_price) / final_high_price * 100
                tracking_info['drop_rate'] = drop_rate
            else:
                drop_rate = 0
                tracking_info['drop_rate'] = 0

            # 현재 상승률 계산 (기준가 대비)
            if base_price > 0:
                current_rise_rate = (final_high_price - base_price) / base_price * 100
            else:
                current_rise_rate = 0
            
            # 누적 상승률을 현재 상승률로 설정 (고점 기준 상승률)
            cumulative_rise_rate = current_rise_rate
            tracking_info['cumulative_rise_rate'] = cumulative_rise_rate
            
            # 투매폭 진입 조건 확인 (누적 상승률에 따른 적정 하락폭)
            target_drops = self._get_target_drop_rates(cumulative_rise_rate)
            min_drop_rate = target_drops['1차']
            stop_loss_rate = target_drops['손절']
            
            # 손절 체크 (최대 하락폭 초과 시)
            if drop_rate > stop_loss_rate:
                # 포지션이 있으면 손절, 없으면 추적 중단
                if tracking_info.get('bought_stages'):
                    # 중복 손절 실행 방지 체크
                    position = self.positions.get(stock_code, {})
                    if not position.get('stop_loss_executed', False):
                        log_error(f"⚠️ 손절 신호: {stock_code} - 하락률 {drop_rate:.1f}% > 최대 {stop_loss_rate:.1f}%")
                        self.execute_stop_loss(stock_code, "최대 하락폭 초과")
                    else:
                        log_debug(f"손절 이미 실행됨 - 스킵: {stock_code}")
                else:
                    log_info(f"추적 중단: {stock_code} - 적정 하락폭 이탈 (하락률: {drop_rate:.1f}%)")
                    tracking_info['status'] = TRACKING_STATUS.get('STOPPED', 'STOPPED')
                return
            
            # 적정 하락폭 범위 내에서 매수 검토
            if min_drop_rate <= drop_rate <= stop_loss_rate:
                tracking_info['status'] = TRACKING_STATUS['READY']
                
                # 매수 단계 확인 후 조건 검토
                buy_stage = self._get_buy_stage(stock_code, current_price)
                if buy_stage != 'WAIT':
                    self.check_buy_conditions(stock_code)
                    log_info(f"투매폭 매수 검토: {stock_code}, 하락률: {drop_rate:.1f}% "
                            f"→ {buy_stage} 단계 (범위: {min_drop_rate:.1f}% ~ {stop_loss_rate:.1f}%)")
                else:
                    log_debug(f"투매폭 대기: {stock_code}, 하락률: {drop_rate:.1f}% "
                             f"(범위: {min_drop_rate:.1f}% ~ {stop_loss_rate:.1f}%)")
            elif tracking_info['status'] == TRACKING_STATUS['TRACKING']:
                # 반등 대기 시작
                tracking_info['status'] = TRACKING_STATUS['WAITING']
                tracking_info.setdefault('waiting_days', 0)
                tracking_info['waiting_days'] += 1
                
                # 3일 대기 후 강제 진입
                if tracking_info['waiting_days'] >= 3:
                    tracking_info['status'] = TRACKING_STATUS['READY']
                    
                    # 강제 진입 시에도 매수 단계 확인
                    buy_stage = self._get_buy_stage(stock_code, current_price)
                    if buy_stage != 'WAIT':
                        self.check_buy_conditions(stock_code)
                        log_info(f"3일 대기 완료 - 강제 진입: {stock_code} "
                                f"→ {buy_stage} 단계 (누적상승률: {cumulative_rise_rate:.1f}%)")
                    else:
                        log_info(f"3일 대기 완료 - 하락폭 부족으로 대기 지속: {stock_code} "
                                f"(하락률: {drop_rate:.1f}%, 누적상승률: {cumulative_rise_rate:.1f}%)")
            
        except Exception as e:
            log_error(f"추적 종목 업데이트 실패: {stock_code}, {str(e)}")
    
    def _get_min_drop_rate(self, cumulative_rise_rate):
        """누적 상승률에 따른 최소 하락률 반환 (투매폭 매트릭스 기준)"""
        for matrix_row in TUMEPOK_MATRIX:
            if matrix_row['rise_min'] <= cumulative_rise_rate <= matrix_row['rise_max']:
                return matrix_row['drop_min']
        
        # 범위를 벗어나는 경우 마지막 구간 사용
        return TUMEPOK_MATRIX[-1]['drop_min']
    
    def _get_target_drop_rates(self, cumulative_rise_rate):
        """누적 상승률에 따른 투매폭 매수선별 하락률 반환"""
        # 투매폭 매트릭스에서 해당 구간 찾기
        for matrix_row in TUMEPOK_MATRIX:
            if matrix_row['rise_min'] <= cumulative_rise_rate <= matrix_row['rise_max']:
                drop_min = matrix_row['drop_min']
                drop_max = matrix_row['drop_max']
                # 3단계 매수선 계산 (적정 하락폭 범위 내에서만)
                # 1차: 최소 하락폭 진입
                # 2차: 중간 지점
                # 3차: 최대 하락폭의 90% (여유 10% 확보)
                drop_mid = drop_min + (drop_max - drop_min) * 0.5
                drop_3rd = drop_min + (drop_max - drop_min) * 0.9  # 최대 하락폭의 90%
                return {
                    '1차': drop_min,      # 1차선: 최소 하락폭
                    '2차': drop_mid,      # 2차선: 중간 하락폭  
                    '3차': drop_3rd,      # 3차선: 최대 하락폭의 90%
                    '손절': drop_max      # 손절선: 최대 하락폭 초과
                }
        
        # 범위를 벗어나는 경우 마지막 구간 사용
        last_row = TUMEPOK_MATRIX[-1]
        drop_min = last_row['drop_min']
        drop_max = last_row['drop_max']
        drop_mid = drop_min + (drop_max - drop_min) * 0.5
        drop_3rd = drop_min + (drop_max - drop_min) * 0.9
        return {
            '1차': drop_min,
            '2차': drop_mid,
            '3차': drop_3rd,
            '손절': drop_max
        }
    
    def check_buy_conditions(self, stock_code):
        """매수 조건 확인"""
        try:
            # 재매수 금지 확인
            rebuy_config = self.config.get_rebuy_restriction_config() if self.config else {}
            if rebuy_config.get('enabled', True):
                restriction_days = rebuy_config.get('restriction_days', 5)
                if self.sold_stocks_manager.is_rebuy_restricted(stock_code, restriction_days):
                    log_debug(f"재매수 금지: {stock_code} ({restriction_days}일 제한)")
                    return
            
            tracking_info = self.tracking_stocks[stock_code]
            current_price = tracking_info['current_price']
            high_price = tracking_info['high_price']
            rise_rate = tracking_info['rise_rate']
            
            # 매수 단계 판단
            buy_stage = TumepokCalculator.determine_buy_stage(current_price, high_price, rise_rate)
            
            if buy_stage == 'WAIT':
                return
            
            # 이미 해당 단계를 매수했는지 확인
            if buy_stage in tracking_info['bought_stages']:
                return
            
            # 지지 조건 확인
            conditions_met = self.check_support_conditions(stock_code, tracking_info)
            
            # 단계별 조건 완화 적용
            condition_requirements = self.config.get_condition_requirements()
            required_conditions = condition_requirements.get(buy_stage, 2)
            
            # 투매폭 계산기를 이용한 매수 단계 검증
            buy_stage_calculated = self._get_buy_stage(stock_code, current_price)
            if buy_stage != buy_stage_calculated:
                log_debug(f"매수 단계 불일치: {stock_code}, 요청={buy_stage}, 계산={buy_stage_calculated}")
                return
            
            if conditions_met >= required_conditions:
                log_info(f"매수 조건 충족: {tracking_info.get('stock_name', stock_code)}({stock_code}) "
                        f"{buy_stage} - 지지조건 {conditions_met}/{required_conditions}개, "
                        f"하락률 {tracking_info.get('drop_rate', 0):.1f}%")
                self.execute_buy_order(stock_code, buy_stage)
            else:
                log_debug(f"지지조건 부족: {stock_code}, 충족: {conditions_met}/{required_conditions}")
                
        except Exception as e:
            log_error(f"매수 조건 확인 실패: {stock_code}, {str(e)}")
    
    def _get_buy_stage(self, stock_code, current_price):
        """매수 단계 결정"""
        try:
            if stock_code not in self.tracking_stocks:
                return 'WAIT'
            
            tracking_info = self.tracking_stocks[stock_code]
            high_price = tracking_info['high_price']
            drop_rate = tracking_info.get('drop_rate', 0)
            cumulative_rise_rate = tracking_info.get('cumulative_rise_rate', tracking_info.get('rise_rate', 0))
            
            # 투매폭 매트릭스에 따른 단계별 하락률 기준
            target_drops = self._get_target_drop_rates(cumulative_rise_rate)
            
            # 이미 매수한 단계 확인
            bought_stages = tracking_info.get('bought_stages', set())
            
            # 1차: 최소 하락폭 도달
            if drop_rate >= target_drops['1차'] and '1차' not in bought_stages:
                return '1차'
            
            # 2차: 중간 하락폭 도달
            if drop_rate >= target_drops['2차'] and '2차' not in bought_stages:
                return '2차'
            
            # 3차: 최대 하락폭의 90% 도달
            if drop_rate >= target_drops['3차'] and '3차' not in bought_stages:
                return '3차'
            
            return 'WAIT'
            
        except Exception as e:
            log_error(f"매수 단계 결정 실패: {stock_code}, {str(e)}")
            return 'WAIT'
    
    def check_support_conditions(self, stock_code, tracking_info):
        """지지 조건 확인 (SupportAnalyzer 활용)"""
        try:
            if not self.support_analyzer:
                log_warning(f"지지 조건 분석기 없음: {stock_code}")
                return 1  # 기본값
            
            # 지지 조건 분석 실행
            analysis_result = self.support_analyzer.check_all_conditions(
                stock_code, tracking_info, condition_confirmed=False
            )
            
            satisfied_count = analysis_result.get('satisfied_count', 0)
            
            # 분석 결과 로깅
            details = analysis_result.get('details', {})
            rsi_info = details.get('rsi', {})
            support_info = details.get('support', {})
            volume_info = details.get('volume', {})
            
            log_debug(f"지지조건 분석 {stock_code}: "
                     f"RSI={rsi_info.get('rsi_value', 'N/A')} "
                     f"(과매도={analysis_result.get('rsi_oversold', False)}), "
                     f"지지선={len(support_info.get('support_levels', []))}개 "
                     f"(근처={analysis_result.get('support_level', False)}), "
                     f"거래량비율={volume_info.get('ratio', 'N/A')} "
                     f"(급감={analysis_result.get('volume_dried', False)}) "
                     f"→ {satisfied_count}/3개 만족")
            
            return satisfied_count
            
        except Exception as e:
            log_error(f"지지 조건 확인 실패: {stock_code}, {str(e)}")
            return 0
    
    def execute_buy_order(self, stock_code, buy_stage, condition_confirmed=None):
        """매수 주문 실행"""
        try:
            tracking_info = self.tracking_stocks[stock_code]
            current_price = tracking_info['current_price']
            rise_days = tracking_info['rise_days']
            
            # 포지션 크기 계산
            base_amount = self.config.get_base_buy_amount()
            stage_amount = self.config.get_buy_stage_amount(base_amount, buy_stage, rise_days)
            
            # 수량 계산
            quantity = TumepokCalculator.calculate_quantity(stage_amount, current_price)
            
            if quantity <= 0:
                log_error(f"매수 수량 부족: {stock_code}, 금액: {stage_amount}")
                return

            # 주문가격 계산
            order_price = TumepokCalculator.calculate_order_price(current_price, is_buy=True, market_order=True)

            # 매수 주문 전송
            if hasattr(self.main_window, 'queue_manager') and self.main_window.queue_manager:
                order_success = self.main_window.queue_manager.send_order_request(
                    "매수주문",
                    종목코드=stock_code,
                    주문수량=quantity,
                    주문가격=order_price,
                    매매전략="투매폭",
                    매수단계=buy_stage
                )

                # 주문 전송 성공 시 추적 시작 (첫 번째 매수)
                if order_success and hasattr(self.main_window, 'on_order_sent'):
                    import time
                    order_id = f"BUY1_{stock_code}_{int(time.time())}"  # 임시 주문 ID
                    self.main_window.on_order_sent({
                        'order_id': order_id,
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'order_type': '매수',
                        'quantity': quantity,
                        'price': order_price
                    })
            elif hasattr(self, 'order_tr_req_queue') and self.order_tr_req_queue:
                # 기존 방식 호환
                self.order_tr_req_queue.put({
                    'action_id': '주식매수주문',
                    'purpose': 'TUMEPOK_BUY',
                    '종목코드': stock_code,
                    '주문수량': quantity,
                    '주문가격': order_price,
                    '매매전략': '투매폭',
                    '매수단계': buy_stage
                })
            else:
                log_error(f"주문 시스템을 사용할 수 없음: {stock_code}")
                return
            
            # 매수 단계 기록 (메모리)
            tracking_info['bought_stages'].add(buy_stage)
            
            # 매수 단계 기록 (영구 저장 - RiseTracker에 기록)
            if hasattr(self, 'rise_tracker') and self.rise_tracker:
                try:
                    self.rise_tracker.update_bought_stages(stock_code, buy_stage)
                    log_debug(f"매수 단계 영구 저장: {stock_code} - {buy_stage}")
                except Exception as e:
                    log_error(f"매수 단계 저장 실패: {stock_code}, {e}")
            
            # UI 업데이트 - 자동매매 현황에 추가
            if hasattr(self.main_window, 'data_manager'):
                self.main_window.data_manager.add_auto_trade_info(
                    종목코드=stock_code,
                    종목명=tracking_info['stock_name'],
                    매수매도="매수",
                    수량=quantity,
                    가격=order_price,
                    상태="주문접수",
                    조건식=f"투매폭 {buy_stage}"
                )
                # 자동매매현황 테이블 즉시 업데이트
                if hasattr(self.main_window, 'update_auto_trade_table'):
                    self.main_window.update_auto_trade_table()
            
            # 조건식 확인 정보 포함 로깅
            condition_info = f" (조건식확인: {condition_confirmed})" if condition_confirmed else ""
            log_trading(f"투매폭 {buy_stage} 매수주문: {tracking_info['stock_name']}({stock_code}), "
                       f"수량: {quantity:,}주, 금액: {stage_amount:,}원{condition_info}")
            
        except Exception as e:
            log_error(f"매수 주문 실행 실패: {stock_code}, {str(e)}")
    
    def process_tumepok_signal(self, stock_code, tracking_info):
        """투매폭 신호 처리 (연속상승 추적기 기반)"""
        try:
            current_price = tracking_info.current_price
            drop_rate = tracking_info.drop_rate
            rise_rate = tracking_info.rise_rate
            
            # 투매폭 매트릭스에 따른 대상 하락률 계산
            target_drops = self._get_target_drop_rates(rise_rate)
            min_drop_rate = target_drops['1차']
            max_drop_rate = target_drops['손절']
            
            # 손절 체크
            if drop_rate > max_drop_rate:
                if tracking_info.bought_stages:
                    # 중복 손절 실행 방지 체크
                    position = self.positions.get(stock_code, {})
                    if not position.get('stop_loss_executed', False):
                        log_error(f"⚠️ 손절 신호: {stock_code} - 하락률 {drop_rate:.1f}% > 최대 {max_drop_rate:.1f}%")
                        self.execute_stop_loss(stock_code, "최대 하락폭 초과")
                    else:
                        log_debug(f"손절 이미 실행됨 - 스킵: {stock_code}")
                else:
                    log_info(f"추적 중단: {stock_code} - 적정 하락폭 이탈")
                    # 연속상승 추적기에서 제거하지 말고 상태만 변경
                    if hasattr(tracking_info, 'status'):
                        tracking_info.status = 'STOPPED'
                return
            
            # 적정 하락폭 범위 내에서 매수 검토
            if min_drop_rate <= drop_rate <= max_drop_rate:
                # 매수 단계 결정
                buy_stage = self._get_buy_stage_from_drop_rate(drop_rate, target_drops)
                
                # 이미 매수한 단계인지 확인
                bought_stages = getattr(tracking_info, 'bought_stages', [])
                if buy_stage in bought_stages:
                    log_debug(f"이미 매수한 단계: {stock_code} - {buy_stage}")
                    return
                
                if buy_stage != 'WAIT':
                    # 매수 조건 검증
                    success = self.check_and_execute_buy(stock_code, buy_stage, tracking_info)
                    if success:
                        log_info(f"투매폭 매수 성공: {tracking_info.stock_name}({stock_code}) - "
                                f"{buy_stage} 단계, 하락률: {drop_rate:.1f}%")
                        
                        # 매수 단계 기록
                        if not hasattr(tracking_info, 'bought_stages'):
                            tracking_info.bought_stages = set()
                        tracking_info.bought_stages.add(buy_stage)
                        
                        # 데이터 저장
                        self.save_rise_tracker_data()
                    else:
                        log_debug(f"투매폭 매수 실패: {stock_code} - 지지조건 미충족")
                else:
                    log_debug(f"투매폭 대기: {stock_code} - 하락률 {drop_rate:.1f}% 부족")
            
        except Exception as e:
            log_error(f"투매폭 신호 처리 실패: {stock_code}, {str(e)}")
    
    def _get_buy_stage_from_drop_rate(self, drop_rate, target_drops):
        """하락률에 따른 매수 단계 결정"""
        try:
            if drop_rate >= target_drops['3차']:
                return '3차'
            elif drop_rate >= target_drops['2차']:
                return '2차'
            elif drop_rate >= target_drops['1차']:
                return '1차'
            else:
                return 'WAIT'
        except Exception as e:
            log_error(f"매수 단계 결정 실패: {str(e)}")
            return 'WAIT'
    
    def check_and_execute_buy(self, stock_code, buy_stage, tracking_info):
        """매수 조건 검증 및 실행"""
        try:
            # 가상 tracking_info 생성 (호환성)
            legacy_tracking_info = {
                'stock_code': stock_code,
                'stock_name': getattr(tracking_info, 'stock_name', f'종목{stock_code}'),
                'current_price': tracking_info.current_price,
                'high_price': tracking_info.high_price,
                'rise_rate': tracking_info.rise_rate,
                'drop_rate': tracking_info.drop_rate,
                'rise_days': tracking_info.rise_days,
                'bought_stages': getattr(tracking_info, 'bought_stages', set()),
                'status': getattr(tracking_info, 'status', 'READY')
            }
            
            # 지지 조건 확인
            conditions_met = self.check_support_conditions(stock_code, legacy_tracking_info)
            
            # 단계별 요구 사항 확인
            condition_requirements = self.config.get_condition_requirements() if self.config else {'1차': 1, '2차': 2, '3차': 2}
            required_conditions = condition_requirements.get(buy_stage, 2)
            
            if conditions_met >= required_conditions:
                # 매수 실행
                self.execute_buy_order_direct(stock_code, buy_stage, legacy_tracking_info)
                return True
            else:
                log_debug(f"지지조건 부족: {stock_code}, 충족: {conditions_met}/{required_conditions}")
                return False
                
        except Exception as e:
            log_error(f"매수 조건 검증 실패: {stock_code}, {str(e)}")
            return False
    
    def execute_buy_order_direct(self, stock_code, buy_stage, tracking_info):
        """직접 매수 주문 실행"""
        try:
            current_price = tracking_info['current_price']
            rise_days = tracking_info.get('rise_days', 1)
            
            # 금액 계산
            base_amount = self.config.get_base_buy_amount() if self.config else 200000
            stage_amount = self.config.get_buy_stage_amount(base_amount, buy_stage, rise_days) if self.config else base_amount // 3
            
            # 수량 계산
            quantity = TumepokCalculator.calculate_quantity(stage_amount, current_price)
            
            if quantity <= 0:
                log_error(f"매수 수량 부족: {stock_code}, 금액: {stage_amount}")
                return False
            
            # 주문가격 계산
            order_price = TumepokCalculator.calculate_order_price(current_price, is_buy=True, market_order=True)

            # 매수 주문 전송
            if hasattr(self.main_window, 'queue_manager') and self.main_window.queue_manager:
                order_success = self.main_window.queue_manager.send_order_request(
                    "매수주문",
                    종목코드=stock_code,
                    주문수량=quantity,
                    주문가격=order_price,
                    매매전략="투매폭",
                    매수단계=buy_stage
                )

                # 주문 전송 성공 시 추적 시작 (직접 매수)
                if order_success and hasattr(self.main_window, 'on_order_sent'):
                    import time
                    stock_name = tracking_info.get('stock_name', stock_code)
                    order_id = f"BUY2_{stock_code}_{int(time.time())}"  # 임시 주문 ID
                    self.main_window.on_order_sent({
                        'order_id': order_id,
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'order_type': '매수',
                        'quantity': quantity,
                        'price': order_price
                    })
                    return True
            elif hasattr(self, 'order_tr_req_queue') and self.order_tr_req_queue:
                self.order_tr_req_queue.put({
                    'action_id': '주식매수주문',
                    'purpose': 'TUMEPOK_BUY',
                    '종목코드': stock_code,
                    '주문수량': quantity,
                    '주문가격': order_price,
                    '매매전략': '투매폭',
                    '매수단계': buy_stage
                })
            else:
                log_error(f"주문 시스템을 사용할 수 없음: {stock_code}")
                return False
            
            log_trading(f"투매폭 {buy_stage} 매수주문: {tracking_info.get('stock_name', stock_code)}({stock_code}), "
                       f"수량: {quantity:,}주, 금액: {stage_amount:,}원, 가격: {current_price:,}원")
            
            return True
            
        except Exception as e:
            log_error(f"직접 매수 주문 실행 실패: {stock_code}, {str(e)}")
            return False
    
    def force_buy_ready_stocks(self):
        """매수 준비 상태 종목에 대해 강제 매수 시도"""
        try:
            ready_stocks = self.get_ready_stocks_summary()
            
            if not ready_stocks:
                log_info("매수 준비 상태 종목이 없습니다")
                return 0
            
            buy_count = 0
            for stock_info in ready_stocks:
                stock_code = stock_info['stock_code']
                buy_stage = stock_info['buy_stage']
                bought_stages = stock_info['bought_stages']
                
                # 이미 매수한 단계는 제외
                if buy_stage == 'WAIT' or buy_stage in bought_stages:
                    continue
                
                log_info(f"강제 매수 시도: {stock_info['stock_name']}({stock_code}) - {buy_stage} 단계")
                
                # 수동 매수 실행
                self.execute_manual_buy(stock_code, buy_stage)
                buy_count += 1
                log_info(f"강제 매수 시도 완료: {stock_code} - {buy_stage}")
            
            log_info(f"강제 매수 완료: {buy_count}/{len(ready_stocks)}개 시도")
            return buy_count
            
        except Exception as e:
            log_error(f"강제 매수 실패: {str(e)}")
            return 0
    
    def test_buy_logic(self, stock_code=None):
        """매수 로직 테스트"""
        try:
            log_info("=== 투매폭 매수 로직 테스트 시작 ===")
            
            # 엔진 상태 확인
            stats = self.get_engine_stats()
            log_info(f"엔진 상태: {stats}")
            
            # 매수 준비 종목 확인
            ready_stocks = self.get_ready_stocks_summary()
            log_info(f"매수 준비 종목: {len(ready_stocks)}개")
            
            for stock_info in ready_stocks:
                log_info(f"  - {stock_info['stock_name']}({stock_info['stock_code']}): "
                        f"하락률 {stock_info['drop_rate']:.1f}%, "
                        f"{stock_info['buy_stage']} 단계 가능")
            
            # 특정 종목 테스트
            if stock_code:
                if self.rise_tracker and stock_code in self.rise_tracker.tracking_stocks:
                    tracking_info = self.rise_tracker.get_tracking_info(stock_code)
                    log_info(f"테스트 종목: {tracking_info.stock_name}({stock_code})")
                    log_info(f"  상태: {tracking_info.status}, 하락률: {tracking_info.drop_rate:.1f}%")
                    
                    # 매수 단계 확인
                    target_drops = self._get_target_drop_rates(tracking_info.rise_rate)
                    buy_stage = self._get_buy_stage_from_drop_rate(tracking_info.drop_rate, target_drops)
                    log_info(f"  매수 단계: {buy_stage}, 목표 하락률: {target_drops}")
                    
                    # 지지 조건 확인
                    legacy_tracking_info = {
                        'current_price': tracking_info.current_price,
                        'high_price': tracking_info.high_price,
                        'rise_rate': tracking_info.rise_rate,
                        'drop_rate': tracking_info.drop_rate
                    }
                    conditions_met = self.check_support_conditions(stock_code, legacy_tracking_info)
                    log_info(f"  지지 조건: {conditions_met}/3개 만족")
                    
                    return True
                else:
                    log_error(f"테스트 종목을 찾을 수 없음: {stock_code}")
                    return False
            
            log_info("=== 투매폭 매수 로직 테스트 완료 ===")
            return True
            
        except Exception as e:
            log_error(f"매수 로직 테스트 실패: {str(e)}")
            return False
    
    def execute_stop_loss(self, stock_code, reason="손절"):
        """손절 실행 (긴급 매도)"""
        try:
            if stock_code not in self.positions:
                log_warning(f"손절 대상 포지션 없음: {stock_code}")
                # 추적 중단
                if stock_code in self.tracking_stocks:
                    del self.tracking_stocks[stock_code]
                return

            position = self.positions[stock_code]
            quantity = position.get('total_quantity', 0)

            if quantity <= 0:
                log_warning(f"보유 수량 없음: {stock_code}")
                return

            # 이미 손절 매도 주문이 실행된 상태인지 확인 (중복 실행 방지)
            if position.get('stop_loss_executed', False):
                log_debug(f"이미 손절 매도 주문 실행됨: {stock_code}")
                return

            # 손절 매도 실행 플래그 설정 (중복 실행 방지)
            position['stop_loss_executed'] = True

            # 긴급 매도 주문 (시장가)
            if self.order_tr_req_queue:
                self.order_tr_req_queue.put({
                    'action_id': '매도주문',  # 올바른 action_id
                    'purpose': 'TUMEPOK_STOP_LOSS',
                    '종목코드': stock_code,  # 한글 키 사용
                    '주문수량': quantity,
                    '주문가격': 0,  # 시장가는 0
                    '시장가여부': True,  # 필수 필드 추가
                    '매도사유': f"긴급손절-{reason}",
                    'order_type': '시장가'
                })

                log_error(f"⚠️ 손절 매도 실행: {stock_code} - {reason} (수량: {quantity:,}주)")
                log_trading(f"손절 매도: {position.get('stock_name', '')}({stock_code}), 수량: {quantity:,}주, 사유: {reason}")
            else:
                # 큐가 없는 경우 직접 매도 시도
                log_error(f"⚠️ 손절 매도 큐 없음, 직접 실행 시도: {stock_code}")
                if hasattr(self.main_window, 'queue_manager') and self.main_window.queue_manager:
                    try:
                        self.main_window.queue_manager.send_order_request(
                            "매도주문",
                            종목코드=stock_code,
                            주문수량=quantity,
                            주문가격=0,  # 시장가
                            매도사유=f"긴급손절-{reason}",
                            urgent=True
                        )
                        log_error(f"⚠️ 손절 매도 직접 실행 완료: {stock_code} - {reason} (수량: {quantity:,}주)")
                        log_trading(f"손절 매도: {position.get('stock_name', '')}({stock_code}), 수량: {quantity:,}주, 사유: {reason}")
                    except Exception as e:
                        log_error(f"⚠️ 손절 매도 직접 실행 실패: {stock_code}, {str(e)}")
                else:
                    log_error(f"⚠️ 손절 매도 실행 불가 - 큐와 매니저 모두 없음: {stock_code}")

            # 추적 및 포지션 정리
            if stock_code in self.tracking_stocks:
                self.tracking_stocks[stock_code]['status'] = TRACKING_STATUS.get('STOPPED', 'STOPPED')

            # 포지션을 매도 대기 상태로 변경 (중복 실행 완전 방지)
            position['status'] = 'SELLING'
            
        except Exception as e:
            log_error(f"손절 실행 실패: {stock_code}, {str(e)}")
    
    def execute_sell_order(self, stock_code, sell_reason):
        """매도 주문 실행 (긴급 처리)"""
        try:
            if stock_code not in self.positions:
                log_error(f"포지션 없음: {stock_code}")
                return
            
            position = self.positions[stock_code]
            quantity = position.get('total_quantity', 0)
            stock_name = position.get('stock_name', stock_code)
            
            if quantity <= 0:
                log_error(f"매도 수량 없음: {stock_code}")
                return
            
            # 중복 매도 주문 방지 - 이미 매도 주문 중인지 확인
            if position.get('sell_order_sent', False):
                log_warning(f"⚠️ 중복 매도 주문 차단: {stock_name}({stock_code}) - 이미 매도 주문 진행 중")
                return
            
            # 🔧 매도 주문 상태 표시 (중복 방지)
            position['sell_order_sent'] = True
            position['sell_order_time'] = datetime.now()
            position['sell_reason'] = sell_reason

            log_info(f"🔒 매도 주문 플래그 설정: {stock_name}({stock_code}) - {sell_reason}")

            # 긴급 매도 주문 - 최고 우선순위로 처리
            log_info(f"🚨 긴급 매도 주문 실행: {stock_name}({stock_code}) {quantity}주, 사유: {sell_reason}")
            
            # 매도 주문 전송 (긴급 플래그 추가)
            order_success = self.main_window.queue_manager.send_order_request(
                "매도주문",
                종목코드=stock_code,
                주문수량=quantity,
                주문가격=0,  # 시장가
                매도사유=sell_reason,
                urgent=True  # 긴급 처리 플래그
            )

            # 주문 성공/실패 처리
            if order_success:
                # 주문 전송 성공 시 추적 시작
                if hasattr(self.main_window, 'on_order_sent'):
                    import time
                    order_id = f"SELL_{stock_code}_{int(time.time())}"  # 임시 주문 ID
                    self.main_window.on_order_sent({
                        'order_id': order_id,
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'order_type': '매도',
                        'quantity': quantity,
                        'price': 0  # 시장가
                    })

                # UI 업데이트 - 자동매매 현황에 추가
                if hasattr(self.main_window, 'data_manager'):
                    self.main_window.data_manager.add_auto_trade_info(
                        종목코드=stock_code,
                        종목명=stock_name,
                        매수매도="매도",
                        수량=quantity,
                        가격=0,  # 시장가
                        상태="주문접수",
                        조건식=sell_reason
                    )

                log_trading(f"투매폭 매도주문: {stock_name}({stock_code}), "
                           f"수량: {quantity:,}주, 사유: {sell_reason}")
            else:
                # 🔧 주문 전송 실패 시 플래그 리셋 및 추적 중지
                log_error(f"❌ 매도주문 실패: {stock_name}({stock_code}) - 주문 상태 리셋")
                position['sell_order_sent'] = False
                position.pop('sell_order_time', None)
                position.pop('sell_reason', None)
                log_info(f"🔓 매도 주문 실패 - 플래그 리셋: {stock_name}({stock_code})")

                # 실패한 주문에 대한 모든 추적 중지
                if hasattr(self.main_window, 'stop_order_monitoring'):
                    try:
                        # 해당 종목의 모든 활성 주문 추적 중지
                        self.main_window._remove_orders_by_stock_code(stock_code, "주문전송실패")
                        log_info(f"🛑 주문 실패로 인한 추적 중지: {stock_name}({stock_code})")
                    except Exception as stop_error:
                        log_error(f"주문 실패 후 추적 중지 실패: {stop_error}")

        except Exception as e:
            log_error(f"매도 주문 실행 실패: {stock_code}, {str(e)}")
            # 🔧 예외 발생 시에도 플래그 리셋
            if stock_code in self.positions:
                position = self.positions[stock_code]
                position['sell_order_sent'] = False
                position.pop('sell_order_time', None)
                position.pop('sell_reason', None)
                log_info(f"🔓 매도 주문 예외 발생 - 플래그 리셋: {stock_code}")
    
    def on_order_result(self, data):
        """주문 결과 처리"""
        try:
            stock_code = data.get('종목코드')

            # 다양한 필드명으로 주문 구분 확인
            order_type = data.get('매수매도구분') or data.get('주문구분') or data.get('906')  # 906: 매매구분 필드

            log_debug(f"주문 결과 처리: {stock_code}, 주문구분: {order_type}, 데이터: {data}")

            # 매수/매도 구분 (다양한 형태 지원)
            if order_type in ['1', '매수', '+매수']:  # 매수 체결
                log_info(f"매수 체결 처리: {stock_code}")
                self.on_buy_filled(stock_code, data)
            elif order_type in ['2', '매도', '-매도', '+매도']:  # 매도 체결
                log_info(f"매도 체결 처리: {stock_code}")
                self.on_sell_filled(stock_code, data)
            else:
                log_warning(f"알 수 없는 주문구분: {order_type}, 종목: {stock_code}")

        except Exception as e:
            log_error(f"주문 결과 처리 실패: {str(e)}")
    
    def load_existing_position(self, stock_code, stock_name, quantity, avg_price, current_price):
        """기존 보유 종목을 포지션으로 로드"""
        try:
            if stock_code not in self.positions:
                self.positions[stock_code] = {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'buy_orders': [{
                        'price': avg_price,
                        'quantity': quantity,
                        'time': datetime.now(),
                        'stage': '기존보유'
                    }],
                    'total_quantity': quantity,
                    'weighted_avg_price': avg_price,
                    'current_price': current_price,
                    'profit_rate': TumepokCalculator.calculate_profit_rate(avg_price, current_price) if avg_price > 0 else 0,
                    'trailing_activated': False,
                    'trailing_high': current_price,
                    'created_time': datetime.now()
                }
                log_info(f"기존 보유 종목 포지션 등록: {stock_name}({stock_code}), 수량: {quantity}, 평균가: {avg_price:,}원")
                
                # 보유 종목 실시간 등록
                if hasattr(self.main_window, 'queue_manager'):
                    self.main_window.queue_manager.send_websocket_request(
                        "실시간등록",
                        종목코드=stock_code
                    )
                    log_info(f"보유 종목 실시간 등록 요청: {stock_code}")
        except Exception as e:
            log_error(f"기존 포지션 로드 실패: {stock_code}, {str(e)}")
    
    def on_buy_filled(self, stock_code, data):
        """매수 체결 처리 - 단계별 독립적 트레일링 스탑 지원"""
        try:
            filled_price = data.get('체결가', 0)
            filled_quantity = data.get('체결량', 0)
            buy_stage = data.get('매수단계', '')

            # None 값 처리
            if filled_price is None:
                filled_price = 0
            if filled_quantity is None:
                filled_quantity = 0

            # 숫자 타입 변환
            try:
                filled_price = float(filled_price)
                filled_quantity = int(filled_quantity)
            except (ValueError, TypeError):
                filled_price = 0
                filled_quantity = 0

            log_info(f"매수 체결 처리 시작: {stock_code}, 체결가: {filled_price}, 수량: {filled_quantity}, 단계: {buy_stage}")
            
            # 매수 이력에 추가 (추적->매수 이력 기록)
            self.bought_stocks_history.add(stock_code)
            log_debug(f"매수 이력 추가: {stock_code}")
            
            # 매수 이력 파일 저장
            self.save_bought_history()
            
            # 포지션에 추가
            if stock_code not in self.positions:
                log_info(f"새 포지션 생성: {stock_code}")
                self.positions[stock_code] = {
                    'stock_code': stock_code,
                    'stock_name': data.get('종목명', ''),
                    'buy_orders': [],
                    'total_quantity': 0,
                    'weighted_avg_price': 0.0,
                    'current_price': filled_price,
                    'profit_rate': 0.0,
                    'trailing_activated': False,
                    'trailing_high': filled_price,
                    'created_time': datetime.now()
                }
            
            position = self.positions[stock_code]
            
            # 매수 정보 추가 (단계 정보 포함)
            buy_order_info = {
                'price': filled_price,
                'quantity': filled_quantity,
                'time': datetime.now(),
                'stage': buy_stage if buy_stage else f'{len(position["buy_orders"])+1}차'
            }
            position['buy_orders'].append(buy_order_info)
            
            # 가중평균 매입가 계산
            position['weighted_avg_price'] = TumepokCalculator.calculate_weighted_average_price(
                position['buy_orders']
            )
            position['total_quantity'] += filled_quantity
            
            # 추적에서 포지션으로 이동 (3단계 완료 시)
            if stock_code in self.tracking_stocks:
                tracking_info = self.tracking_stocks[stock_code]
                if len(tracking_info['bought_stages']) >= 3:
                    tracking_info['status'] = TRACKING_STATUS['COMPLETED']
                    # 추적에서 제거하지 않고 완료 상태로 유지

            # stage_key 생성
            stage_key = buy_stage if buy_stage else f"{len(position['buy_orders'])}차"

            log_trading(f"투매폭 {stage_key} 매수 체결: {position['stock_name']}({stock_code}), "
                       f"체결가: {filled_price:,}원, 수량: {filled_quantity:,}주")
            
        except Exception as e:
            log_error(f"매수 체결 처리 실패: {stock_code}, {str(e)}")
    
    def on_sell_filled(self, stock_code, data):
        """매도 체결 처리 - 포지션 및 추적에서 완전 제거"""
        try:
            position_name = ""
            sell_price = 0
            sell_quantity = 0

            log_info(f"📤 매도 체결 처리 시작: {stock_code}")

            # 체결 정보 추출 (다양한 필드명 지원)
            sell_price = (float(data.get('단위체결가', 0)) or
                         float(data.get('체결가', 0)) or
                         float(data.get('910', 0))) if data.get('단위체결가') or data.get('체결가') or data.get('910') else 0

            sell_quantity = (int(data.get('단위체결량', 0)) or
                           int(data.get('체결량', 0)) or
                           int(data.get('911', 0))) if data.get('단위체결량') or data.get('체결량') or data.get('911') else 0

            log_info(f"매도 체결 정보: {stock_code}, 가격: {sell_price:,}원, 수량: {sell_quantity}주")
                
            if stock_code in self.positions:
                position = self.positions[stock_code]
                position_name = position['stock_name']

                # 🔧 매도 체결 시 sell_order_sent 플래그 즉시 리셋
                if position.get('sell_order_sent', False):
                    position['sell_order_sent'] = False
                    position.pop('sell_order_time', None)
                    position.pop('sell_reason', None)
                    log_info(f"✅ 매도 체결 완료 - sell_order_sent 플래그 리셋: {position_name}({stock_code})")

                # 재매수 제한 기능이 활성화된 경우 매도 내역 저장
                rebuy_config = self.config.get_rebuy_restriction_config() if self.config else {}
                if rebuy_config.get('enabled', True) and hasattr(self, 'sold_stocks_manager'):
                    try:
                        sell_amount = sell_price * sell_quantity
                        sell_reason = position.get('sell_reason', "AUTO_SELL")  # 실제 매도 사유 사용

                        self.sold_stocks_manager.add_sold_stock(
                            stock_code=stock_code,
                            stock_name=position_name,
                            sell_reason=sell_reason,
                            sell_price=sell_price,
                            quantity=sell_quantity,
                            sell_amount=sell_amount
                        )
                        log_info(f"매도 종목 재매수 제한 등록: {position_name}({stock_code})")

                    except Exception as e:
                        log_error(f"매도 종목 재매수 제한 등록 실패: {stock_code}, {str(e)}")

                # 매도 완료 처리
                del self.positions[stock_code]
                log_trading(f"투매폭 매도 체결 완료: {position_name}({stock_code})")
                log_info(f"🗑️ 포지션 제거 완료: {position_name}({stock_code})")
            else:
                log_warning(f"⚠️ 매도 체결되었지만 포지션이 없음: {stock_code}")

            # 추적 완전 정리 (개선사항 적용)
            cleanup_success = self.cleanup_tracking_after_sell(stock_code, position_name)
            if cleanup_success:
                log_info(f"✅ 매도 후 추적 정리 완료: {position_name}({stock_code})")
            else:
                log_warning(f"⚠️ 매도 후 추적 정리 실패: {position_name}({stock_code})")
            
            # DataManager에서 매도 상태 표시
            if hasattr(self.main_window, 'data_manager') and self.main_window.data_manager:
                try:
                    self.main_window.data_manager.mark_tumepok_stock_as_sold(stock_code)
                    log_info(f"DataManager에서 매도 상태 표시: {position_name}({stock_code})")
                except Exception as e:
                    log_error(f"DataManager 매도 표시 실패: {stock_code}, {e}")
            
            # 추적현황 테이블 즉시 업데이트 (매도 완료 상태 표시)
            if hasattr(self.main_window, 'tumepok_panel') and self.main_window.tumepok_panel:
                try:
                    tracking_df = self.get_tracking_dataframe()
                    self.main_window.tumepok_panel.update_tracking_data(tracking_df)
                    log_info(f"추적현황 테이블 업데이트 완료: {position_name}({stock_code}) 매도 완료 상태 표시")
                except Exception as update_error:
                    log_error(f"추적현황 테이블 업데이트 실패: {update_error}")
            
            # 계좌 정보 다시 조회하여 실제 보유 현황 확인 (매도 완료 반영)
            if hasattr(self.main_window, 'refresh_account_info'):
                try:
                    # 2초 후 계좌 정보 새로고침 (매도 체결 완료 대기)
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(2000, self.main_window.refresh_account_info)
                    log_info(f"매도 완료 후 계좌 정보 새로고침 예약: {position_name}({stock_code})")

                    # 5초 후 포지션 정리 재실행 (계좌 동기화 완료 후)
                    QTimer.singleShot(5000, self.cleanup_all_sold_positions)
                    log_info(f"매도 완료 후 포지션 정리 예약: {position_name}({stock_code})")
                except Exception as refresh_error:
                    log_error(f"계좌 정보 새로고침 실패: {refresh_error}")

            # 계좌 테이블도 즉시 업데이트 (매도 완료 포지션 제거 반영)
            if hasattr(self.main_window, 'update_account_table'):
                try:
                    self.main_window.update_account_table()
                    log_debug(f"계좌 테이블 업데이트 완료: 매도 완료 포지션 제거 반영")
                except Exception as update_error:
                    log_error(f"계좌 테이블 업데이트 실패: {update_error}")
            
        except Exception as e:
            log_error(f"매도 체결 처리 실패: {stock_code}, {str(e)}")
    
    def update_position(self, stock_code, current_price):
        """포지션 업데이트"""
        try:
            if stock_code not in self.positions:
                return
            
            position = self.positions[stock_code]
            
            # 🔧 중복 매도 주문 방지 - 조건 확인은 계속 수행
            if position.get('sell_order_sent', False):
                # 매도 주문 후 30초 경과 시 플래그 리셋 (주문 실패/체결 누락 대비)
                sell_order_time = position.get('sell_order_time')
                if sell_order_time and (datetime.now() - sell_order_time).total_seconds() > 30:  # 30초로 단축
                    log_warning(f"매도 주문 30초 경과 - 플래그 리셋: {stock_code}")
                    position['sell_order_sent'] = False
                    position.pop('sell_order_time', None)
                    position.pop('sell_reason', None)
                else:
                    log_debug(f"매도 주문 진행 중인 포지션: {stock_code} - 중복 주문 방지만 활성")
                    # 🔧 조건 확인은 스킵하지 않고 계속 진행 (중복 주문만 방지)
            
            position['current_price'] = current_price
            
            # 수익률 계산
            buy_price = position['weighted_avg_price']
            profit_rate = TumepokCalculator.calculate_profit_rate(buy_price, current_price)
            position['profit_rate'] = profit_rate
            
            # 매도 조건 확인
            sell_signal = self.check_sell_conditions(stock_code, position)

            # 🔧 매도 신호가 있고 중복 주문이 아닌 경우에만 실행
            if sell_signal and not position.get('sell_order_sent', False):
                self.execute_sell_order(stock_code, sell_signal)
            elif sell_signal and position.get('sell_order_sent', False):
                log_debug(f"매도 신호 발생했지만 이미 주문 진행 중: {stock_code} - {sell_signal}")
                
        except Exception as e:
            log_error(f"포지션 업데이트 실패: {stock_code}, {str(e)}")
    
    def check_sell_conditions(self, stock_code, position):
        """매도 조건 확인 - 전체 포지션 트레일링 스탑"""
        try:
            current_price = position['current_price']
            weighted_avg_price = position['weighted_avg_price']
            overall_profit_rate = position['profit_rate']
            
            log_debug(f"매도 조건 확인: {stock_code}, 수익률: {overall_profit_rate:.2f}%")
            
            # 투매폭 손절 조건 - 매트릭스 기준 최대 하락폭 초과 시에만 손절
            buy_orders = position.get('buy_orders', [])
            current_stage = len(buy_orders)

            # 투매폭 매트릭스에서 손절선 확인
            tracking_info = self.tracking_stocks.get(stock_code)
            if tracking_info:
                rise_rate = tracking_info.get('cumulative_rise_rate', 0)

                # 투매폭 매트릭스에서 직접 계산
                max_drop_rate = 25.0  # 기본값
                if self.config:
                    drop_range = self.config.calculate_target_drop_range(rise_rate)
                    max_drop_rate = drop_range.get('max_drop', 25.0)

                # 현재 하락률 계산 (상승 시작가 기준)
                rise_start_price = tracking_info.get('rise_start_price', position.get('first_buy_price', current_price))
                if rise_start_price > 0:
                    current_drop_rate = ((rise_start_price - current_price) / rise_start_price) * 100

                    # 투매폭 매트릭스 기준 최대 하락폭 초과 시에만 손절
                    if current_drop_rate > max_drop_rate:
                        log_info(f"📉 투매폭 손절 매도 신호: {stock_code}, {current_stage}차 매수 후, 하락률: {current_drop_rate:.1f}% > 최대 {max_drop_rate:.1f}%")
                        return SELL_REASONS['STOP_LOSS']
                    else:
                        log_debug(f"투매폭 진행 중: {stock_code}, {current_stage}차 매수 후, 하락률: {current_drop_rate:.1f}% (최대 {max_drop_rate:.1f}%까지 대기)")
            else:
                # 추적 정보가 없는 경우 기본 손절률 적용 (3차 완료 후)
                if current_stage >= 3 and overall_profit_rate <= -2.0:
                    log_info(f"📉 기본 손절 매도 신호: {stock_code}, 3차 매수 완료 후, 수익률: {overall_profit_rate:.2f}%")
                    return SELL_REASONS['STOP_LOSS']
            
            # 트레일링 스탑 조건 (2% 상승 시 발동)
            trailing_trigger = self.config.get_trailing_trigger_rate()  # 2.0
            trailing_sell_rate = self.config.get_trailing_sell_rate()   # -1.0
            
            # 트레일링 스탑 발동 체크 (전체 포지션 기준)
            log_debug(f"트레일링 체크: 활성화={position.get('trailing_activated', False)}, 수익률={overall_profit_rate:.2f}%, 발동기준={trailing_trigger}%")
            
            if not position.get('trailing_activated', False) and overall_profit_rate >= trailing_trigger:
                position['trailing_activated'] = True
                position['trailing_high'] = current_price
                
                # 현재 몇 차 매수까지 진행되었는지 확인
                current_stage = len(buy_orders)
                stage_info = f"{current_stage}차 매수 후"
                
                log_info(f"🎯 트레일링 스탑 발동: {stock_code}, {stage_info} 수익률: {overall_profit_rate:.2f}%")
                
                # UI 업데이트
                if hasattr(self, 'main_window') and self.main_window:
                    try:
                        self.main_window.update_account_table()
                    except:
                        pass
            
            # 트레일링 매도 체크 (전량 매도)
            if position.get('trailing_activated', False):
                trailing_high = position.get('trailing_high', current_price)
                
                # 고점 업데이트
                if current_price > trailing_high:
                    position['trailing_high'] = current_price
                    trailing_high = current_price
                
                # 트레일링 매도 조건 확인 (고점 대비 -1% 하락)
                high_drop_rate = ((trailing_high - current_price) / trailing_high) * 100  # 하락률을 양수로 계산
                trailing_sell_threshold = abs(trailing_sell_rate)  # -1% -> 1%
                
                log_debug(f"트레일링 확인: {stock_code}, 고점={trailing_high:,}원, 현재가={current_price:,}원, 하락률={high_drop_rate:.2f}%, 임계값={trailing_sell_threshold:.2f}%")
                
                if high_drop_rate >= trailing_sell_threshold:  # 1% 이상 하락 시 매도
                    current_stage = len(buy_orders)
                    log_info(f"🚨 트레일링 매도 신호 발동! {stock_code}, {current_stage}차 매수 후, 고점({trailing_high:,}원) 대비 {high_drop_rate:.2f}% 하락")
                    return SELL_REASONS['TRAILING_SELL']
            
            return None
            
        except Exception as e:
            log_error(f"매도 조건 확인 실패: {stock_code}, {str(e)}")
            return None
    
    def is_valid_tracking_stock(self, stock_info):
        """추적 가능한 종목인지 확인"""
        try:
            current_price = stock_info.get('현재가', 0)

            # 가격 범위 확인 (config에서 가져오기)
            if self.config:
                min_price = self.config.get_min_price()
                max_price = self.config.get_max_price()

                if current_price < min_price or current_price > max_price:
                    log_debug(f"가격 범위 벗어남: {current_price:,}원 (범위: {min_price:,}~{max_price:,}원)")
                    return False
            else:
                # config 없을 때 기본값
                if current_price < 1000 or current_price > 100000:
                    return False

            return True

        except Exception as e:
            log_error(f"종목 유효성 확인 실패: {str(e)}")
            return False
    
    # 외부 인터페이스 메서드들
    
    def add_manual_tracking(self, stock_code):
        """수동 추적 추가"""
        try:
            if stock_code in self.tracking_stocks:
                log_debug(f"이미 추적 중: {stock_code}")
                return
            
            # 종목 기본정보 요청
            self.main_window.queue_manager.send_tr_request(
                "주식기본정보",
                종목코드=stock_code,
                purpose="TUMEPOK_MANUAL_TRACKING"
            )
            
        except Exception as e:
            log_error(f"수동 추적 추가 실패: {stock_code}, {str(e)}")
    
    def remove_tracking(self, stock_code):
        """추적 제거 (수동 정지)"""
        try:
            removed = False
            stock_name = stock_code  # 기본값

            # tracking_stocks에서 제거
            if stock_code in self.tracking_stocks:
                stock_info = self.tracking_stocks.get(stock_code, {})
                stock_name = stock_info.get('stock_name', stock_info.get('name', stock_code))
                del self.tracking_stocks[stock_code]
                removed = True
                log_info(f"🛑 투매폭 추적 수동 정지: {stock_name}({stock_code})")

            # RiseTracker에서도 제거
            if hasattr(self, 'rise_tracker') and self.rise_tracker:
                try:
                    # RiseTracker의 tracking_stocks 확인
                    if stock_code in self.rise_tracker.tracking_stocks:
                        tracking_info = self.rise_tracker.tracking_stocks.get(stock_code)
                        if tracking_info:
                            stock_name = getattr(tracking_info, 'stock_name', stock_name)

                        result = self.rise_tracker.remove_stock(stock_code)
                        if result:
                            removed = True
                            log_info(f"🛑 RiseTracker에서 수동 제거: {stock_name}({stock_code})")
                        else:
                            log_debug(f"RiseTracker에 없는 종목: {stock_code}")
                    else:
                        log_debug(f"RiseTracker에 추적되지 않는 종목: {stock_code}")

                except Exception as e:
                    log_error(f"RiseTracker 제거 중 오류: {stock_code}, {e}")

            # DataManager에서도 제거
            if hasattr(self.main_window, 'data_manager') and self.main_window.data_manager:
                try:
                    remove_success = self.main_window.data_manager.remove_realtime_tracking_stock(
                        stock_code, reason="MANUAL_STOP"
                    )
                    if remove_success:
                        removed = True
                        log_info(f"🛑 DataManager에서 수동 제거: {stock_name}({stock_code})")
                except Exception as e:
                    log_error(f"DataManager 제거 실패: {stock_code}, {e}")

            # 수동 정지 아카이브에 추가
            if removed:
                self.archive_manual_stopped_stock(stock_code, stock_name)

                # sold_stocks_manager에 재매수 제한 기록 추가
                if self.sold_stocks_manager:
                    try:
                        # 현재가 정보 가져오기
                        current_price = 0
                        if hasattr(self, 'rise_tracker') and self.rise_tracker:
                            tracking_info = self.rise_tracker.tracking_stocks.get(stock_code)
                            if tracking_info:
                                current_price = getattr(tracking_info, 'current_price', 0)

                        self.sold_stocks_manager.add_sold_stock(
                            stock_code=stock_code,
                            stock_name=stock_name,
                            sell_reason="MANUAL_STOP",  # 수동 중단
                            sell_price=current_price,
                            quantity=0,  # 추적만 중단이므로 수량은 0
                            sell_amount=0
                        )
                        log_info(f"✅ 재매수 제한 등록: {stock_name}({stock_code}) - 5일간 제한")
                    except Exception as e:
                        log_error(f"재매수 제한 등록 실패: {stock_code}, {str(e)}")

            # 데이터 파일 저장 (추적 제거 반영)
            if removed:
                try:
                    if hasattr(self, 'save_rise_tracker_data'):
                        self.save_rise_tracker_data()
                        log_debug(f"추적 데이터 파일 저장 완료")
                except Exception as save_error:
                    log_error(f"데이터 파일 저장 실패: {save_error}")

            # 추적현황 테이블 즉시 업데이트
            if hasattr(self.main_window, 'tumepok_panel') and self.main_window.tumepok_panel:
                try:
                    tracking_df = self.get_tracking_dataframe()
                    self.main_window.tumepok_panel.update_tracking_data(tracking_df)
                    log_info(f"추적현황 테이블 업데이트 완료: {stock_name}({stock_code}) 제거")
                except Exception as update_error:
                    log_error(f"추적현황 테이블 업데이트 실패: {update_error}")

            if not removed:
                log_warning(f"추적 제거할 종목을 찾을 수 없음: {stock_code}")
                # UI 테이블에서만 존재하는 경우 강제 업데이트
                if hasattr(self.main_window, 'tumepok_panel') and self.main_window.tumepok_panel:
                    try:
                        # 빈 DataFrame이라도 전송하여 UI 동기화
                        tracking_df = self.get_tracking_dataframe()
                        self.main_window.tumepok_panel.update_tracking_data(tracking_df)
                        log_info(f"UI 테이블 강제 동기화: {stock_code}")
                    except:
                        pass

            return removed

        except Exception as e:
            log_error(f"추적 제거 실패: {stock_code}, {str(e)}")
            return False
    
    def execute_manual_buy(self, stock_code, stage):
        """수동 매수 실행"""
        try:
            if stock_code in self.tracking_stocks:
                self.execute_buy_order(stock_code, stage)
            else:
                log_error(f"추적 중이 아닌 종목: {stock_code}")
                
        except Exception as e:
            log_error(f"수동 매수 실행 실패: {stock_code}, {str(e)}")
    
    def get_tracking_stocks(self):
        """추적 종목 목록 반환"""
        return self.tracking_stocks.copy()
    
    def get_positions(self):
        """포지션 목록 반환"""
        return self.positions.copy()
    
    def get_tracking_dataframe(self):
        """추적 현황 DataFrame 반환 - RiseTracker 사용 (매도된 종목도 포함하여 상태 표시)"""
        try:
            # RiseTracker에서 전체 추적 데이터 가져오기
            full_tracking_df = self.rise_tracker.get_tracking_dataframe()
            
            if full_tracking_df.empty:
                return full_tracking_df
            
            # DataManager에서 매도된 종목 목록 확인하여 상태 업데이트
            if hasattr(self.main_window, 'data_manager') and self.main_window.data_manager:
                sold_stocks = self.main_window.data_manager.today_sold_stocks
                
                # 매도된 종목이 있으면 상태를 '매도완료'로 표시
                if sold_stocks and '종목코드' in full_tracking_df.columns:
                    sold_mask = full_tracking_df['종목코드'].isin(sold_stocks)
                    if '상태' not in full_tracking_df.columns:
                        full_tracking_df['상태'] = '추적중'
                    
                    # 매도된 종목의 상태를 '매도완료'로 변경
                    full_tracking_df.loc[sold_mask, '상태'] = '매도완료'
                    
                    from utils.enhanced_logging import log_debug, log_info
                    sold_count = sold_mask.sum()
                    if sold_count > 0:
                        log_info(f"📊 추적현황에 매도 완료된 종목 {sold_count}개 상태 표시")
            
            return full_tracking_df
            
        except Exception as e:
            from utils.enhanced_logging import log_error
            log_error(f"추적 DataFrame 필터링 실패: {str(e)}")
            return self.rise_tracker.get_tracking_dataframe()
    
    def get_engine_stats(self):
        """엔진 통계 반환"""
        try:
            rise_tracker_count = len(self.rise_tracker.tracking_stocks) if self.rise_tracker else 0
            legacy_tracking_count = len(self.tracking_stocks)
            
            return {
                'is_active': self.is_active,
                'rise_tracker_count': rise_tracker_count,
                'legacy_tracking_count': legacy_tracking_count,
                'total_tracking_count': rise_tracker_count + legacy_tracking_count,
                'position_count': len(self.positions),
                'last_scan_time': self.last_scan_time,
                'stats': self.stats.copy(),
                'ready_stocks': self.get_ready_stocks_summary()
            }
        except Exception as e:
            log_error(f"엔진 통계 생성 실패: {str(e)}")
            return {
                'is_active': self.is_active,
                'tracking_count': len(self.tracking_stocks),
                'position_count': len(self.positions),
                'error': str(e)
            }
    
    def cleanup_tracking_after_sell(self, stock_code, stock_name):
        """매도 후 추적 상태 완전 정리"""
        try:
            cleanup_results = []

            # 1. tracking_stocks에서 완전 제거
            if stock_code in self.tracking_stocks:
                del self.tracking_stocks[stock_code]
                cleanup_results.append("tracking_stocks 제거")
                log_info(f"🗑️ tracking_stocks에서 제거: {stock_name}({stock_code})")

            # 2. RiseTracker에서 완전 제거
            if hasattr(self, 'rise_tracker') and self.rise_tracker:
                try:
                    if stock_code in self.rise_tracker.tracking_stocks:
                        result = self.rise_tracker.remove_stock(stock_code)
                        if result:
                            cleanup_results.append("RiseTracker 제거")
                            log_info(f"🗑️ RiseTracker에서 제거: {stock_name}({stock_code})")
                        else:
                            log_warning(f"⚠️ RiseTracker 제거 실패: {stock_code}")
                except Exception as e:
                    log_error(f"RiseTracker 제거 중 오류: {stock_code}, {e}")

            # 3. DataManager에서 추적 데이터 제거
            if hasattr(self.main_window, 'data_manager') and self.main_window.data_manager:
                try:
                    remove_success = self.main_window.data_manager.remove_realtime_tracking_stock(
                        stock_code, reason="SELL_COMPLETED"
                    )
                    if remove_success:
                        cleanup_results.append("DataManager 제거")
                        log_info(f"🗑️ DataManager에서 제거: {stock_name}({stock_code})")
                except Exception as e:
                    log_error(f"DataManager 제거 실패: {stock_code}, {e}")

            # 4. 매도 완료 종목 아카이브에 추가
            self.archive_sold_stock(stock_code, stock_name)
            cleanup_results.append("매도 아카이브 추가")

            # 5. UI 테이블 즉시 업데이트
            self.update_tracking_ui_after_cleanup()
            cleanup_results.append("UI 업데이트")

            # 6. 데이터 파일 저장
            try:
                if hasattr(self, 'save_rise_tracker_data'):
                    self.save_rise_tracker_data()
                cleanup_results.append("데이터 저장")
            except Exception as save_error:
                log_error(f"데이터 저장 실패: {save_error}")

            log_info(f"✅ 추적 정리 완료: {stock_name}({stock_code}) - {', '.join(cleanup_results)}")
            return True

        except Exception as e:
            log_error(f"추적 정리 실패: {stock_code}, {str(e)}")
            return False

    def archive_sold_stock(self, stock_code, stock_name):
        """매도 완료 종목 아카이브"""
        try:
            if not hasattr(self, 'sold_stock_archive'):
                self.sold_stock_archive = {}

            import datetime
            self.sold_stock_archive[stock_code] = {
                'stock_name': stock_name,
                'action_type': 'SELL_COMPLETED',
                'action_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'action_time': datetime.datetime.now().strftime('%H:%M:%S'),
                'archive_until': (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                'reason': '매도 완료'
            }

            log_debug(f"📦 매도 종목 아카이브: {stock_name}({stock_code}) - 30일 후 자동 삭제")

        except Exception as e:
            log_error(f"매도 종목 아카이브 실패: {stock_code}, {str(e)}")

    def archive_manual_stopped_stock(self, stock_code, stock_name):
        """수동 정지 종목 아카이브"""
        try:
            if not hasattr(self, 'manual_stop_archive'):
                self.manual_stop_archive = {}

            import datetime
            self.manual_stop_archive[stock_code] = {
                'stock_name': stock_name,
                'action_type': 'MANUAL_STOP',
                'action_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'action_time': datetime.datetime.now().strftime('%H:%M:%S'),
                'archive_until': (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
                'reason': '수동 정지'
            }

            log_debug(f"📦 수동 정지 종목 아카이브: {stock_name}({stock_code}) - 7일 후 자동 삭제")

        except Exception as e:
            log_error(f"수동 정지 종목 아카이브 실패: {stock_code}, {str(e)}")

    def update_tracking_ui_after_cleanup(self):
        """추적 정리 후 UI 업데이트"""
        try:
            # 추적현황 테이블 업데이트
            if hasattr(self.main_window, 'tumepok_panel') and self.main_window.tumepok_panel:
                tracking_df = self.get_tracking_dataframe()
                self.main_window.tumepok_panel.update_tracking_data(tracking_df)
                log_debug("🔄 추적현황 테이블 업데이트 완료")

            # 계좌 테이블 업데이트
            if hasattr(self.main_window, 'update_account_table'):
                self.main_window.update_account_table()
                log_debug("🔄 계좌 테이블 업데이트 완료")

        except Exception as e:
            log_error(f"UI 업데이트 실패: {str(e)}")

    def cleanup_expired_archives(self):
        """만료된 아카이브 정리"""
        try:
            import datetime
            today = datetime.datetime.now().strftime('%Y-%m-%d')

            # 매도 완료 아카이브 정리 (30일 후)
            if hasattr(self, 'sold_stock_archive'):
                expired_sold = []
                for stock_code, archive_info in self.sold_stock_archive.items():
                    if today > archive_info.get('archive_until', ''):
                        expired_sold.append(stock_code)

                for stock_code in expired_sold:
                    stock_name = self.sold_stock_archive[stock_code]['stock_name']
                    del self.sold_stock_archive[stock_code]
                    log_debug(f"🗑️ 만료된 매도 아카이브 삭제: {stock_name}({stock_code})")

                if expired_sold:
                    log_info(f"📦 매도 아카이브 정리 완료: {len(expired_sold)}개 삭제")

            # 수동 정지 아카이브 정리 (7일 후)
            if hasattr(self, 'manual_stop_archive'):
                expired_manual = []
                for stock_code, archive_info in self.manual_stop_archive.items():
                    if today > archive_info.get('archive_until', ''):
                        expired_manual.append(stock_code)

                for stock_code in expired_manual:
                    stock_name = self.manual_stop_archive[stock_code]['stock_name']
                    del self.manual_stop_archive[stock_code]
                    log_debug(f"🗑️ 만료된 수동정지 아카이브 삭제: {stock_name}({stock_code})")

                if expired_manual:
                    log_info(f"📦 수동정지 아카이브 정리 완료: {len(expired_manual)}개 삭제")

        except Exception as e:
            log_error(f"아카이브 정리 실패: {str(e)}")

    def get_archive_summary(self):
        """아카이브 요약 정보"""
        try:
            summary = {
                'sold_count': len(getattr(self, 'sold_stock_archive', {})),
                'manual_stop_count': len(getattr(self, 'manual_stop_archive', {})),
                'total_count': 0
            }
            summary['total_count'] = summary['sold_count'] + summary['manual_stop_count']
            return summary

        except Exception as e:
            log_error(f"아카이브 요약 실패: {str(e)}")
            return {'sold_count': 0, 'manual_stop_count': 0, 'total_count': 0}

    def get_ready_stocks_summary(self):
        """매수 준비 종목 요약"""
        try:
            ready_stocks = []

            # 연속상승 추적기에서 READY 상태 종목 찾기
            if self.rise_tracker:
                for stock_code, tracking_info in self.rise_tracker.tracking_stocks.items():
                    # 매수 대상 조건: READY 또는 하락률이 최소 기준 이상
                    target_drops = self._get_target_drop_rates(tracking_info.rise_rate)
                    is_ready_to_buy = (
                        hasattr(tracking_info, 'status') and tracking_info.status == 'READY'
                    ) or (
                        tracking_info.drop_rate >= target_drops['1차']
                    )

                    if is_ready_to_buy:
                        # 매수 단계 결정
                        buy_stage = self._get_buy_stage_from_drop_rate(tracking_info.drop_rate, target_drops)

                        ready_stocks.append({
                            'stock_code': stock_code,
                            'stock_name': tracking_info.stock_name or f'종목{stock_code}',
                            'current_price': tracking_info.current_price,
                            'drop_rate': tracking_info.drop_rate,
                            'rise_rate': tracking_info.rise_rate,
                            'buy_stage': buy_stage,
                            'bought_stages': getattr(tracking_info, 'bought_stages', []),
                            'status': getattr(tracking_info, 'status', 'UNKNOWN'),
                            'target_drops': target_drops
                        })
            
            return ready_stocks
            
        except Exception as e:
            log_error(f"매수 준비 종목 요약 실패: {str(e)}")
            return []    

    def add_to_tracking(self, stock_code, current_price, change_rate=None):
        """추적 목록에 추가 (재매수 제한 확인 및 가격 필터 포함)"""
        try:
            if stock_code in self.tracking_stocks:
                return False

            # 가격 범위 확인 추가
            if self.config:
                min_price = self.config.get_min_price()
                max_price = self.config.get_max_price()

                if current_price < min_price or current_price > max_price:
                    log_info(f"❌ 가격 범위 벗어난 종목 스킵: {stock_code} - {current_price:,}원 (범위: {min_price:,}~{max_price:,}원)")
                    return False

            # 재매수 제한 확인 추가
            if self.sold_stocks_manager:
                rebuy_config = self.config.get_rebuy_restriction_config() if self.config else {}
                restriction_days = rebuy_config.get('restriction_days', 5)

                if self.sold_stocks_manager.is_rebuy_restricted(stock_code, restriction_days):
                    log_info(f"❌ 재매수 제한 종목 자동추가 스킵: {stock_code} - {restriction_days}일 제한 중")
                    return False

            max_tracking = self.config.get_max_tracking_stocks()
            if len(self.tracking_stocks) >= max_tracking:
                return False
            
            # 추적 정보 생성 (간소화)
            self.tracking_stocks[stock_code] = {
                'stock_code': stock_code,
                'stock_name': f'종목{stock_code}',
                'start_price': current_price,
                'current_price': current_price,
                'high_price': current_price,
                'daily_change_rate': change_rate if change_rate is not None else 0.0,  # 당일 등락률
                'rise_rate': 0.0,  # 누적 상승률 (시작시에는 0)
                'drop_rate': 0.0,
                'rise_days': 1,
                'status': 'TRACKING',
                'bought_stages': set(),
                'start_time': datetime.now()
            }
            
            log_debug(f"추적 목록 추가: {stock_code} @ {current_price:,}원")
            return True
            
        except Exception as e:
            log_error(f"추적 목록 추가 실패 {stock_code}: {str(e)}")
            return False
    
    def update_tracking_stock_simple(self, stock_code, current_price):
        """추적 중인 종목 업데이트 (성능 테스트용 간소화 버전)"""
        try:
            if stock_code not in self.tracking_stocks:
                return
            
            tracking_info = self.tracking_stocks[stock_code]
            tracking_info['current_price'] = current_price
            
            # 간단한 상승률 계산
            start_price = tracking_info['start_price']
            if start_price > 0:
                rise_rate = ((current_price - start_price) / start_price) * 100
                tracking_info['rise_rate'] = rise_rate
            
            log_debug(f"추적 종목 업데이트: {stock_code} @ {current_price:,}원")
            
        except Exception as e:
            log_error(f"추적 종목 업데이트 실패 {stock_code}: {str(e)}")
    
    def update_position_stock_simple(self, stock_code, current_price):
        """포지션 종목 업데이트 (성능 테스트용 간소화 버전)"""
        try:
            if stock_code not in self.positions:
                return
            
            self.positions[stock_code]['current_price'] = current_price
            log_debug(f"포지션 종목 업데이트: {stock_code} @ {current_price:,}원")
            
        except Exception as e:
            log_error(f"포지션 종목 업데이트 실패 {stock_code}: {str(e)}")
    
    def on_rising_stocks_received(self, rising_stocks):
        """급등주 리스트 수신 처리"""
        try:
            log_info(f"급등주 수신: {len(rising_stocks)}개 종목")
            
            if not rising_stocks:
                log_debug("수신된 급등주가 없습니다")
                return
            
            # 각 급등주에 대해 처리
            for stock_info in rising_stocks:
                stock_code = stock_info.get('종목코드')
                stock_name = stock_info.get('종목명', '')
                current_price = stock_info.get('현재가', 0)
                change_rate = stock_info.get('등락률', 0)
                volume = stock_info.get('거래량', 0)
                
                # 종목코드 타입 정규화 (numpy float64 -> string)
                if stock_code is None:
                    continue
                
                # numpy 타입이면 문자열로 변환하고 소수점 제거
                if hasattr(stock_code, 'dtype'):  # numpy 타입 체크
                    stock_code = f"{int(stock_code):06d}"  # 6자리 종목코드로 변환
                else:
                    stock_code = str(stock_code).split('.')[0]  # 소수점 제거
                
                if not stock_code or stock_code == 'nan':
                    continue
                
                log_info(f"급등주 발견: {stock_name}({stock_code}) - 등락률: {change_rate:.2f}%, 현재가: {current_price:,}원")
                
                # 이미 추적 중인지 확인
                if stock_code in self.tracking_stocks:
                    log_debug(f"이미 추적 중인 종목: {stock_name}({stock_code})")
                    continue
                
                # 최대 추적 종목 수 확인
                max_tracking = self.config.get_max_tracking_stocks() if self.config else 10
                if len(self.tracking_stocks) >= max_tracking:
                    log_debug(f"최대 추적 종목 수 초과: {len(self.tracking_stocks)}/{max_tracking}")
                    break
                
                # 급등주를 추적 목록에 추가
                if self._add_rising_stock_to_tracking(stock_code, stock_info):
                    log_info(f"급등주 추적 시작: {stock_name}({stock_code}) - 등락률: {change_rate:.2f}%")
                
        except Exception as e:
            log_error(f"급등주 리스트 처리 실패: {str(e)}")
    
    def _add_rising_stock_to_tracking(self, stock_code, stock_info):
        """급등주를 추적 목록에 추가"""
        try:
            # 기본 정보 추출
            current_price = stock_info.get('현재가', 0)
            change_rate = stock_info.get('등락률', 0)  # 전일 대비 등락률
            stock_name = stock_info.get('종목명', '')

            # 가격 범위 확인 추가
            if self.config:
                min_price = self.config.get_min_price()
                max_price = self.config.get_max_price()

                if current_price < min_price or current_price > max_price:
                    log_info(f"❌ 가격 범위 벗어난 종목 스킵: {stock_name}({stock_code}) - {current_price:,}원 (범위: {min_price:,}~{max_price:,}원)")
                    return False

            # 재매수 제한 확인
            if self.sold_stocks_manager:
                rebuy_config = self.config.get_rebuy_restriction_config() if self.config else {}
                restriction_days = rebuy_config.get('restriction_days', 5)

                if self.sold_stocks_manager.is_rebuy_restricted(stock_code, restriction_days):
                    log_info(f"❌ 재매수 제한 종목 스킵: {stock_name}({stock_code}) - {restriction_days}일 제한 중")
                    return False

            # 전일 종가 계산 (현재가에서 등락률을 역산)
            if change_rate != 0:
                prev_close = current_price / (1 + change_rate / 100)
            else:
                prev_close = current_price
            
            # Rise Tracker에 추가 (급등 시작점 = 전일 종가)
            success = self.rise_tracker.add_stock(
                stock_code=stock_code, 
                start_price=prev_close, 
                stock_name=stock_name,
                daily_change_rate=change_rate
            )
            
            if success:
                # 현재가로 가격 업데이트 (고점 설정) - 신규 추가 시에는 고가 데이터 없음
                self.rise_tracker.update_price(stock_code, current_price)
                
                # 새 종목 추가 시 데이터 저장
                self.save_rise_tracker_data()
                
                # 실시간 등록 요청 (WebSocket) - 성공 시에만 실행
                if self.websocket_req_queue:
                    self.websocket_req_queue.put({
                        'action_id': '실시간등록',
                        '종목코드': stock_code,  # WebSocket 함수에서 기대하는 키명 사용
                        'data_type': '0B'  # 주식체결
                    })
                    log_info(f"실시간 등록 요청: {stock_code}")
                
                # 종목 기본정보 요청 (추가 분석용)
                if self.tr_req_queue:
                    self.tr_req_queue.put({
                        'action_id': '주식기본정보',
                        '종목코드': stock_code,
                        'purpose': 'TUMEPOK_ANALYSIS'
                    })
                    log_debug(f"종목 기본정보 요청: {stock_code}")
                
                return True
            else:
                return False
            
        except Exception as e:
            log_error(f"급등주 추적 추가 실패: {stock_code}, {str(e)}")
            return False
    
    def add_test_tracking_data(self):
        """테스트용 추적 데이터 추가"""
        try:
            # 테스트 데이터 1: 이화전기 (가상)
            self.tracking_stocks['123456'] = {
                'stock_code': '123456',
                'stock_name': '이화전기',
                'start_date': '20250903',
                'start_price': 1000,  # 시작가
                'base_price': 1000,   # 기준가
                'high_price': 1450,   # 고점 (45% 상승)
                'current_price': 1300, # 현재가 (고점에서 10% 하락)
                'rise_days': 3,
                'rise_rate': 45.0,    # 상승률
                'drop_rate': 10.3,    # 하락률
                'status': 'READY',
                'waiting_days': 0,
                'bought_stages': set(),
                'target_drop_info': None,
                'created_time': datetime.now()
            }
            
            # 테스트 데이터 2: 이아이디 (가상)
            self.tracking_stocks['234567'] = {
                'stock_code': '234567',
                'stock_name': '이아이디',
                'start_date': '20250903',
                'start_price': 2000,
                'base_price': 2000,
                'high_price': 2900,   # 45% 상승
                'current_price': 2600, # 고점에서 10% 하락
                'rise_days': 2,
                'rise_rate': 45.0,
                'drop_rate': 10.3,
                'status': 'TRACKING',
                'waiting_days': 0,
                'bought_stages': set(),
                'target_drop_info': None,
                'created_time': datetime.now()
            }
            
            # 테스트 데이터 3: 이트론 (가상)
            self.tracking_stocks['345678'] = {
                'stock_code': '345678',
                'stock_name': '이트론',
                'start_date': '20250903',
                'start_price': 1500,
                'base_price': 1500,
                'high_price': 2175,   # 45% 상승
                'current_price': 1950, # 고점에서 10% 하락
                'rise_days': 4,
                'rise_rate': 45.0,
                'drop_rate': 10.3,
                'status': 'READY',
                'waiting_days': 0,
                'bought_stages': {'1차'},
                'target_drop_info': None,
                'created_time': datetime.now()
            }
            
            log_info("테스트 추적 데이터 3개 추가 완료")
            
        except Exception as e:
            log_error(f"테스트 데이터 추가 실패: {str(e)}")
    
    def save_rise_tracker_data(self):
        """연속상승 추적 데이터 저장"""
        try:
            if self.rise_tracker:
                rise_tracker_file = "rise_tracker_data.json"
                success = self.rise_tracker.save_tracking_data(rise_tracker_file)
                if success:
                    log_debug(f"연속상승 추적 데이터 저장 완료: {len(self.rise_tracker.tracking_stocks)}개 종목")
                return success
            return False
            
        except Exception as e:
            log_error(f"연속상승 추적 데이터 저장 실패: {str(e)}")
            return False
    
    def cleanup_sold_stocks_from_tracking(self, current_holdings):
        """매수 이력이 있고 매도 완료된 종목만 연속상승 추적에서 제거"""
        try:
            if not current_holdings:
                log_debug("보유 종목 정보가 없어 정리 생략")
                return
            
            # 현재 보유 종목 코드 집합
            holding_codes = set(current_holdings.keys()) if isinstance(current_holdings, dict) else set(current_holdings)
            
            # 연속상승 추적에서 매수->매도 완료된 종목만 제거
            removed_stocks = []
            if self.rise_tracker and self.rise_tracker.tracking_stocks:
                tracking_codes = list(self.rise_tracker.tracking_stocks.keys())
                
                for stock_code in tracking_codes:
                    # 보유하지 않고 + 매수 이력이 있는 종목만 제거
                    if stock_code not in holding_codes and stock_code in self.bought_stocks_history:
                        stock_info = self.rise_tracker.tracking_stocks.get(stock_code)
                        stock_name = stock_info.stock_name if stock_info and hasattr(stock_info, 'stock_name') else stock_code
                        
                        try:
                            self.rise_tracker.remove_stock(stock_code)
                            # 매수 이력에서도 제거 (매도 완료 처리)
                            self.bought_stocks_history.discard(stock_code)
                            removed_stocks.append(f"{stock_name}({stock_code})")
                            log_info(f"매수->매도 완료 종목 추적 제거: {stock_name}({stock_code})")
                        except Exception as e:
                            log_error(f"추적 제거 실패: {stock_code}, {e}")
                    elif stock_code not in holding_codes:
                        # 매수 이력이 없는 종목은 보존 (추적만 된 종목)
                        stock_info = self.rise_tracker.tracking_stocks.get(stock_code)
                        stock_name = stock_info.stock_name if stock_info and hasattr(stock_info, 'stock_name') else stock_code
                        log_debug(f"추적 전용 종목 보존: {stock_name}({stock_code}) - 매수 이력 없음")
            
            # 투매폭 추적에서도 매수->매도 완료된 종목만 제거
            tracking_codes = list(self.tracking_stocks.keys())
            for stock_code in tracking_codes:
                # 보유하지 않고 + 매수 이력이 있는 종목만 제거
                if stock_code not in holding_codes and stock_code in self.bought_stocks_history:
                    stock_info = self.tracking_stocks.get(stock_code, {})
                    stock_name = stock_info.get('name', stock_code)
                    
                    del self.tracking_stocks[stock_code]
                    # 중복 카운트 방지
                    removed_name = f"{stock_name}({stock_code})"
                    if removed_name not in removed_stocks:
                        removed_stocks.append(removed_name)
                    log_info(f"매수->매도 완료 종목 투매폭 추적 제거: {stock_name}({stock_code})")
                elif stock_code not in holding_codes:
                    # 매수 이력이 없는 종목은 보존
                    stock_info = self.tracking_stocks.get(stock_code, {})
                    stock_name = stock_info.get('name', stock_code)
                    log_debug(f"추적 전용 종목 보존: {stock_name}({stock_code}) - 매수 이력 없음")
            
            if removed_stocks:
                log_info(f"매수->매도 완료 종목 정리 완료: {len(removed_stocks)}개 - {', '.join(removed_stocks)}")
                log_info(f"현재 매수 이력 종목: {len(self.bought_stocks_history)}개")
            else:
                log_debug("매수->매도 완료 종목 없음 - 정리 사항 없음")
                
        except Exception as e:
            log_error(f"매도 완료 종목 정리 실패: {str(e)}")
    
    def load_bought_history(self):
        """매수 이력 파일 로드"""
        try:
            bought_history_file = "bought_stocks_history.json"
            if os.path.exists(bought_history_file):
                with open(bought_history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.bought_stocks_history = set(data.get('bought_stocks', []))
                    log_info(f"매수 이력 로드 완료: {len(self.bought_stocks_history)}개 종목")
            else:
                log_info("매수 이력 파일 없음 - 새로 시작")
                
        except Exception as e:
            log_error(f"매수 이력 로드 실패: {str(e)}")
            self.bought_stocks_history = set()
    
    def save_bought_history(self):
        """매수 이력 파일 저장"""
        try:
            bought_history_file = "bought_stocks_history.json"
            data = {
                'bought_stocks': list(self.bought_stocks_history),
                'last_update': datetime.now().isoformat()
            }
            
            with open(bought_history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            log_debug(f"매수 이력 저장 완료: {len(self.bought_stocks_history)}개 종목")
            
        except Exception as e:
            log_error(f"매수 이력 저장 실패: {str(e)}")
    
    def update_config(self, new_config):
        """투매폭 설정 업데이트"""
        try:
            self.config = new_config

            # RiseTracker에도 설정 업데이트
            if hasattr(self, 'rise_tracker') and self.rise_tracker:
                self.rise_tracker.update_config(new_config)

            # SupportAnalyzer에도 설정 업데이트
            if hasattr(self, 'support_analyzer') and self.support_analyzer:
                self.support_analyzer.update_config(new_config)

            log_info("투매폭 엔진 설정 업데이트 완료")
            log_debug(f"새 설정: 기본매수금액={new_config.get_base_buy_amount():,}원, "
                     f"급등기준={new_config.get_rise_threshold()}%, "
                     f"최대추적={new_config.get_max_tracking_stocks()}개")

        except Exception as e:
            log_error(f"투매폭 엔진 설정 업데이트 실패: {str(e)}")

    def force_cleanup_position(self, stock_code, reason="매도완료"):
        """포지션 강제 정리 (중복 손절 방지용)"""
        try:
            # 포지션 제거
            if stock_code in self.positions:
                position = self.positions[stock_code]
                stock_name = position.get('stock_name', stock_code)
                del self.positions[stock_code]
                log_info(f"🗑️ 포지션 강제 정리: {stock_name}({stock_code}) - {reason}")

            # 추적 정리
            if stock_code in self.tracking_stocks:
                del self.tracking_stocks[stock_code]
                log_debug(f"추적 정리: {stock_code}")

            # RiseTracker 정리
            if hasattr(self, 'rise_tracker') and self.rise_tracker:
                self.rise_tracker.remove_stock(stock_code)
                log_debug(f"RiseTracker 정리: {stock_code}")

            return True

        except Exception as e:
            log_error(f"포지션 강제 정리 실패: {stock_code}, {str(e)}")
            return False

    def cleanup_all_sold_positions(self):
        """모든 매도된 포지션 정리 (수동 실행용)"""
        try:
            if not self.positions:
                log_info("정리할 포지션이 없습니다.")
                return

            # 계좌에서 실제 보유하지 않은 포지션들을 찾아서 정리
            if hasattr(self.main_window, 'data_manager') and self.main_window.data_manager:
                account_df = self.main_window.data_manager.account_info_df

                for stock_code in list(self.positions.keys()):
                    # 계좌에 실제로 없는 종목은 포지션에서 제거
                    if account_df.empty or stock_code not in account_df.index:
                        position = self.positions[stock_code]
                        stock_name = position.get('stock_name', stock_code)

                        log_info(f"🧹 매도 완료된 포지션 자동 정리: {stock_name}({stock_code})")
                        self.force_cleanup_position(stock_code, "계좌에서 제거됨")

                log_info("매도된 포지션 정리 완료")
            else:
                log_warning("DataManager가 없어 포지션 정리를 할 수 없습니다.")

        except Exception as e:
            log_error(f"매도된 포지션 정리 실패: {str(e)}")