# VoiceAuth プロジェクトルール

このファイルは Claude Code が起動時に自動的に読み込むプロジェクトルールです。

## プロジェクト概要

- **名前**: VoiceAuth（音声認証システム）
- **言語**: Python 3.11
- **フレームワーク**: FastAPI
- **パッケージ管理**: uv

## コーディング規約

### Python スタイル

- **フォーマッター**: ruff format
- **リンター**: ruff check
- **型チェック**: ty
- **行長制限**: なし（E501 は無視）

### インポート順序

```python
# 1. 標準ライブラリ
import os
from typing import Any

# 2. サードパーティ
from fastapi import FastAPI
from pydantic import BaseModel

# 3. ローカル
from voiceauth.core import config
```

### 命名規則

| 種類 | 形式 | 例 |
|------|------|-----|
| クラス | PascalCase | `VoiceAuthenticator` |
| 関数・変数 | snake_case | `verify_speaker` |
| 定数 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| モジュール | snake_case | `voice_processor.py` |

### 型ヒント

- すべての関数に型ヒントを付ける
- 戻り値が `None` の場合も明示 (`-> None`)
- 複雑な型は `TypeAlias` を使用

## コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/) に従う。

### フォーマット

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Type 一覧

| Type | 用途 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみの変更 |
| `style` | コードの意味に影響しない変更（空白、フォーマット等） |
| `refactor` | バグ修正でも機能追加でもないコード変更 |
| `perf` | パフォーマンス改善 |
| `test` | テストの追加・修正 |
| `chore` | ビルドプロセスや補助ツールの変更 |
| `ci` | CI 設定の変更 |

### Scope 例

- `api`: API エンドポイント
- `auth`: 認証関連
- `voice`: 音声処理
- `db`: データベース
- `docker`: Docker 関連

### 例

```
feat(api): 声紋登録エンドポイントを追加

- POST /api/v1/speakers を実装
- 登録時のバリデーションを追加
```

## 開発コマンド

```bash
# テスト実行
make test

# 型チェック
make typecheck

# フォーマット & Lint
make format

# 開発サーバー起動
docker compose up -d
```

## ディレクトリ構成

```
voiceauth/
├── api/          # FastAPI ルーター
├── core/         # 設定、依存性注入
├── models/       # SQLModel データモデル
├── services/     # ビジネスロジック
└── tests/        # テスト
```

## テスト

- **フレームワーク**: pytest
- **カバレッジ**: pytest-cov
- **方針**: Outside-In TDD

テストファイルは各モジュールと同じディレクトリに配置:
- `voiceauth/api/routes.py` → `voiceauth/api/test_routes.py`

## 重要な注意事項

1. **セキュリティ**: 音声データは機密情報として扱う
2. **パフォーマンス**: CPU 推論のため、処理時間に注意
3. **互換性**: Python 3.11 のみサポート
