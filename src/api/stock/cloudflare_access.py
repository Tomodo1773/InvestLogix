"""
Cloudflare Access が発行した JWT の検証

Cloudflare は Access で保護したアプリケーションへのリクエストに `Cf-Access-Jwt-Assertion`
ヘッダーを付与する。ヘッダーが存在することは信頼の根拠にならないため、Access チームの JWKS で
署名を検証し、issuer / audience / 有効期限まで確認する。これにより Cloudflare を迂回した
Cloud Run への直アクセスも同じ経路で拒否できる。

このモジュールは外部トークンの検証だけを担当する。アプリ内ユーザーへの解決は
services/user_service.py、FastAPI への接続は auth.py が行う。
"""

from dataclasses import dataclass
from typing import Any

import httpx
from jose import JWTError, jwt

from .database import settings
from .utils.cache import timed_cache

# Cloudflare が Access 通過後のリクエストに付与する JWT のヘッダー名
ACCESS_JWT_HEADER = "Cf-Access-Jwt-Assertion"

# Cloudflare の署名鍵は数週間単位でしか入れ替わらないため、1時間キャッシュすれば足りる
JWKS_CACHE_SECONDS = 3600
JWKS_TIMEOUT_SECONDS = 5.0


class AccessTokenError(Exception):
    """Access JWT を信頼できなかったことを表す"""


@dataclass(frozen=True)
class AccessIdentity:
    """
    Access が保証する外部ID

    - issuer: Access チームのURL（例: https://example.cloudflareaccess.com）
    - subject: Access が採番する利用者ID。IdP側でメールが変わっても不変
    - email: IdP が確認済みのメールアドレス
    """

    issuer: str
    subject: str
    email: str


@timed_cache(seconds=JWKS_CACHE_SECONDS)
async def fetch_jwks(team_domain: str) -> dict[str, Any]:
    """Access チームの公開鍵（JWK Set）を取得する"""
    async with httpx.AsyncClient(timeout=JWKS_TIMEOUT_SECONDS) as client:
        response = await client.get(f"https://{team_domain}/cdn-cgi/access/certs")
        response.raise_for_status()
        return response.json()


async def verify_access_token(token: str) -> AccessIdentity:
    """
    Access JWT を検証して外部IDを返す
    - token: Cf-Access-Jwt-Assertion ヘッダーの値
    - 署名・issuer・audience・有効期限のいずれかが不正なら AccessTokenError
    """
    if not settings.CF_ACCESS_TEAM_DOMAIN or not settings.CF_ACCESS_AUD:
        raise AccessTokenError("Cloudflare Accessの検証設定が未構成です")

    issuer = f"https://{settings.CF_ACCESS_TEAM_DOMAIN}"

    try:
        jwks = await fetch_jwks(settings.CF_ACCESS_TEAM_DOMAIN)
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.CF_ACCESS_AUD,
            issuer=issuer,
        )
    except (JWTError, httpx.HTTPError) as e:
        raise AccessTokenError(str(e)) from e

    subject = claims.get("sub")
    email = claims.get("email")
    if not subject or not email:
        # サービストークンでの認証は sub / email を持たない。第1段階では利用者ログインのみ扱う
        raise AccessTokenError("Access JWTに sub / email が含まれていません")

    return AccessIdentity(issuer=issuer, subject=subject, email=email)
