# ETF NAV (0G)

## TR 정보
- **TR 코드**: 0G
- **TR 명**: ETF NAV
- **타입**: WebSocket 실시간 데이터
- **용도**: ETF NAV 실시간 통신

## WebSocket 연결 및 실시간 데이터 수신

```python
import asyncio 
import websockets
import json

SOCKET_URL = 'wss://api.kiwoom.com:10000/api/dostk/websocket'
ACCESS_TOKEN = '사용자 AccessToken'

async def etf_nav_websocket():
	async with websockets.connect(SOCKET_URL) as websocket:
		# 로그인
		await websocket.send(json.dumps({'trnm': 'LOGIN', 'token': ACCESS_TOKEN}))
		
		# ETF NAV 실시간 등록
		await websocket.send(json.dumps({
			'trnm': 'REG',
			'grp_no': '1',
			'refresh': '1', 
			'data': [{'item': ['069500'], 'type': ['0G']}]  # KODEX 200 ETF
		}))
		
		# 실시간 데이터 수신
		while True:
			try:
				response = await websocket.recv()
				data = json.loads(response)
				if data.get('trnm') == 'PING':
					await websocket.send(response)
				else:
					print(f'ETF NAV 데이터: {data}')
			except websockets.ConnectionClosed:
				break

if __name__ == '__main__':
	asyncio.run(etf_nav_websocket())
```

## 기능 설명
ETF의 순자산가치(NAV) 정보를 실시간으로 수신합니다.