#!/usr/bin/env bash
# main にマージ直後、Cloud Run Jobs のイメージを最新へ揃えるスクリプト。
# Cloud Build の完了待ちと、更新後の SHA verify までセットで行う。
#
# 使い方:
#   cd infra && set -a; source .env; set +a && cd ..   # TF_VAR_project_id を読み込む
#   scripts/update-cloud-run-jobs.sh                   # origin/main の最新 SHA を使う
#   scripts/update-cloud-run-jobs.sh <SHA>             # 特定の SHA を指定（ロールバック等）

set -euo pipefail

PROJECT_ID="${TF_VAR_project_id:?Set TF_VAR_project_id (e.g. 'cd infra && set -a; source .env; set +a')}"
REGION="${TF_VAR_region:-asia-northeast1}"
IMAGE_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/investlogix/investlogix-api"
JOBS=(recalc-holdings update-and-notify notify-weekly-performance)
WAIT_TIMEOUT_SEC=600
WAIT_INTERVAL_SEC=15

# 1) ターゲット SHA を決める
if [ "$#" -ge 1 ]; then
  TARGET_SHA="$1"
else
  echo ">> git fetch origin main"
  git fetch --quiet origin main
  TARGET_SHA="$(git rev-parse origin/main)"
fi

IMAGE_URI="${IMAGE_REPO}:${TARGET_SHA}"
echo ">> Target image: ${IMAGE_URI}"

# 2) 該当 SHA の Cloud Build が SUCCESS になるまで待つ
echo ">> Wait for Cloud Build of ${TARGET_SHA:0:8}..."
elapsed=0
while :; do
  status="$(gcloud builds list \
    --project="${PROJECT_ID}" \
    --filter="images:${IMAGE_URI}" \
    --format='value(status)' --limit=1 2>/dev/null || true)"

  case "${status}" in
    SUCCESS)
      echo "   build SUCCESS"
      break
      ;;
    FAILURE|CANCELLED|TIMEOUT|EXPIRED)
      echo "   build ${status} -- abort" >&2
      exit 1
      ;;
    "")
      echo "   build not found yet (waited ${elapsed}s)"
      ;;
    *)
      echo "   build ${status} (waited ${elapsed}s)"
      ;;
  esac

  if [ "${elapsed}" -ge "${WAIT_TIMEOUT_SEC}" ]; then
    echo "   timeout after ${WAIT_TIMEOUT_SEC}s" >&2
    exit 1
  fi
  sleep "${WAIT_INTERVAL_SEC}"
  elapsed=$((elapsed + WAIT_INTERVAL_SEC))
done

# 3) 各 Job を新イメージへ更新
for job in "${JOBS[@]}"; do
  echo ">> Update ${job}"
  gcloud run jobs update "${job}" \
    --project="${PROJECT_ID}" --region="${REGION}" \
    --image="${IMAGE_URI}" >/dev/null
done

# 4) 更新後の verify (gcloud のコマンド成功表示はアテにならないため必ず実 SHA を確認する)
echo ">> Verify"
fail=0
for job in "${JOBS[@]}"; do
  current="$(gcloud run jobs describe "${job}" \
    --project="${PROJECT_ID}" --region="${REGION}" \
    --format='value(spec.template.spec.template.spec.containers[0].image)')"
  if [ "${current}" = "${IMAGE_URI}" ]; then
    echo "   OK  ${job}  -> ${TARGET_SHA:0:8}"
  else
    echo "   NG  ${job}  -> ${current##*:}"
    fail=1
  fi
done

exit "${fail}"
