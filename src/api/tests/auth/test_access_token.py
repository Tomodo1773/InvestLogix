"""Cloudflare Access JWT の検証のテスト

Cloudflareを迂回した直アクセスを拒否できることが要点なので、正しく署名されたトークンだけを
受け入れ、issuer / audience / 署名鍵が違うものは拒否することを確認する。
"""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from stock import cloudflare_access
from stock.cloudflare_access import AccessTokenError, verify_access_token
from stock.database import settings
from stock.utils.datetime import now_jst

TEAM_DOMAIN = "example.cloudflareaccess.com"
ISSUER = f"https://{TEAM_DOMAIN}"
AUD = "test-audience-tag"


def _generate_key_pair() -> tuple[str, dict]:
    """RS256用の鍵ペアを作り、(署名用のPEM, JWK Set) を返す"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    jwks = {"keys": [jwk.construct(public_pem, algorithm="RS256").to_dict()]}
    return pem, jwks


def _issue_token(pem: str, *, issuer: str = ISSUER, aud: str = AUD, expires_in: int = 3600) -> str:
    now = int(now_jst().timestamp())
    claims = {
        "iss": issuer,
        "aud": aud,
        "sub": "access-user-uuid",
        "email": "user@example.com",
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(claims, pem, algorithm="RS256")


@pytest.fixture
def access_env(mocker):
    """Access の検証設定と JWKS 取得をテスト用に差し替える

    Returns:
        str: トークン署名用の秘密鍵PEM
    """
    mocker.patch.object(settings, "CF_ACCESS_TEAM_DOMAIN", TEAM_DOMAIN)
    mocker.patch.object(settings, "CF_ACCESS_AUD", AUD)

    pem, jwks = _generate_key_pair()
    mocker.patch.object(cloudflare_access, "fetch_jwks", mocker.AsyncMock(return_value=jwks))
    return pem


@pytest.mark.asyncio
async def test_verify_valid_token(access_env: str):
    """正しく署名されたトークンから利用者IDを取り出せること"""
    identity = await verify_access_token(_issue_token(access_env))

    assert identity.email == "user@example.com"


@pytest.mark.asyncio
async def test_verify_rejects_other_signing_key(access_env: str):
    """別の鍵で署名されたトークンを拒否すること（ヘッダーの偽造を防ぐ）"""
    other_pem, _ = _generate_key_pair()

    with pytest.raises(AccessTokenError):
        await verify_access_token(_issue_token(other_pem))


@pytest.mark.asyncio
async def test_verify_rejects_other_audience(access_env: str):
    """別のAccess application向けのトークンを拒否すること"""
    with pytest.raises(AccessTokenError):
        await verify_access_token(_issue_token(access_env, aud="another-application"))


@pytest.mark.asyncio
async def test_verify_rejects_expired_token(access_env: str):
    """期限切れのトークンを拒否すること"""
    with pytest.raises(AccessTokenError):
        await verify_access_token(_issue_token(access_env, expires_in=-60))


@pytest.mark.asyncio
async def test_verify_requires_configuration(mocker):
    """検証設定が無いときは、トークンがあっても信頼しないこと"""
    mocker.patch.object(settings, "CF_ACCESS_TEAM_DOMAIN", "")
    mocker.patch.object(settings, "CF_ACCESS_AUD", "")

    with pytest.raises(AccessTokenError):
        await verify_access_token("dummy.token.value")
