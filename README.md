# VCA Server

## GCP Cloud Runへのデプロイ

### 前提条件

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) インストール済み
- `gcloud auth login` で認証完了

### 初回セットアップ

```bash
# 1. プロジェクト作成
gcloud projects create YOUR_PROJECT_ID --name="VCA Server"
gcloud config set project YOUR_PROJECT_ID

# 2. 課金アカウント紐付け
gcloud billing accounts list
gcloud billing projects link YOUR_PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

# 3. API有効化
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### デプロイ

```bash
gcloud run deploy vca-server --source . --region asia-northeast1 --allow-unauthenticated --set-env-vars ENVIRONMENT=production
```

### 再デプロイ（コード変更後）

```bash
gcloud run deploy vca-server --source . --region asia-northeast1 --set-env-vars ENVIRONMENT=production
```

### 便利なコマンド

```bash
# ログ確認
gcloud run logs read vca-server --region asia-northeast1

# サービス情報
gcloud run services describe vca-server --region asia-northeast1

# 環境変数更新
gcloud run services update vca-server --region asia-northeast1 --update-env-vars KEY=VALUE
```
