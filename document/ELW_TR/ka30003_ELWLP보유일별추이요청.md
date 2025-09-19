# ELWLP보유일별추이요청

**TR 코드:** ka30003

## Python 코드

```python
import requests
import json

# ELWLP보유일별추이요청
def fn_ka30003(token, data, cont_yn='N', next_key=''):
	# 1. 요청할 API URL
	#host = 'https://mockapi.kiwoom.com' # 모의투자
	host = 'https://api.kiwoom.com' # 실전투자
	endpoint = '/api/dostk/elw'
	url =  host + endpoint

	# 2. header 데이터
	headers = {
		'Content-Type': 'application/json;charset=UTF-8', # 컨텐츠타입
		'authorization': f'Bearer {token}', # 접근토큰
		'cont-yn': cont_yn, # 연속조회여부
		'next-key': next_key, # 연속조회키
		'api-id': 'ka30003', # TR명
	}

	# 3. http POST 요청
	response = requests.post(url, headers=headers, json=data)

	# 4. 응답 상태 코드와 데이터 출력
	print('Code:', response.status_code)
	print('Header:', json.dumps({key: response.headers.get(key) for key in ['next-key', 'cont-yn', 'api-id']}, indent=4, ensure_ascii=False))
	print('Body:', json.dumps(response.json(), indent=4, ensure_ascii=False))  # JSON 응답을 파싱하여 출력

# 실행 구간
if __name__ == '__main__':
	# 1. 토큰 설정
	MY_ACCESS_TOKEN = '사용자 AccessToken'# 접근토큰

	# 2. 요청 데이터
	params = {
		'bsis_aset_cd': '57KJ99', # 기초자산코드 
		'base_dt': '20241122', # 기준일자 YYYYMMDD
	}

	# 3. API 실행
	fn_ka30003(token=MY_ACCESS_TOKEN, data=params)

	# next-key, cont-yn 값이 있을 경우
	# fn_ka30003(token=MY_ACCESS_TOKEN, data=params, cont_yn='Y', next_key='nextkey..')
```

## 요청 파라미터

### Header
| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| authorization | 접근토큰 | String | Y | 1000 | 토큰 지정시 토큰타입("Bearer") 붙혀서 호출<br>예) Bearer Egicyx... |
| cont-yn | 연속조회여부 | String | N | 1 | 응답 Header의 연속조회여부값이 Y일 경우 다음데이터 요청시 응답 Header의 cont-yn값 세팅 |
| next-key | 연속조회키 | String | N | 50 | 응답 Header의 연속조회여부값이 Y일 경우 다음데이터 요청시 응답 Header의 next-key값 세팅 |
| api-id | TR명 | String | Y | 10 |  |

### Body
| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| bsis_aset_cd | 기초자산코드 | String | Y | 12 |  |
| base_dt | 기준일자 | String | Y | 8 | YYYYMMDD |

## 응답 파라미터

### Header
| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| cont-yn | 연속조회여부 | String | N | 1 | 다음 데이터가 있을시 Y값 전달 |
| next-key | 연속조회키 | String | N | 50 | 다음 데이터가 있을시 다음 키값 전달 |
| api-id | TR명 | String | Y | 10 |  |

### Body
| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| elwlpposs_daly_trnsn | ELWLP보유일별추이 | LIST | N |  |  |
| - dt | 일자 | String | N | 20 |  |
| - cur_prc | 현재가 | String | N | 20 |  |
| - pre_tp | 대비구분 | String | N | 20 |  |
| - pred_pre | 전일대비 | String | N | 20 |  |
| - flu_rt | 등락율 | String | N | 20 |  |
| - trde_qty | 거래량 | String | N | 20 |  |
| - trde_prica | 거래대금 | String | N | 20 |  |
| - chg_qty | 변동수량 | String | N | 20 |  |
| - lprmnd_qty | LP보유수량 | String | N | 20 |  |
| - wght | 비중 | String | N | 20 |  |