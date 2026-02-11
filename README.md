# VCA Server

## ローカル開発

### データベース選択

環境変数`DB_TYPE`でPostgreSQLまたはSQLiteを選択できます（デフォルト: SQLite）。

**SQLiteを使う場合（デフォルト）:**

```bash
# .envファイル
DB_TYPE=sqlite

# 起動（dbコンテナなし、軽量）
docker compose up -d
```

**PostgreSQLを使う場合:**

```bash
# .envファイル
DB_TYPE=postgres

# 起動（dbコンテナも起動）
docker compose --profile postgres up -d
```

### 起動

```bash
docker compose up -d
```

### テスト実行

> **注意**: pytestはパッケージごとに実行してください（conftest.pyの衝突を避けるため）

```bash
# 全パッケージのテストを実行
make test

# 特定パッケージのテストを実行
make test-auth
make test-engine
make test-infra
```

### 型チェック

```bash
# ローカル環境
make typecheck

# Docker環境
docker compose exec app sh -c "uv sync && make typecheck"
```

### Lint & Format

```bash
# ローカル環境
make lint     # Lintチェックのみ
make format   # Lint修正 + フォーマット

# Docker環境
docker compose exec app sh -c "uv sync && make format"

# pre-commit（コミット前の一括チェック）
uv run pre-commit run -a
```

### API動作確認

```bash
# 声紋登録（WAV形式の音声ファイルを使用）
AUDIO_BASE64=$(base64 -i samples/sample1.wav)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"speaker_id\": \"test_user\", \"audio_data\": \"$AUDIO_BASE64\", \"audio_format\": \"wav\"}"

# 声紋認証
AUDIO_BASE64=$(base64 -i samples/sample1.wav)
curl -X POST http://localhost:8000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d "{\"speaker_id\": \"test_user\", \"audio_data\": \"$AUDIO_BASE64\", \"audio_format\": \"wav\"}"
```

---

## デプロイ

GCP Cloud Run へのデプロイ手順は [deployment/README.md](deployment/README.md) を参照してください。
