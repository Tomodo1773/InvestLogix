# Cloud Run Jobs セットアップ手順

定期実行を GAS から Cloud Run Jobs + Cloud Scheduler に移行するための手順。セットアップが終わったらこのファイルは削除してよい。

## 前提

- バックエンドは Cloud Run サービスとして稼働中（Dockerfile 自動デプロイ）
- 同じ Docker イメージをジョブでも流用する（ENTRYPOINT は Cloud Run Jobs 側で上書き）
- 対象ジョブは3つ

| ジョブ名 | モジュール | スケジュール |
|---|---|---|
| `recalc-holdings` | `stock.jobs.recalc_holdings` | 日次 |
| `update-and-notify` | `stock.jobs.update_and_notify` | 週次 |
| `notify-weekly-performance` | `stock.jobs.notify_weekly_performance` | 週次 |

## 環境変数

Cloud Run サービスで設定している環境変数・Secret をジョブにも同じ値で設定する。最低限必要:

- `DATABASE_URL`（Cloud SQL 接続）
- `LINE_CHANNEL_ACCESS_TOKEN`
- `JQUANTS_API_KEY`
- `ALPHAVANTAGE_API_KEY`
- `OPENAI_API_KEY`

Secret Manager を使っている値は `--set-secrets` で引き継ぐ。

## 1. Cloud Run Jobs の作成

既存の Cloud Run サービスのイメージ URI を確認して `IMAGE_URI` に入れる。

```bash
PROJECT_ID=<your-project-id>
REGION=<your-region>  # 例: asia-northeast1
IMAGE_URI=<services-region>-docker.pkg.dev/${PROJECT_ID}/<repo>/<image>:<tag>
SA=<cloud-run-service-account>@${PROJECT_ID}.iam.gserviceaccount.com

# ジョブの共通作成関数（Cloud SQL 接続・Secret などは既存サービスに合わせる）
create_job() {
  local name=$1
  local module=$2
  gcloud run jobs create "${name}" \
    --image="${IMAGE_URI}" \
    --region="${REGION}" \
    --service-account="${SA}" \
    --command="python" \
    --args="-m,${module}" \
    --set-cloudsql-instances="<cloud-sql-instance>" \
    --set-secrets="LINE_CHANNEL_ACCESS_TOKEN=line-token:latest,JQUANTS_API_KEY=jquants:latest,ALPHAVANTAGE_API_KEY=alphavantage:latest,OPENAI_API_KEY=openai:latest" \
    --set-env-vars="DATABASE_URL=<...>" \
    --task-timeout="30m" \
    --max-retries=1
}

create_job recalc-holdings stock.jobs.recalc_holdings
create_job update-and-notify stock.jobs.update_and_notify
create_job notify-weekly-performance stock.jobs.notify_weekly_performance
```

## 2. 手動実行で動作確認

```bash
gcloud run jobs execute recalc-holdings --region="${REGION}" --wait
gcloud run jobs execute update-and-notify --region="${REGION}" --wait
gcloud run jobs execute notify-weekly-performance --region="${REGION}" --wait
```

Cloud Logging で `job=<name>` タグ付きログが出ていること、終了コード0で完了していることを確認する。

## 3. Cloud Scheduler の設定

Cloud Run Jobs は Cloud Scheduler から HTTP ターゲットで起動する。認証用のサービスアカウントには `roles/run.invoker` を付与しておく。

```bash
SCHEDULER_SA=<scheduler-sa>@${PROJECT_ID}.iam.gserviceaccount.com
JOB_URI_PREFIX="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs"

# 日次ジョブ（例: 毎日 18:00 JST）
gcloud scheduler jobs create http recalc-holdings-daily \
  --location="${REGION}" \
  --schedule="0 18 * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="${JOB_URI_PREFIX}/recalc-holdings:run" \
  --http-method=POST \
  --oauth-service-account-email="${SCHEDULER_SA}"

# 週次ジョブ（例: 毎週金曜 18:30 JST）
gcloud scheduler jobs create http update-and-notify-weekly \
  --location="${REGION}" \
  --schedule="30 18 * * 5" \
  --time-zone="Asia/Tokyo" \
  --uri="${JOB_URI_PREFIX}/update-and-notify:run" \
  --http-method=POST \
  --oauth-service-account-email="${SCHEDULER_SA}"

gcloud scheduler jobs create http notify-weekly-performance-weekly \
  --location="${REGION}" \
  --schedule="0 19 * * 5" \
  --time-zone="Asia/Tokyo" \
  --uri="${JOB_URI_PREFIX}/notify-weekly-performance:run" \
  --http-method=POST \
  --oauth-service-account-email="${SCHEDULER_SA}"
```

スケジュールは既存 GAS のトリガ時刻に合わせて調整する。

## 4. GAS 側のトリガ停止

Cloud Scheduler で翌日・翌週の自動起動を目視確認できたら、GAS 側の既存トリガを削除する。既存 HTTP エンドポイント（`/api/v1/holdings/recalculate-all` 等）は手動再実行用に残してある。

## 5. イメージ更新時

Cloud Run サービスの自動デプロイでイメージが更新されても、Cloud Run Jobs のイメージは自動では追従しない。新しいタグを参照するよう以下で更新する:

```bash
gcloud run jobs update recalc-holdings --image="${IMAGE_URI}" --region="${REGION}"
gcloud run jobs update update-and-notify --image="${IMAGE_URI}" --region="${REGION}"
gcloud run jobs update notify-weekly-performance --image="${IMAGE_URI}" --region="${REGION}"
```

必要であれば Cloud Build などのデプロイパイプラインに同コマンドを組み込む。
