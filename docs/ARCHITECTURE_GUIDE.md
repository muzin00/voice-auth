# 設計ガイド

> このドキュメントは、VCA Server のアーキテクチャ設計を定めたものです。

## コンセプト & アーキテクチャ

Rust の Workspace 思想を取り入れた **Modular Monolith (Package by Feature)** 構成を採用します。
各機能は独立した Python パッケージとして管理され、明確な責務と依存方向を持ちます。

- **パッケージ管理**: `uv` Workspace
- **依存性管理**: 依存性逆転の原則 (DIP) による疎結合設計
- **ORM**: SQLModel (ドメインモデルと DB 定義の実用的統合)
- **マイグレーション**: プロジェクトルート集約型 (Alembic)

## Router-Service-Repository パターン

FastAPIで推奨される「モダンな構成」。MVCをより細分化・進化させたパターン。
FastAPIの強みである「自動ドキュメント生成」や「型安全」を活かすため、ビジネスロジック（Service）とデータベース処理（Repository）を分離し、テスト容易性を高め、コードの肥大化を抑える。

| 層 | 役割 | 実装 |
|---|---|---|
| **Router** | パス定義、リクエスト受付、バリデーション | FastAPI Router |
| **DTO** | 入出力データの型定義 | Pydantic モデル |
| **Service** | 計算、外部API連携、条件分岐などの業務処理 | Python クラス/関数 |
| **Repository** | データベースへのアクセス | SQLModel |

## ディレクトリ構成

```
vca_server/                     # プロジェクトルート
├── pyproject.toml              # Workspace定義, Root依存関係
├── alembic.ini                 # Alembic設定 (script_location = migrations)
├── uv.lock                     # ロックファイル
├── migrations/                 # 【DBマイグレーション管理】
│   ├── env.py                  # 全パッケージのモデルを集約し、InfraのDB設定で実行
│   ├── script.py.mako
│   └── versions/               # マイグレーションスクリプト
│
└── packages/
    ├── vca_api/                # 【プレゼンテーション層 / Composition Root】
    │   ├── pyproject.toml
    │   ├── tests/
    │   └── vca_api/
    │       ├── py.typed            # 型ヒントマーカー
    │       ├── settings.py         # サーバー設定 (Host, Port, LogLevel)
    │       ├── main.py             # FastAPI起動, Middleware, Router統合
    │       ├── dependencies.py     # DIコンテナ (Infra実装をAuthサービスへ注入)
    │       ├── exception_handlers.py # ドメイン例外をHTTPレスポンスへ変換
    │       └── routers/            # エンドポイント定義
    │           ├── auth.py         # 認証関連 API (WebSocket含む)
    │           └── demo.py         # デモ画面用 API
    │
    ├── vca_auth/               # 【機能ドメイン: 認証】(ビジネスロジックの中核)
    │   ├── pyproject.toml
    │   ├── tests/
    │   └── vca_auth/
    │       ├── py.typed
    │       ├── settings.py         # 認証設定 (閾値, リトライ回数)
    │       ├── protocols.py        # 外部への要求仕様 (Storage, EngineのIF定義)
    │       ├── dto.py              # データ転送用モデル (Request/Response)
    │       ├── models/             # 永続化モデル (SQLModel)
    │       │   ├── __init__.py
    │       │   ├── speaker.py      # 話者, PIN情報
    │       │   └── voiceprint.py   # 声紋ベクトル
    │       ├── services/           # ビジネスロジック (ユースケース)
    │       │   ├── __init__.py
    │       │   ├── enrollment.py   # 登録フロー (ステートマシン)
    │       │   └── verify.py       # 認証フロー
    │       └── repositories/       # データアクセス実装
    │           ├── __init__.py
    │           └── speaker_repo.py # DB操作 (CRUD)
    │
    ├── vca_engine/             # 【固有ドメイン: 音声AI】(sherpa-onnxの隠蔽)
    │   ├── pyproject.toml
    │   ├── tests/
    │   └── vca_engine/
    │       ├── py.typed
    │       ├── settings.py         # エンジン設定 (モデルパス, スレッド数)
    │       ├── loader.py           # モデルのロード・シングルトン管理
    │       ├── processor.py        # 音声処理パイプライン (Facade)
    │       ├── vad.py              # 音声区間検出 (Silero VAD)
    │       ├── asr.py              # 音声認識 (Paraformer)
    │       ├── speaker.py          # 声紋抽出 (CAM++)
    │       ├── converter.py        # 音声フォーマット変換 (PyAV)
    │       └── models/             # ONNXモデルバイナリ置き場
    │
    └── vca_infra/              # 【汎用インフラ】(技術的詳細)
        ├── pyproject.toml
        ├── tests/
        └── vca_infra/
            ├── py.typed
            ├── settings.py         # インフラ設定 (DB URL, S3 Bucket, Region)
            ├── database/           # DBセッション管理 (SQLAlchemy Engine)
            └── storage/            # ファイルストレージ実装 (S3, Local)
```

## 各パッケージの役割

| パッケージ | 役割 |
|---|---|
| **vca_api** | プレゼンテーション層。FastAPI に依存し、Composition Root（依存関係の組み立て）として機能 |
| **vca_auth** | 認証ドメイン。ビジネスロジックの中核。他パッケージの実装詳細（S3 や sherpa-onnx）には依存しない |
| **vca_engine** | 音声AI処理。sherpa-onnx を隠蔽し、VAD/ASR/声紋抽出の機能を提供 |
| **vca_infra** | 汎用インフラ。DB 接続やストレージ等の技術的詳細を担当 |

## 依存の流れ

```
vca_api → { vca_auth, vca_engine, vca_infra }
vca_infra → (依存なし)
vca_engine → (依存なし)
vca_auth → (依存なし)
```

## 依存性逆転（Protocol パターン）

vca_auth の Service は、永続化や音声処理の具象実装に直接依存しない。代わりに vca_auth/protocols.py に Protocol（インターフェース）を定義し、vca_engine や vca_infra がその Protocol を実装する。

vca_api は Composition Root として機能し、dependencies.py で vca_engine / vca_infra の具象実装を vca_auth の Service に注入する。これにより、vca_auth は外部機能の詳細を知らずにビジネスロジックを実行できる。

## 開発ガイドライン

1. **依存の方向**
   - `vca_auth` は `vca_engine` や `vca_infra` を `import` してはいけない
   - 必要な外部機能は必ず `protocols.py` に定義し、DI で受け取る

2. **設定の管理**
   - 各パッケージは独立した `settings.py` を持つ
   - 設定値は環境変数から読み込む（例: `VCA_AUTH_THRESHOLD`, `VCA_INFRA_DB_URL`）

3. **型安全性**
   - 全パッケージに `py.typed` を配置
   - Protocol に対する実装クラスの適合性は `mypy`（静的解析）でチェック

4. **例外処理**
   - 各パッケージ内で発生したエラーは独自の例外クラスとして送出
   - それらを `vca_api/exception_handlers.py` で一元的にハンドリング

## テスト構成

テストファイルは各パッケージの `tests/` ディレクトリに配置する。
`vca_auth` のテストでは、Engine や Infra をモックに差し替えることで高速に実行可能。
