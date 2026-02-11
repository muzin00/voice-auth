# GCP Cloud Runへのデプロイ

## GitHub Actions CI/CD セットアップ

GitHub Actionsを使ったCI/CDパイプラインを利用する場合は、以下の設定が必要です。

### 1. Workload Identity Federation セットアップ

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export GITHUB_ORG="your-github-org"  # GitHubのユーザー名またはOrg名
export GITHUB_REPO="voice-auth"      # リポジトリ名

# Workload Identity Pool 作成
gcloud iam workload-identity-pools create "github-pool" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# OIDC Provider 作成
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# サービスアカウント作成
gcloud iam service-accounts create "github-actions" \
  --project="$PROJECT_ID" \
  --display-name="GitHub Actions"

# 必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Workload Identityとサービスアカウントをバインド
gcloud iam service-accounts add-iam-policy-binding \
  "github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"
```

### 2. Artifact Registry リポジトリ作成

```bash
gcloud artifacts repositories create voiceauth \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="VoiceAuth container images"
```

### 3. GitHub Secrets/Variables 設定

GitHubリポジトリの Settings > Secrets and variables > Actions で以下を設定:

**Secrets:**
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: `projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- `GCP_SERVICE_ACCOUNT`: `github-actions@${PROJECT_ID}.iam.gserviceaccount.com`

**Variables:**
- `GCP_PROJECT_ID`: プロジェクトID
- `GCP_REGION`: `asia-northeast1`

---

## 前提条件

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
  インストール済み
- `gcloud auth login` で認証完了

> **Note**: デプロイは GitHub Actions による CI/CD で自動化されています。
> 以下の初回セットアップのみ手動で実行してください。

---

## 初回セットアップ

> **SQLite + GCS マウント構成**
>
> GCSマウント上のSQLiteでデータを永続化します。
> 維持費はほぼ0円ですが、スケーリングには制約があります。
>
> - `max-instances=1` 必須（複数インスタンス不可）
> - 同時リクエスト数が制限される
> - GCS FUSEはSQLiteの公式サポート外のため、自己責任での運用

### 1. プロジェクト作成とAPI有効化

```bash
# プロジェクト作成
gcloud projects create YOUR_PROJECT_ID --name="VoiceAuth Server"
gcloud config set project YOUR_PROJECT_ID

# 課金アカウント紐付け
gcloud billing accounts list
gcloud billing projects link YOUR_PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

# API有効化
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com
```

### 2. 環境変数設定

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast1
# 音声ファイル用バケット
export BUCKET_NAME="${PROJECT_ID}-voiceauth-voices"
# SQLite DB保存用バケット
export DB_BUCKET_NAME="${PROJECT_ID}-voiceauth-db"
```

### 3. GCS バケット セットアップ

```bash
# 音声用バケット
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME/

# DB用バケット
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$DB_BUCKET_NAME/
```

### 4. サービスアカウントへの権限付与

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# ストレージオブジェクトの読み書き権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"
```

### 5. コンテナイメージビルド

```bash
# 初回イメージビルド（まだ公開しない）
gcloud run deploy voiceauth-server \
  --source . \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated

# イメージURL取得
IMAGE_URL=$(gcloud run services describe voiceauth-server \
  --region=$REGION \
  --format="value(spec.template.spec.containers[0].image)")
```

### 6. マイグレーション用 Cloud Run Job 作成

```bash
gcloud run jobs create migration-upgrade-sqlite \
  --image=$IMAGE_URL \
  --region=$REGION \
  --command="sh" \
  --args="-c,cd /app && uv run alembic upgrade head" \
  --add-volume="name=db-volume,type=cloud-storage,bucket=$DB_BUCKET_NAME" \
  --add-volume-mount="volume=db-volume,mount-path=/app/db" \
  --set-env-vars="DB_SQLITE_PATH=/app/db/voiceauth.db" \
  --max-retries=0 \
  --task-timeout=300
```

### 7. マイグレーション実行

```bash
gcloud run jobs execute migration-upgrade-sqlite \
  --region=$REGION \
  --wait
```

### 8. Cloud Run デプロイ（外部公開）

> **重要**: `max-instances=1`
> でインスタンス数を制限し、SQLiteへの同時書き込みを防止します。

```bash
gcloud run deploy voiceauth-server \
  --image=$IMAGE_URL \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --execution-environment=gen2 \
  --add-volume="name=db-volume,type=cloud-storage,bucket=$DB_BUCKET_NAME" \
  --add-volume-mount="volume=db-volume,mount-path=/app/db" \
  --set-env-vars="DB_SQLITE_PATH=/app/db/voiceauth.db,STORAGE_TYPE=gcs,GCS_BUCKET_NAME=$BUCKET_NAME,GCS_PROJECT_ID=$PROJECT_ID" \
  --max-instances=1 \
  --memory=4Gi \
  --cpu-boost \
  --cpu=2 \
  --timeout=300
```

---

## 便利なコマンド

### ログ確認

```bash
# サービスログ
gcloud run services logs read voiceauth-server --region asia-northeast1 --limit=50

# マイグレーションログ
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=migration-upgrade-sqlite" \
  --limit=50 \
  --format="value(textPayload)"
```

### サービス情報

```bash
# サービス詳細
gcloud run services describe voiceauth-server --region asia-northeast1

# サービスURL取得
gcloud run services describe voiceauth-server \
  --region asia-northeast1 \
  --format="value(status.url)"
```

### マイグレーション管理

#### マイグレーションJob一覧

- **migration-upgrade-sqlite**: 最新状態にマイグレーション (`alembic upgrade head`)
- **migration-downgrade-sqlite**: 1ステップ戻す (`alembic downgrade -1`)
- **migration-reset-sqlite**: すべてリセット (`alembic downgrade base`)

#### 使い方

```bash
# 最新にアップグレード
gcloud run jobs execute migration-upgrade-sqlite --region asia-northeast1 --wait

# 1ステップ戻す（本番環境で慎重にロールバック）
gcloud run jobs execute migration-downgrade-sqlite --region asia-northeast1 --wait

# すべてリセット（開発環境のみ）
gcloud run jobs execute migration-reset-sqlite --region asia-northeast1 --wait

# リセット後、最新に戻す
gcloud run jobs execute migration-reset-sqlite --region asia-northeast1 --wait
gcloud run jobs execute migration-upgrade-sqlite --region asia-northeast1 --wait
```

### Artifact Registryクリーンアップ

コンテナイメージが溜まるのを防ぐため、クリーンアップポリシーを設定します。

```bash
# クリーンアップポリシーを適用（最新2つのイメージを保持）
gcloud artifacts repositories set-cleanup-policies cloud-run-source-deploy \
    --project=YOUR_PROJECT_ID \
    --location=asia-northeast1 \
    --policy=deployment/artifact-registry-cleanup-policy.json
```

**設定内容** (`artifact-registry-cleanup-policy.json`):

- 最新2つのイメージバージョンを保持
- それ以外の古いイメージを自動削除

**効果**:

- Whisperモデルを含むイメージは1つで2-4GB程度
- 20個のイメージがある場合、約40-80GBのストレージを削減可能
- 月額コスト削減: 約$4-8/月（$0.10/GB/月として計算）

> クリーンアップポリシーは自動的に実行されます。現在Cloud Runで稼働中のリビジョンのイメージは削除されません。

### トラブルシューティング

```bash
# サービスを以前のリビジョンにロールバック
gcloud run services update-traffic voiceauth-server \
  --to-revisions=REVISION_NAME=100 \
  --region asia-northeast1
```

---

## アーキテクチャ

- **API**: Cloud Run (FastAPI)
- **Database**: SQLite on GCS FUSE
- **Storage**: GCS (音声ファイル + DBファイル)
- **Container Registry**: Artifact Registry (自動クリーンアップ有効)
- **Migrations**: Cloud Run Jobs (Alembic)
- **CI/CD**: GitHub Actions

## コスト概算（東京リージョン）

| サービス  |                       月額コスト |
| --------- | -------------------------------: |
| Cloud Run |           従量課金（無料枠あり） |
| GCS       | ほぼ無料（数GB以下なら無料枠内） |
| **合計**  |                       **~$0/月** |

> 個人利用の低トラフィック環境では、GCPの無料枠内で運用可能です。
