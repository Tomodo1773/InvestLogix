import aiohttp
import asyncio
# import json
import os
# import pandas as pd
from typing import Dict, Any
from datetime import datetime, timedelta


class JQuantsAPI:
    def __init__(self):
        self.base_url = "https://api.jquants.com/v1"
        self.refresh_token = None
        self.id_token = None
        self.refresh_token_expiry = None
        self.id_token_expiry = None

    @staticmethod
    def ensure_directory_exists(path):
        if not os.path.exists(path):
            os.makedirs(path)

    async def get_refresh_token(self):
        mail_address = os.environ.get("JQUANTS_MAIL_ADDRESS")
        password = os.environ.get("JQUANTS_PASSWORD")
        data = {"mailaddress": mail_address, "password": password}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/token/auth_user", json=data) as response:
                response_data = await response.json()
                self.refresh_token = response_data["refreshToken"]
                self.refresh_token_expiry = datetime.now() + timedelta(days=7)

    async def get_id_token(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/token/auth_refresh?refreshtoken={self.refresh_token}"
            ) as response:
                response_data = await response.json()
                self.id_token = response_data["idToken"]
                self.id_token_expiry = datetime.now() + timedelta(hours=24)

    async def ensure_valid_tokens(self):
        now = datetime.now()
        if self.refresh_token is None or now >= self.refresh_token_expiry:
            await self.get_refresh_token()
        if self.id_token is None or now >= self.id_token_expiry:
            await self.get_id_token()

    async def get_stock_list(self, params: Dict[str, Any], file_path: str = "./data/stock_list.csv"):
        await self.ensure_valid_tokens()
        headers = {"Authorization": f"Bearer {self.id_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/listed/info", headers=headers, params=params) as response:
                response_data = await response.json()
                # df = pd.DataFrame(response_data["info"])
                # df.to_csv(file_path, index=False)

    async def get_stock_price(self, params: Dict[str, Any], base_path: str = "./data/stock/"):
        await self.ensure_valid_tokens()
        headers = {"Authorization": f"Bearer {self.id_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/prices/daily_quotes", headers=headers, params=params) as response:
                response_data = await response.json()
                # df = pd.DataFrame(response_data["daily_quotes"])
                # file_path = f'{base_path}{params["code"]}_price.csv'
                # df.to_csv(file_path, index=False)

    # 財務情報取得
    async def get_financial_information(self, params: Dict[str, Any], base_path: str = "./data/stock/financial/"):
        await self.ensure_valid_tokens()
        headers = {"Authorization": f"Bearer {self.id_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/fins/statements", headers=headers, params=params) as response:
                response_data = await response.json()
                # df = pd.DataFrame(response_data["statements"])
                # file_path = f'{base_path}{params["code"]}.csv'
                # df.to_csv(file_path, index=False)

    async def get_earnings_announcement(self):
        await self.ensure_valid_tokens()
        headers = {"Authorization": f"Bearer {self.id_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/fins/announcement", headers=headers) as response:
                response_data = await response.json()
                # df = pd.DataFrame(response_data["announcement"])
                return response_data

    async def initialize(self):
        await self.ensure_valid_tokens()


# 使用例
async def main():
    api = JQuantsAPI()
    await api.initialize()

    # 各メソッドの呼び出し例
    await api.get_stock_list(params={})
    await api.get_stock_price(params={"code": "86970"})


if __name__ == "__main__":
    asyncio.run(main())
