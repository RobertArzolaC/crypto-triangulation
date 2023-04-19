import requests
import hashlib
import hmac
import time


class BinanceClient:

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = 'https://api.binance.com'

    def generate_signature(self, payload):
        signature = hmac.new(
            self.api_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return signature

    def send_request(self, method, endpoint, params=None, headers=None):
        url = self.api_url + endpoint
        timestamp = str(int(time.time() * 1000))
        headers = headers or {}
        headers['X-MBX-APIKEY'] = self.api_key
        params = params or {}
        params['timestamp'] = timestamp
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = self.generate_signature(query_string)
        query_string += f"&signature={signature}"
        if method == 'GET':
            response = requests.get(url, params=query_string, headers=headers)
        elif method == 'POST':
            response = requests.post(url, data=query_string, headers=headers)
        return response.json()

    def create_order(self, symbol, side, type, quantity):
        endpoint = '/api/v3/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'quantity': quantity
        }
        return self.send_request('POST', endpoint, params)
