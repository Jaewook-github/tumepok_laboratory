# 투매폭 설정 관리 시스템 가이드

## 개요

투매폭 자동매매 시스템의 설정을 관리하는 종합적인 시스템입니다. 사용자 친화적인 GUI를 통해 모든 설정을 조정할 수 있으며, 프리셋 관리, 백업/복원, 실시간 적용 등의 고급 기능을 제공합니다.

## 주요 기능

### 1. 설정 다이얼로그 (TumepokSettingsDialog)

#### 기본 설정 탭
- **기본 매수 금액**: 투매폭 매매 시 사용할 기본 금액 (50,000원 ~ 10,000,000원)
- **최대 추적 종목**: 동시에 추적할 수 있는 최대 종목 수 (1개 ~ 50개)
- **급등 기준**: 급등주로 인식할 상승률 기준 (10% ~ 100%)
- **최대 연속상승일**: 추적을 중단할 연속상승일 한계 (3일 ~ 10일)
- **반등 대기일**: 투매폭 진입 전 반등 대기 기간 (1일 ~ 5일)

#### 단계별 매수 설정 탭
- **1차 매수 (강매수)**: 전체 포지션 중 1차 매수 비율 (10% ~ 80%)
- **2차 매수 (보통매수)**: 전체 포지션 중 2차 매수 비율 (10% ~ 80%)
- **3차 매수 (약매수)**: 전체 포지션 중 3차 매수 비율 (10% ~ 80%)
- **실시간 합계 검증**: 3단계 비율의 합이 100%인지 실시간 확인

#### 리스크 관리 설정 탭
- **연속상승일수별 포지션 축소율**:
  - 1일 연속상승: 기본 포지션 (1.0배)
  - 2일 연속상승: 기본 포지션 (1.0배)
  - 3일 연속상승: 포지션 축소 (0.8배)
  - 4일 연속상승: 포지션 축소 (0.5배)
  - 5일 이상: 매수 금지 (0.0배)

#### 포지션 관리 설정 탭
- **손절률**: 자동 손절 기준 (-10% ~ 0%)
- **트레일링 발동률**: 트레일링 스탑 시작 수익률 (0% ~ 10%)
- **트레일링 매도률**: 고점 대비 하락 시 매도 기준 (-5% ~ 0%)

#### 지지 조건 설정 탭
- **RSI 과매도 기준**: RSI 과매도 판단 기준 (20 ~ 40)
- **거래량 급감 기준**: 거래량 급감 판단 비율 (0.1 ~ 0.5배)
- **지지선 허용 오차**: 지지선 인식 허용 오차 (0.5% ~ 5%)
- **단계별 조건 완화**:
  - 1차 매수: 3개 조건 중 1개 이상 충족
  - 2차 매수: 3개 조건 중 2개 이상 충족
  - 3차 매수: 3개 조건 중 2개 이상 충족

### 2. 프리셋 관리 시스템

#### 기본 프리셋
- **보수적**: 안전한 매매를 위한 보수적 설정
  - 매수금액: 100,000원
  - 추적종목: 10개
  - 급등기준: 25%
  - 손절률: -1.5%
  
- **균형**: 리스크와 수익의 균형을 맞춘 설정 (기본값)
  - 매수금액: 200,000원
  - 추적종목: 20개
  - 급등기준: 20%
  - 손절률: -2.0%
  
- **공격적**: 높은 수익을 추구하는 공격적 설정
  - 매수금액: 300,000원
  - 추적종목: 30개
  - 급등기준: 15%
  - 손절률: -3.0%

#### 사용자 정의 프리셋
- **프리셋 저장**: 현재 설정을 새로운 프리셋으로 저장
- **프리셋 불러오기**: 저장된 프리셋을 현재 설정에 적용
- **프리셋 삭제**: 불필요한 프리셋 삭제
- **프리셋 내보내기**: 프리셋을 JSON 파일로 내보내기
- **프리셋 가져오기**: 외부 JSON 파일에서 프리셋 가져오기

### 3. 백업 및 복원 시스템

#### 자동 백업
- 설정 변경 시 자동으로 백업 파일 생성
- 타임스탬프 기반 백업 파일명 (tumepok_config_20250903_111946.json)
- data/backup/ 디렉토리에 백업 파일 저장

#### 수동 백업/복원
- **백업**: 현재 설정을 지정한 위치에 백업
- **복원**: 백업 파일에서 설정 복원
- **유효성 검증**: 복원 시 설정 유효성 자동 검증

### 4. 실시간 설정 적용

#### 디바운싱 적용
- 설정 변경 후 1초 대기 후 적용 (연속 변경 시 마지막 변경만 적용)
- 불필요한 연산 방지 및 성능 최적화

#### 유효성 검증
- 실시간으로 설정값 유효성 검증
- 잘못된 설정 시 즉시 경고 표시
- 단계별 비율 합계 실시간 확인

#### 시그널 기반 통신
- 설정 변경 시 settings_changed 시그널 발송
- 메인 시스템에서 실시간으로 설정 변경 감지 및 적용

## 설정 데이터 구조

### JSON 설정 파일 구조
```json
{
  "base_buy_amount": 500000,
  "max_tracking_stocks": 20,
  "rise_threshold": 20.0,
  "max_rise_days": 7,
  "wait_days": 3,
  "stage_ratios": {
    "1차": 0.5,
    "2차": 0.3,
    "3차": 0.2
  },
  "position_ratios": {
    "1": 1.0,
    "2": 1.0,
    "3": 0.8,
    "4": 0.5
  },
  "stop_loss_rate": -2.0,
  "trailing_trigger_rate": 2.0,
  "trailing_sell_rate": -1.0,
  "rsi_threshold": 30,
  "volume_ratio_threshold": 0.25,
  "support_tolerance": 0.01,
  "condition_requirements": {
    "1차": 1,
    "2차": 2,
    "3차": 2
  },
  "daily_loss_limit": -200000,
  "max_daily_trades": 20,
  "tumepok_active": true
}
```

## 사용 방법

### 1. 설정 다이얼로그 열기
```python
from ui.settings_dialog import TumepokSettingsDialog
from config.tumepok_config import TumepokConfig

config = TumepokConfig()
dialog = TumepokSettingsDialog(config, parent_window)

# 설정 변경 시그널 연결
dialog.settings_changed.connect(on_settings_changed)

# 다이얼로그 표시
if dialog.exec_() == QDialog.Accepted:
    print("설정이 적용되었습니다.")
```

### 2. 프로그래밍 방식으로 설정 변경
```python
config = TumepokConfig()

# 기본 설정 변경
config.set_base_buy_amount(300000)
config.set_max_tracking_stocks(15)
config.set_rise_threshold(25.0)

# 단계별 비율 변경
config.set_stage_ratios({
    "1차": 0.4,
    "2차": 0.3,
    "3차": 0.3
})

# 설정 저장
config.save_config()
```

### 3. 투매폭 계산 활용
```python
config = TumepokConfig()

# 상승률에 따른 적정 하락폭 계산
drop_range = config.calculate_target_drop_range(35.0)
print(f"35% 상승 시 적정 하락폭: {drop_range['min_drop']}~{drop_range['max_drop']}%")

# 포지션 크기 계산
position_size = config.calculate_position_size(200000, rise_days=3, rise_rate=50)
print(f"3일 연속상승, 50% 상승 시 포지션: {position_size:,}원")

# 단계별 매수 금액 계산
stage1_amount = config.get_buy_stage_amount(200000, "1차", rise_days=2)
print(f"1차 매수 금액: {stage1_amount:,}원")
```

## 주의사항

### 설정 유효성
- 단계별 매수 비율의 합은 반드시 100%여야 합니다
- 손절률은 음수값이어야 합니다
- 트레일링 발동률은 양수값이어야 합니다
- 모든 설정값은 지정된 범위 내에 있어야 합니다

### 백업 관리
- 중요한 설정 변경 전에는 반드시 백업을 생성하세요
- 정기적으로 백업 파일을 정리하여 디스크 공간을 관리하세요
- 백업 파일은 안전한 위치에 별도 보관하는 것을 권장합니다

### 성능 고려사항
- 실시간 설정 적용은 디바운싱을 통해 최적화되어 있습니다
- 너무 빈번한 설정 변경은 시스템 성능에 영향을 줄 수 있습니다
- 대량의 프리셋 저장 시 메모리 사용량을 고려하세요

## 문제 해결

### 설정 파일 손상
```python
# 기본값으로 복원
config = TumepokConfig()
config.reset_to_defaults()
config.save_config()
```

### 프리셋 로드 실패
```python
# 유효성 검증 후 로드
if config.validate_config():
    config.save_config()
else:
    print("설정이 유효하지 않습니다.")
    config.reset_to_defaults()
```

### 실시간 적용 문제
```python
# 수동으로 설정 적용
dialog.apply_settings()

# 또는 강제로 시그널 발송
dialog.settings_changed.emit(config.get_all_settings())
```

이 가이드를 참고하여 투매폭 설정 관리 시스템을 효과적으로 활용하시기 바랍니다.