# ADR 0001: get_db() でリクエスト単位の自動 commit / rollback を採用する

- ステータス: Accepted
- 日付: 2026-03-25
- 関連: PR #298 / Issue #297 / commit 957a524

## 背景

FastAPI の DB セッション依存 `get_db()` は、当初 SQLite 時代の実装をそのまま引き継ぎ、commit を呼ばない形になっていた。各サービス層が必要に応じて個別に `session.commit()` を呼ぶことで永続化する設計。

```python
# 本番 (変更前)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

一方、テスト側の `override_get_db` は J-Quants v2 移行時（commit `1da6370`）に自動 commit / rollback が追加されていた。

この乖離により、以下のバグが発生した:

- `stock_service` で `commit()` を忘れ `flush()` のみ呼び出していた
- テストでは `override_get_db` が自動 commit するためレスポンス・DB 状態共に正しく見え、検知できなかった
- 本番では `get_db()` がセッションを閉じるタイミングで暗黙ロールバックされ、DB に変更が反映されない

本番とテストで「誰が commit するか」の契約が異なることが、構造的にこのクラスのバグを生みやすい状態だった。

## 決定

1. `get_db()` にリクエスト単位の自動 commit / rollback を導入する。

    ```python
    async def get_db():
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    ```

2. サービス層・ルート層の `session.commit()` はすべて `session.flush()` に置き換える。commit は「リクエスト終端で 1 回」に集約する。
3. テスト側の `override_get_db` は本番と同じ形に揃える。

## 代替案

- **A. 現状維持（サービスが個別に commit）**: 明示的でわかりやすい反面、commit 忘れが常にバグ源。テストで検知できない乖離が残る。
- **B. `@transactional` デコレータや明示的なトランザクション境界を関数単位で導入**: 粒度は細かく制御できるが、10〜20 ユーザ規模のこのアプリでは過剰。YAGNI。
- **C. 今回採用した「リクエスト境界 = トランザクション境界」**: FastAPI の依存スコープと素直に一致し、追加の抽象化なしで commit 忘れを構造的に防げる。

## 影響

### 良い面

- 本番とテストで `get_db()` の挙動が揃い、commit 忘れがテストをすり抜けなくなる
- サービス層から副作用（commit）を除去でき、責務がシンプルになる
- HTTP 例外時は自動で rollback されるため、途中まで書き込まれた中途半端な状態が残らない

### 注意する面

- 1 リクエスト内で「途中まで commit して外から見えるようにする」ユースケースは取れない。現時点では該当なしだが、将来バックグラウンドタスクや別セッションからの参照が必要になれば、明示的トランザクションの導入を再検討する。
- 同一リクエスト内で複数の論理操作を行うサービス（例: `transaction_service.create_transaction` → `update_single_holding_pl`）は、途中 `flush()` で済むことを前提にしている。別セッションから呼ばれる形に変えるときは注意。
- サービスを FastAPI のリクエスト外（CLI / バッチ）から呼ぶ場合、呼び出し側でトランザクション境界を明示する必要がある。
