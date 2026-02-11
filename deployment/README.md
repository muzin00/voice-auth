# GCP Cloud Runへのデプロイ

## 前提条件

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
  インストール済み
- `gcloud auth login` で認証完了

## 構成の選択

| 構成             | DB          | 月額コスト | 推奨用途                 |
| ---------------- | ----------- | ---------: | ------------------------ |
| **PostgreSQL版** | Cloud SQL   |       ~$10 | チーム利用、本番サービス |
| **SQLite版**     | GCSマウント |        ~$0 | 個人利用、テスト         |

> ⚠️ **SQLite版の注意事項**:
>
> - `max-instances=1` 必須（複数インスタンス不可）
> - 同時リクエスト数が制限される
> - GCS FUSEはSQLiteの公式サポート外のため、自己責任での運用

---

## 初回セットアップ（PostgreSQL版）

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

### 5. Secret Manager セットアップ

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

### 6. コンテナイメージビルド

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

### 7. マイグレーション用 Cloud Run Job 作成

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

### 8. マイグレーション実行

```bash
gcloud run jobs execute migration-upgrade \
  --region=$REGION \
  --wait
```

### 9. Cloud Run デプロイ（外部公開）

```bash
gcloud run deploy vca-server \
  --image=$IMAGE_URL \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="DB_TYPE=postgres,POSTGRES_SERVER=/cloudsql/$CONNECTION_NAME,POSTGRES_PORT=5432,POSTGRES_USER=$DB_USER,POSTGRES_DB=$DB_NAME,STORAGE_TYPE=gcs,GCS_BUCKET_NAME=$BUCKET_NAME,GCS_PROJECT_ID=$PROJECT_ID" \
  --set-secrets="POSTGRES_PASSWORD=vca-db-password:latest" \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --max-instances=10 \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300
```

---

## 初回セットアップ（SQLite + GCSマウント版）

> ⚠️ **個人利用・テスト用途向け** Cloud
> SQLを使用せず、GCSマウント上のSQLiteでデータを永続化します。
> 維持費はほぼ0円ですが、スケーリングには制約があります。

### 1. プロジェクト作成とAPI有効化

```bash
# プロジェクト作成
gcloud projects create YOUR_PROJECT_ID --name="VCA Server"
gcloud config set project YOUR_PROJECT_ID

# 課金アカウント紐付け
gcloud billing accounts list
gcloud billing projects link YOUR_PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

# API有効化（Cloud SQL Adminは不要）
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com
```

### 2. 環境変数設定

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast1
# 音声ファイル用バケット
export BUCKET_NAME="${PROJECT_ID}-vca-voices"
# SQLite DB保存用バケット
export DB_BUCKET_NAME="${PROJECT_ID}-vca-db"
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
gcloud run jobs create migration-upgrade-sqlite \
  --image=$IMAGE_URL \
  --region=$REGION \
  --command="sh" \
  --args="-c,cd /app && uv run alembic upgrade head" \
  --add-volume="name=db-volume,type=cloud-storage,bucket=$DB_BUCKET_NAME" \
  --add-volume-mount="volume=db-volume,mount-path=/app/db" \
  --set-env-vars="DB_TYPE=sqlite,SQLITE_PATH=/app/db/vca.db" \
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
gcloud run deploy vca-server \
  --image=$IMAGE_URL \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --execution-environment=gen2 \
  --add-volume="name=db-volume,type=cloud-storage,bucket=$DB_BUCKET_NAME" \
  --add-volume-mount="volume=db-volume,mount-path=/app/db" \
  --set-env-vars="DB_TYPE=sqlite,SQLITE_PATH=/app/db/vca.db,STORAGE_TYPE=gcs,GCS_BUCKET_NAME=$BUCKET_NAME,GCS_PROJECT_ID=$PROJECT_ID" \
  --max-instances=1 \
  --memory=4Gi \
  --cpu-boost \
  --cpu=2 \
  --timeout=300
```

---

## 再デプロイ（コード変更後）- PostgreSQL版

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

## 再デプロイ（コード変更後）- SQLite版

### 環境変数再設定

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast1
export BUCKET_NAME="${PROJECT_ID}-vca-voices"
export DB_BUCKET_NAME="${PROJECT_ID}-vca-db"
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
gcloud run jobs update migration-upgrade-sqlite \
  --image=$IMAGE_URL \
  --region=$REGION

# 4. マイグレーション実行
gcloud run jobs execute migration-upgrade-sqlite \
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
gcloud run services logs read vca-server --region asia-northeast1 --limit=50

# マイグレーションログ（PostgreSQL版）
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=migration-upgrade" \
  --limit=50 \
  --format="value(textPayload)"

# マイグレーションログ（SQLite版）
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=migration-upgrade-sqlite" \
  --limit=50 \
  --format="value(textPayload)"
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
gcloud run services update-traffic vca-server \
  --to-revisions=REVISION_NAME=100 \
  --region asia-northeast1
```

---

## アーキテクチャ

### PostgreSQL版

- **API**: Cloud Run (FastAPI)
- **Database**: Cloud SQL (PostgreSQL 16)
- **Storage**: GCS (音声ファイル)
- **Container Registry**: Artifact Registry (自動クリーンアップ有効)
- **Secrets**: Secret Manager
- **Migrations**: Cloud Run Jobs (Alembic)

### SQLite版

- **API**: Cloud Run (FastAPI)
- **Database**: SQLite on GCS FUSE
- **Storage**: GCS (音声ファイル + DBファイル)
- **Container Registry**: Artifact Registry (自動クリーンアップ有効)
- **Migrations**: Cloud Run Jobs (Alembic)

## コスト概算（東京リージョン）

### PostgreSQL版

| サービス                |             月額コスト |
| ----------------------- | ---------------------: |
| Cloud SQL (db-f1-micro) |                   ~$10 |
| Cloud Run               | 従量課金（無料枠あり） |
| Secret Manager          |               ほぼ無料 |
| GCS                     |               ほぼ無料 |
| **合計**                |            **~$10/月** |

### SQLite版

| サービス  |                       月額コスト |
| --------- | -------------------------------: |
| Cloud Run |           従量課金（無料枠あり） |
| GCS       | ほぼ無料（数GB以下なら無料枠内） |
| **合計**  |                       **~$0/月** |

> SQLite版は個人利用の低トラフィック環境では、GCPの無料枠内で運用可能です。
