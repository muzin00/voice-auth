# VCA Server

## GCP Cloud Runへのデプロイ

### 前提条件

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) インストール済み
- `gcloud auth login` で認証完了

---

## 初回セットアップ

### 1. プロジェクト作成とAPI有効化

```bash
# プロジェクト作成
gcloud projects create YOUR_PROJECT_ID --name="VCA Server"
gcloud config set project YOUR_PROJECT_ID

# 課金アカウント紐付け
gcloud billing accounts list
gcloud billing projects link YOUR_PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

# API有効化
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com
```

### 2. 環境変数設定

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast1
export INSTANCE_NAME=vca-postgres
export DB_NAME=vca_db
export DB_USER=vca_user
export ROOT_PASSWORD="<SECURE_ROOT_PASSWORD>"
export DB_PASSWORD="<SECURE_DB_PASSWORD>"
export BUCKET_NAME="${PROJECT_ID}-vca-voices"
```

### 3. GCS バケット セットアップ

```bash
# バケット作成
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME/

# ライフサイクルルール設定（90日後に削除）
cat > /tmp/lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["voices/"]
        }
      }
    ]
  }
}
EOF
gsutil lifecycle set /tmp/lifecycle.json gs://$BUCKET_NAME/

# CORS設定
cat > /tmp/cors.json << 'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF
gsutil cors set /tmp/cors.json gs://$BUCKET_NAME/
```

### 4. Cloud SQL セットアップ

```bash
# インスタンス作成（5-10分）
gcloud sql instances create $INSTANCE_NAME \
  --database-version=POSTGRES_16 \
  --edition=ENTERPRISE \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password="$ROOT_PASSWORD"

# データベースとユーザー作成
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME
gcloud sql users create $DB_USER \
  --instance=$INSTANCE_NAME \
  --password="$DB_PASSWORD"

# 接続名を取得
export CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)")
echo "Connection Name: $CONNECTION_NAME"
```

### 4. Secret Manager セットアップ

```bash
# パスワードをSecretに保存
echo -n "$DB_PASSWORD" | gcloud secrets create vca-db-password \
  --data-file=- \
  --replication-policy="automatic"

# IAM権限設定
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding vca-db-password \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### 5. コンテナイメージビルド

```bash
# 初回イメージビルド（まだ公開しない）
gcloud run deploy vca-server \
  --source . \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated

# イメージURL取得
IMAGE_URL=$(gcloud run services describe vca-server \
  --region=$REGION \
  --format="value(spec.template.spec.containers[0].image)")
```

### 6. マイグレーション用 Cloud Run Job 作成

```bash
gcloud run jobs create migration-upgrade \
  --image=$IMAGE_URL \
  --region=$REGION \
  --command="sh" \
  --args="-c,cd /app && uv run alembic upgrade head" \
  --update-env-vars="POSTGRES_SERVER=/cloudsql/$CONNECTION_NAME,POSTGRES_PORT=5432,POSTGRES_USER=$DB_USER,POSTGRES_DB=$DB_NAME" \
  --set-secrets="POSTGRES_PASSWORD=vca-db-password:latest" \
  --set-cloudsql-instances=$CONNECTION_NAME \
  --max-retries=0 \
  --task-timeout=300
```

### 7. マイグレーション実行

```bash
gcloud run jobs execute migration-upgrade \
  --region=$REGION \
  --wait
```

### 8. Cloud Run デプロイ（外部公開）

```bash
gcloud run deploy vca-server \
  --image=$IMAGE_URL \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="POSTGRES_SERVER=/cloudsql/$CONNECTION_NAME,POSTGRES_PORT=5432,POSTGRES_USER=$DB_USER,POSTGRES_DB=$DB_NAME,STORAGE_TYPE=gcs,GCS_BUCKET_NAME=$BUCKET_NAME,GCS_PROJECT_ID=$PROJECT_ID" \
  --set-secrets="POSTGRES_PASSWORD=vca-db-password:latest" \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300
```

---

## 再デプロイ（コード変更後）

### 環境変数再設定

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast1
export INSTANCE_NAME=vca-postgres
export CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)")
```

### デプロイ手順

```bash
# 1. 新しいイメージをビルド（トラフィックはまだ流さない）
gcloud run deploy vca-server \
  --source . \
  --region=$REGION \
  --no-traffic

# 2. イメージURL取得
IMAGE_URL=$(gcloud run services describe vca-server \
  --region=$REGION \
  --format="value(spec.template.spec.containers[0].image)")

# 3. マイグレーションJob更新
gcloud run jobs update migration-upgrade \
  --image=$IMAGE_URL \
  --region=$REGION

# 4. マイグレーション実行
gcloud run jobs execute migration-upgrade \
  --region=$REGION \
  --wait

# 5. トラフィックを新リビジョンに切り替え
gcloud run services update-traffic vca-server \
  --to-latest \
  --region=$REGION
```

---

## 便利なコマンド

### ログ確認

```bash
# サービスログ
gcloud run logs read vca-server --region asia-northeast1 --limit=50

# マイグレーションログ
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=migration-upgrade" \
  --limit=50 \
  --format="value(textPayload)"

# リアルタイムログ
gcloud run logs tail vca-server --region asia-northeast1
```

### サービス情報

```bash
# サービス詳細
gcloud run services describe vca-server --region asia-northeast1

# サービスURL取得
gcloud run services describe vca-server \
  --region asia-northeast1 \
  --format="value(status.url)"
```

### データベース操作

```bash
# Cloud SQLに接続
gcloud sql connect vca-postgres --user=vca_user --database=vca_db

# バックアップ作成
gcloud sql backups create --instance=vca-postgres
```

### マイグレーション管理

#### マイグレーションJob一覧

- **migration-upgrade**: 最新状態にマイグレーション (`alembic upgrade head`)
- **migration-downgrade**: 1ステップ戻す (`alembic downgrade -1`)
- **migration-reset**: すべてリセット (`alembic downgrade base`)

#### 使い方

```bash
# 最新にアップグレード
gcloud run jobs execute migration-upgrade --region asia-northeast1 --wait

# 1ステップ戻す（本番環境で慎重にロールバック）
gcloud run jobs execute migration-downgrade --region asia-northeast1 --wait

# すべてリセット（開発環境のみ）
gcloud run jobs execute migration-reset --region asia-northeast1 --wait

# リセット後、最新に戻す
gcloud run jobs execute migration-reset --region asia-northeast1 --wait
gcloud run jobs execute migration-upgrade --region asia-northeast1 --wait
```

### トラブルシューティング

```bash
# サービスを以前のリビジョンにロールバック
gcloud run services update-traffic vca-server \
  --to-revisions=REVISION_NAME=100 \
  --region asia-northeast1
```

---

## アーキテクチャ

- **API**: Cloud Run (FastAPI)
- **Database**: Cloud SQL (PostgreSQL 16)
- **Secrets**: Secret Manager
- **Migrations**: Cloud Run Jobs (Alembic)

## コスト概算（東京リージョン）

- Cloud SQL (db-f1-micro): ~$10/月
- Cloud Run: 従量課金（無料枠あり）
- Secret Manager: ほぼ無料
