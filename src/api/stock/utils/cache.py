"""
キャッシュユーティリティモジュール

このモジュールは、関数の結果をキャッシュするためのデコレータを提供します。
主にAPIリクエストなど、頻繁に呼び出されるが結果が短時間で変わらない関数に使用します。
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, cast

# 型変数の定義
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def timed_cache(seconds: int = 3600):
    """
    指定した秒数の間、関数の結果をキャッシュするデコレータ

    このデコレータは、同じ引数で関数が呼び出された場合に、
    指定された時間内であればキャッシュから結果を返します。
    これにより、APIリクエストなどの重い処理を減らすことができます。

    Args:
        seconds (int): キャッシュの有効期間（秒）。デフォルトは1時間（3600秒）

    Returns:
        Callable: デコレータ関数

    Example:
        @timed_cache(seconds=300)  # 5分間キャッシュ
        async def fetch_data(param):
            # 重い処理やAPIリクエスト
            return result
    """

    def decorator(func: F) -> F:
        # キャッシュを保持する辞書
        # キー: 引数のハッシュ、値: (結果, タイムスタンプ)のタプル
        cache: Dict[str, Tuple[Any, float]] = {}

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 引数からキャッシュキーを生成
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()

            # キャッシュが有効かチェック
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < seconds:
                    return result

            # 関数を実行して結果をキャッシュ
            result = await func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 引数からキャッシュキーを生成
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()

            # キャッシュが有効かチェック
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < seconds:
                    return result

            # 関数を実行して結果をキャッシュ
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result

        # 非同期関数か同期関数かを判定して適切なラッパーを返す
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def invalidate_cache(func: Callable) -> None:
    """
    timed_cacheデコレータが適用された関数のキャッシュを無効化します

    Args:
        func (Callable): キャッシュを無効化する関数

    Example:
        invalidate_cache(fetch_data)  # fetch_data関数のキャッシュを無効化
    """
    if hasattr(func, "__wrapped__"):
        # デコレータが適用された関数の場合
        wrapper = func
        if hasattr(wrapper, "cache"):
            wrapper.cache.clear()  # type: ignore


class CacheManager:
    """
    複数のキャッシュを管理するためのクラス

    このクラスは、複数のキャッシュを一元管理し、
    特定のキャッシュの無効化や全キャッシュの無効化などの操作を提供します。
    """

    def __init__(self):
        self.caches: Dict[str, Dict[str, Tuple[Any, float]]] = {}

    def register_cache(self, name: str, cache_dict: Dict[str, Tuple[Any, float]]) -> None:
        """
        キャッシュを登録します

        Args:
            name (str): キャッシュの名前
            cache_dict (Dict): キャッシュを保持する辞書
        """
        self.caches[name] = cache_dict

    def invalidate(self, name: Optional[str] = None) -> None:
        """
        キャッシュを無効化します

        Args:
            name (Optional[str]): 無効化するキャッシュの名前。Noneの場合は全てのキャッシュを無効化
        """
        if name is not None:
            if name in self.caches:
                self.caches[name].clear()
        else:
            for cache_name, cache in self.caches.items():
                cache.clear()


# グローバルなキャッシュマネージャーインスタンス
cache_manager = CacheManager()
