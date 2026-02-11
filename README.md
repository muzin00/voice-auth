# VoiceAuth

音声によるランダムプロンプト認証システム。声紋とASR（音声認識）を組み合わせた二要素認証を提供します。

## 特徴

- **声紋認証**: CAM++ による話者識別（192次元ベクトル）
- **ASR検証**: SenseVoice による発話内容の検証
- **ランダムプロンプト**: 毎回異なる数字列を発話させることでリプレイ攻撃を防止
- **CPU推論**: sherpa-onnx による低遅延な推論（GPU不要）

## クイックスタート

```bash
# リポジトリをクローン
git clone <repository-url>
cd voice-auth

# 環境変数を設定
cp .env.example .env

# 起動
docker compose up -d

# ブラウザでデモ画面にアクセス
open http://localhost:8000/demo/
```

## 開発

```bash
# テスト実行
make test

# 型チェック
make typecheck

# Lint & Format
make format
```

### データベース選択

環境変数`DB_TYPE`でPostgreSQLまたはSQLiteを選択できます（デフォルト: SQLite）。

```bash
# SQLite（デフォルト）
DB_TYPE=sqlite
docker compose up -d

# PostgreSQL
DB_TYPE=postgres
docker compose --profile postgres up -d
```

## ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [要件定義書](docs/requirements.md) | 機能要件・非機能要件・セキュリティ要件 |
| [アーキテクチャガイド](docs/architecture-guide.md) | 設計・ディレクトリ構成・データモデル |
| [API仕様書](docs/api-specification.md) | WebSocket/REST API詳細 |
| [開発ガイド](docs/development-guide.md) | 開発方針（TDD, Outside-In） |
| [デプロイガイド](docs/deployment.md) | GCP Cloud Runへのデプロイ |

## 技術スタック

| コンポーネント | 技術 |
|---------------|------|
| フレームワーク | FastAPI |
| 音声区間検出 | sherpa-onnx (Silero VAD) |
| 音声認識 | sherpa-onnx (SenseVoice) |
| 声紋抽出 | sherpa-onnx (CAM++) |
| データベース | PostgreSQL / SQLite |

## ライセンス

MIT License
