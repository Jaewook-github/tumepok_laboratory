# VI발동/해제 (1h)

## TR 정보
- **TR 코드**: 1h
- **TR 명**: VI발동/해제
- **타입**: WebSocket 실시간 데이터
- **용도**: 변동성완화장치(VI) 발동/해제 실시간 통신

## WebSocket 연결 및 실시간 데이터 수신

```python
import asyncio 
import websockets
import json

SOCKET_URL = 'wss://api.kiwoom.com:10000/api/dostk/websocket'
ACCESS_TOKEN = '사용자 AccessToken'

async def vi_trigger_websocket():
	async with websockets.connect(SOCKET_URL) as websocket:
		await websocket.send(json.dumps({'trnm': 'LOGIN', 'token': ACCESS_TOKEN}))
		
		await websocket.send(json.dumps({
			'trnm': 'REG',
			'grp_no': '1',
			'refresh': '1',
			'data': [{'item': ['005930'], 'type': ['1h']}]
		}))
		
		while True:
			try:
				response = await websocket.recv()
				data = json.loads(response)
				if data.get('trnm') == 'PING':
					await websocket.send(response)
				else:
					print(f'VI발동/해제 데이터: {data}')
			except websockets.ConnectionClosed:
				break

if __name__ == '__main__':
	asyncio.run(vi_trigger_websocket())
```

## 기능 설명
변동성완화장치(VI) 발동 및 해제 정보를 실시간으로 수신합니다.

### VI(Volatility Interruption) 설명
- 급격한 가격 변동 시 일시적으로 거래가 정지되는 제도
- 발동 시점과 해제 시점을 실시간으로 통지