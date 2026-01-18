# Deployment Configuration

このディレクトリには、GCP Cloud
Runへのデプロイに関連する設定ファイルが含まれています。

## ファイル一覧

### artifact-registry-cleanup-policy.json

Artifact Registryのクリーンアップポリシー設定です。

**目的**:
ビルドされたコンテナイメージが溜まるのを防ぎ、ストレージコストを削減します。

**設定内容**:

- 最新2つのイメージバージョンを保持
- それ以外の古いイメージを自動削除

**適用方法**:

```bash
gcloud artifacts repositories set-cleanup-policies cloud-run-source-deploy \
    --project=YOUR_PROJECT_ID \
    --location=asia-northeast1 \
    --policy=deployment/artifact-registry-cleanup-policy.json
```

**効果**:

- Whisperモデルを含むイメージは1つで2-4GB程度
- 20個のイメージがある場合、約40-80GBのストレージを削減可能
- 月額コスト削減: 約$4-8/月（$0.10/GB/月として計算）

## 注意事項

- クリーンアップポリシーは自動的に実行されます
- 現在Cloud Runで稼働中のリビジョンのイメージは削除されません
- `keepCount` を変更する場合は、運用中のリビジョン数を考慮してください
