# ADR 0002: ruff 0.16 のデフォルトルールセットを受け入れる

- ステータス: Accepted
- 日付: 2026-08-03
- 関連: PR #425

## 背景

Dependabot の PR #425 が ruff を 0.15.22 から 0.16.0 へ更新したところ、API CI（`.github/workflows/api-ci.yml` の `ruff check`）が 413 件のエラーで失敗した。

原因は ruff 0.16.0 の破壊的変更で、デフォルトで有効な lint ルールが 59 から 413 に拡張されたことにある（https://github.com/astral-sh/ruff/releases/tag/0.16.0 ）。なお「有効ルール数 413」と「検出エラー 413 件」は数字が偶然一致しているだけで、両者に関係はない。

ただし単純な「全部盛り」ではない。同時に、意見が割れる次の 18 ルールはデフォルトから外されている。

```text
E401 E402 E701 E702 E703 E711 E712 E713 E714
E721 E731 E741 E742 E743 F403 F405 F406 F722
```

Astral 側が「実績があり異論の少ないものを標準にする」という方針に転換した結果であり、拡張と削減はセットで行われている。

一方このリポジトリの `src/api/pyproject.toml` の `[tool.ruff]` は `line-length = 110` しか設定しておらず、ルール選択を上流のデフォルトに委ねていた。そのため 0.16 の方針転換をそのまま被った形になる。

検出されたエラーの内訳は以下のとおり。

| ルール | 件数 | 判断 |
| --- | --- | --- |
| UP006 / UP045 / UP007 / UP035 / UP043 / UP012 / UP017 | 287 | 採用（全自動修正可） |
| B008 | 46 | 設定を入れた上で採用 |
| DTZ001 / DTZ011 | 23 | 採用（テストのみ除外） |
| BLE001 | 15 | 除外 |
| I001 | 14 | 採用 |
| TRY002 | 7 | 除外（別途対応） |
| その他小粒（PIE790 / RUF010 / RUF022 / FURB188 / PERF102 / PIE810 / PLR1722 / RUF012 / RUF059 / SIM117） | 21 | 採用（一部は手動修正） |

## 決定

0.16 のデフォルトルールセットを基本的に受け入れ、プロジェクト固有の事情があるものだけを設定で調整する。ルールごとの判断は次のとおり。

1. **UP 系（型記法のモダナイズ）: 採用**

    `List[int]` → `list[int]`、`Optional[X]` → `X | None`、`typing.Sequence` → `collections.abc.Sequence` への書き換え。`src/api/pyproject.toml` の `requires-python = ">=3.13"` である以上、旧記法を残す技術的理由がない。

    このうち 49 件は `alembic/versions/` 配下だが、出所は `src/api/alembic/script.py.mako` の以下のテンプレートである。

    ```python
    from typing import Sequence, Union
    ```

    テンプレートを直さないと新規マイグレーションを生成するたびに再発するため、テンプレート側も修正した。

2. **B008 (function-call-in-default-argument): 設定を入れた上で有効のまま維持**

    46 件すべてが FastAPI の `Depends()` で、公式パターンに対する誤検知。ただしルール本体（可変オブジェクトをデフォルト引数に置くバグの検出）には価値があるため、`[tool.ruff.lint.flake8-bugbear]` の `extend-immutable-calls` に `fastapi.Depends` 等を登録し、ルールを無効化せずに 0 件にした。

3. **DTZ001 / DTZ011: 採用（`tests/**` のみ除外）**

    本番コードのヒットは `src/api/stock/services/price_history_repo.py` の 2 箇所（`get_recent_prices` と `prune_old_prices` の `date.today()`）のみ。同ファイルは `get_jst_now` を import しているにもかかわらず `date.today()` を使っており、サーバーのローカル TZ に依存する。本番コンテナが UTC なら JST 00:00〜09:00 の間は日付が 1 日前になり、直近 N 日の株価取得と古いデータ削除の境界がずれる。**DTZ を有効化したことで実バグが 1 件見つかった**ことは、今回の判断の重要な根拠である。

    ただし修正は挙動変更を伴うため本 PR には含めず、当該 2 箇所に `# noqa: DTZ011` と TODO コメントを置いて別 PR に切り出す。lint 設定変更のついでに挙動が変わると追跡が困難になるため。

    テスト側 21 件は naive datetime を意図的に生成しているもので（`tests/test_datetime_conversion.py` は naive → JST 変換の検証そのもの）、`per-file-ignores` で `tests/**` を除外する。

4. **BLE001 (blind-except): 除外**

    15 件すべてが「外部 API 呼び出しやバッチのユーザー単位処理を catch して `logger.warning` / `logger.exception` する」意図的な境界処理（`stock/jobs/_runner.py`、`stock/services/holding_service.py`、`stock/routes/transactions.py` など）。ruff はログ出力の有無を判定しないため、このプロジェクトでは恒常的にノイズになる。

5. **TRY002 (raise-vanilla-class): 除外（保留。別途対応する）**

    `raise Exception("...")` が `stock/services/alphavantage_service.py`、`jquants_service.py`、`price_history_service.py` にある。呼び出し側が例外を選別できないという実害はあり指摘自体は正当だが、修正にはカスタム例外クラスの設計が必要で、lint 対応 PR の範囲を超える。いったん除外するが、これは「無視してよいルール」ではなく保留状態である。

6. **I001 およびその他小粒ルール: 採用**

    I001（import 順）は formatter が並べ替えを行わないため、これまで担保されていなかった。その他 21 件は自動修正または軽微な手直しで解消できる粒度であり、除外する理由がない。

## 代替案

- **A. 旧デフォルト相当に pin する（`[tool.ruff.lint] select = ["E4","E7","E9","F"]`）**: 差分は最小で CI もすぐ緑になる。ローカル検証で ruff 0.16.0 に `--select E4,E7,E9,F` を与えると `All checks passed!` になることは確認済み。しかし上流が「実績あるルールを標準化する」方向に舵を切った意図を捨てることになり、次のバージョンでも同じ先送りを繰り返す。今回それによって実バグ（DTZ）が 1 件見つかっている以上、得られるものを捨てる判断になる。
- **B. ruff 0.15.22 のまま、別 PR でカテゴリ select による lint 対応を済ませてから #425 を通す**: 依存更新 PR と大規模リファクタを分離できる点は魅力。しかし `--select E4,E7,E9,F,UP,I,B,DTZ,PIE,PERF,SIM,RUF,FURB,PLR,TRY,BLE` で検証したところ 1405 件に膨れ、0.16 のデフォルト集合はカテゴリ単位では再現できないことが判明した（0.16 のデフォルトはカテゴリ内の一部ルールを選んでいるため）。技術的に不可能。
- **C. 今回採用した「0.16 のデフォルトを基本的に受け入れ、プロジェクト固有の事情があるものだけ設定で調整する」**: 上流のキュレーションを信頼し、`extend-immutable-calls`（FastAPI）、`per-file-ignores`（tests の DTZ）、`ignore`（BLE001 / TRY002）の 3 点だけを明示する。以後 ruff がデフォルトを変えたときも「追随を基本とし、差分だけ検討する」という同じ手順で判断できる。

## 影響

### 良い面

- 型記法が Python 3.13 前提に統一され、import 順も機械的に保証される
- DTZ の有効化により、JST / UTC のずれという、株価・取引日を扱うこのアプリのドメインにとって致命的なクラスのバグを継続的に検出できる。実際に今回 1 件検出している
- `script.py.mako` を直したことで、新規マイグレーション生成のたびに同じ指摘が再発することがなくなる
- ルール選択の意図が `pyproject.toml` と本 ADR に明文化され、「なぜこのルールが off なのか」を後から追える
- 今後 ruff のデフォルトが変わっても「追随を基本とし、差分だけ検討する」という判断基準が定まった

### 注意する面

- 一括修正により 60 ファイル・633 行（+317 / -316）が変更され、git blame が一段汚れる。うち 360 件は `ruff check --fix` による自動修正、9 件が手動修正。本 ADR と PR #425 がその参照先になる。
- `BLE001` / `TRY002` の除外は恒久的な是認ではない。特に `TRY002` はカスタム例外の設計が済んだ時点で再有効化を検討する。
- `extend-immutable-calls` のリストは FastAPI の API 面に依存する。新しい依存性注入ヘルパーを使い始めたら追記が必要。
- `price_history_repo.py` の `# noqa` は別 PR での修正が済むまでの一時的なもので、放置すると DTZ を有効化した意味が薄れる。
- ruff のバージョンは `src/api/uv.lock` を唯一の情報源とし、`.pre-commit-config.yaml` の `rev` も合わせて更新する運用を継続する（`.github/workflows/api-ci.yml` のコメント参照）。
