# CD 移行手順 (Cloud Build → GitHub Actions)

このドキュメントは、Cloud Run のデプロイを Cloud Build から GitHub Actions に切り替える **一回限り** の作業手順です。完了したら削除してかまいません。

> 関連する変更内容は本ブランチ `claude/cd-pipeline-discussion-IVJIE` のコミットを参照。

## 前提

- `gcloud` 認証済み (`gcloud auth login` + `gcloud auth application-default login` の両方)
- `tofu` インストール済み
- `infra/.env` と `infra/backend.hcl` が手元にある
- 本ブランチが GitHub に push 済み（既に push 済）

---

## Phase A — インフラ反映

### A-1. `infra/.env` に変数を追記

```bash
echo 'TF_VAR_github_repository="Tomodo1773/InvestLogix"' >> infra/.env
```

### A-2. 環境変数を読み込む

```bash
cd infra
set -a; source .env; set +a
```

### A-3. 既存 Artifact Registry リポを state に取り込む

Cloud Build が自動生成した `cloud-run-source-deploy` リポを OpenTofu 管理下に入れる:

```bash
tofu import google_artifact_registry_repository.api \
  projects/$TF_VAR_project_id/locations/asia-northeast1/repositories/cloud-run-source-deploy
```

> `region` と `artifact_registry_repo_id` は `variables.tf` の default を使う前提で `.env` に書かない運用なので、import の ID にはリテラルで埋める。
>
> 既に import 済みなら "Resource already managed" エラーになるので、その場合はスキップ。

### A-4. plan で差分確認

```bash
tofu plan
```

期待する差分:

- ✅ **新規作成**: `google_iam_workload_identity_pool.github`, `google_iam_workload_identity_pool_provider.github`, `google_service_account.deployer`, `google_project_iam_member.deployer["roles/..."]` × 3, `google_service_account_iam_member.deployer_wif`
- ✅ **変更なし or in-place**: `google_artifact_registry_repository.api` (description だけ差分が出ても OK)
- ❌ **destroy がある場合は中止**してログを確認

### A-5. apply

```bash
tofu apply
# yes と入力
```

### A-6. output を確認

```bash
tofu output -raw wif_provider       # 例: projects/123456789/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider
tofu output -raw deployer_sa_email  # 例: investlogix-deployer@<project>.iam.gserviceaccount.com
tofu output -raw image_base         # 例: asia-northeast1-docker.pkg.dev/<project>/cloud-run-source-deploy/investlogix/investlogix-api
```

3 つの値をメモしておく（次のフェーズで GitHub に登録）。

---

## Phase B — GitHub Actions Variables 登録

GitHub の **Settings → Secrets and variables → Actions → Variables タブ → New repository variable** で以下 5 つを登録する。

| Name | 値の取得元 |
|---|---|
| `WIF_PROVIDER` | `tofu output -raw wif_provider` |
| `DEPLOYER_SA` | `tofu output -raw deployer_sa_email` |
| `IMAGE_BASE` | `tofu output -raw image_base` |
| `GCP_REGION` | リテラル `asia-northeast1` |
| `SERVICE_NAME` | リテラル `investlogix-api` |

> **Secrets ではなく Variables** に登録する。これらは秘密ではなく識別子で、ログに出ても問題ない（プロジェクト ID 程度）。

`gh` CLI が手元にあるなら一括登録も可:

```bash
gh variable set WIF_PROVIDER --body "$(tofu output -raw wif_provider)"
gh variable set DEPLOYER_SA  --body "$(tofu output -raw deployer_sa_email)"
gh variable set IMAGE_BASE   --body "$(tofu output -raw image_base)"
gh variable set GCP_REGION   --body "asia-northeast1"
gh variable set SERVICE_NAME --body "investlogix-api"
```

---

## Phase C — ワークフロー試走

### C-1. workflow_dispatch でブランチから手動実行

GitHub UI: **Actions → API CD (Cloud Run) → Run workflow → Branch: `claude/cd-pipeline-discussion-IVJIE` → Run**

または `gh` で:

```bash
gh workflow run api-cd.yml --ref claude/cd-pipeline-discussion-IVJIE
gh run watch
```

### C-2. 各ステップの成功を確認

特に注目するもの:

- `google-github-actions/auth` で WIF 認証が通る（403 が出たら Phase A の attribute_condition / WIF 設定を見直す）
- `Build & push image` で AR への push が通る（権限不足なら deployer に `artifactregistry.writer` が付いているか確認）
- `Deploy Cloud Run Service & Jobs` が完走
- `Verify image SHA` で Service と 3 Jobs すべて `OK` と表示される

### C-3. Cloud Run コンソールで実物確認

```bash
gcloud run services describe investlogix-api --region=asia-northeast1 \
  --format='value(spec.template.spec.containers[0].image)'
# → asia-northeast1-docker.pkg.dev/.../investlogix-api:<commit-sha> が新しい SHA になっているか
```

3 Jobs についても:

```bash
for job in recalc-holdings update-and-notify notify-weekly-performance; do
  printf '%-30s %s\n' "$job" "$(gcloud run jobs describe "$job" --region=asia-northeast1 \
    --format='value(spec.template.spec.template.spec.containers[0].image)')"
done
```

### C-4. main にマージ

PR を出して main にマージ。マージで `api-cd.yml` の `push` トリガーが起動するので、もう一度 Phase C-2 / C-3 を確認する。

---

## Phase D — Cloud Build トリガー無効化

api-cd.yml が main で正常稼働していることを確認したら、旧 CD 経路を止める。

### D-1. トリガー一覧

```bash
gcloud builds triggers list --project=$TF_VAR_project_id \
  --format='table(name,github.name,github.push.branch,disabled)'
```

`investlogix` 系で main を対象にしているトリガーを特定。

### D-2. 無効化（削除ではなく disable）

```bash
gcloud builds triggers update <TRIGGER_ID> --disable --project=$TF_VAR_project_id
```

> いきなり削除しない。数日 GitHub Actions だけで運用して問題が出ないことを確認してから、最終的に `gcloud builds triggers delete <TRIGGER_ID>` で削除。

### D-3. このドキュメントを削除

```bash
git rm infra/cd-migration.md
git commit -m "chore: remove one-shot CD migration doc"
```

---

## トラブルシュート

| 症状 | 対応 |
|---|---|
| `auth@v3` で `Permission denied` / `unauthorized_client` | WIF の `attribute_condition` が一致しているか。`assertion.repository == "Tomodo1773/InvestLogix"` と完全一致が必要 |
| `docker push` が `denied: permission_denied` | deployer SA に `roles/artifactregistry.writer` が付いているか。`gcloud projects get-iam-policy` で確認 |
| `gcloud run deploy` が `iam.serviceAccounts.actAs` で失敗 | deployer SA に `roles/iam.serviceAccountUser` が付いているか |
| `tofu import` で `Resource already managed` | 既に import 済み。次のステップへ |
| `tofu plan` で `cloud-run-source-deploy` が destroy & create になる | location や format がデフォルトと違う可能性。`tofu state show google_artifact_registry_repository.api` で実体を確認 |
| 試走でデプロイは成功するが image SHA が古いまま | Cloud Build トリガーがまだ有効で同時にデプロイしている。Phase D-2 を先に実施 |

## ロールバック

GitHub Actions 経路に問題があった場合:

1. Cloud Build トリガーを再有効化: `gcloud builds triggers update <ID> --no-disable`
2. `api-cd.yml` を一時的に無効化: ファイルをリネームか削除して main に push
3. `tofu destroy -target=<resource>` で WIF/deployer を消すのは原則不要（残っていても害はない）
