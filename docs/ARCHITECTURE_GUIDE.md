# 設計ガイド

> このドキュメントは、FastAPIプロジェクトのアーキテクチャ設計を定めたものです。

## Router-Service-Repository パターン

FastAPIで推奨される「モダンな構成」。MVCをより細分化・進化させたパターン。
FastAPIの強みである「自動ドキュメント生成」や「型安全」を活かすため、ビジネスロジック（Service）とデータベース処理（Repository）を分離し、テスト容易性を高め、コードの肥大化を抑える。

| 層 | 役割 | 実装 |
|---|---|---|
| **Router** | パス定義、リクエスト受付、バリデーション | FastAPI Router |
| **Schema** | 入出力データの型定義 | Pydantic モデル |
| **Service** | 計算、外部API連携、条件分岐などの業務処理 | Python クラス/関数 |
| **Repository** | データベースへのアクセス | SQLAlchemy/SQLModel |

## ディレクトリ構成

```
vca_server/
├── main.py                     # サーバー起動エントリーポイント
├── pyproject.toml              # ルートプロジェクト設定
└── packages/
    ├── vca_api/                # APIレイヤー
    │   ├── pyproject.toml
    │   ├── tests/
    │   └── vca_api/
    │       ├── main.py         # FastAPIアプリ定義
    │       ├── settings.py     # アプリ設定
    │       ├── routes/         # ルーティング
    │       ├── schemas/        # リクエスト/レスポンスモデル
    │       ├── dependencies/   # 依存性注入
    │       ├── middleware/     # ミドルウェア
    │       ├── exceptions/     # 例外ハンドラ
    │       └── utils/          # ユーティリティ
    ├── vca_store/              # 永続化レイヤー
    │   ├── pyproject.toml
    │   ├── tests/
    │   └── vca_store/
    │       ├── session.py      # DB接続
    │       ├── settings.py     # DB設定
    │       ├── repositories/   # リポジトリ実装
    │       └── migrations/     # マイグレーション
    └── vca_core/               # コアレイヤー
        ├── pyproject.toml
        ├── tests/
        └── vca_core/
            ├── models/         # ドメインモデル
            ├── services/       # ビジネスロジック
            ├── interfaces/     # Protocol定義
            └── exceptions/     # カスタム例外
```

## 依存の流れ

```
vca_api → vca_store → vca_core
```

- **vca_api**: FastAPIに依存。Composition Root（依存関係の組み立て）
- **vca_store**: 永続化を担当。SQLModel/SQLAlchemy等でvca_coreのProtocolを実装
- **vca_core**: ドメインロジックの中心。Webフレームワーク非依存

## 依存性逆転（Repository Interface パターン）

vca_core の Service は、永続化の具象実装に直接依存しない。代わりに vca_core/interfaces に Protocol（インターフェース）を定義し、vca_store がその Protocol を実装する。

vca_api は Composition Root として機能し、dependencies/ で vca_store の具象実装を vca_core の Service に注入する。これにより、vca_core は永続化の詳細を知らずにビジネスロジックを実行できる。

## テスト構成

テストファイルは各パッケージの `tests/` ディレクトリに配置する。
