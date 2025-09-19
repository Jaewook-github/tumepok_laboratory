# ELW 지표 (0u)

## TR 정보
- **TR 코드**: 0u
- **TR 명**: ELW 지표
- **타입**: WebSocket 실시간 데이터
- **용도**: ELW 지표 실시간 통신

## WebSocket 연결 및 실시간 데이터 수신

```python
import asyncio 
import websockets
import json

SOCKET_URL = 'wss://api.kiwoom.com:10000/api/dostk/websocket'
ACCESS_TOKEN = '사용자 AccessToken'

async def elw_indicator_websocket():
	async with websockets.connect(SOCKET_URL) as websocket:
		await websocket.send(json.dumps({'trnm': 'LOGIN', 'token': ACCESS_TOKEN}))
		
		await websocket.send(json.dumps({
			'trnm': 'REG',
			'grp_no': '1',
			'refresh': '1',
			'data': [{'item': ['580001'], 'type': ['0u']}]  # ELW 종목코드 예시
		}))
		
		while True:
			try:
				response = await websocket.recv()
				data = json.loads(response)
				if data.get('trnm') == 'PING':
					await websocket.send(response)
				else:
					print(f'ELW 지표 데이터: {data}')
			except websockets.ConnectionClosed:
				break

if __name__ == '__main__':
	asyncio.run(elw_indicator_websocket())
```

## 기능 설명
ELW(주식워런트) 관련 지표들을 실시간으로 수신합니다.