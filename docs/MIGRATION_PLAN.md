# 移行計画

> vca-server から voiceauth への移行計画

## 移行完了サマリー

全8フェーズの移行が完了しました。

```
voiceauth/                     # 48ファイル
├── app/                       # Application層（Composition Root）
│   ├── routers/              # APIルーター
│   ├── websocket/            # WebSocketハンドラー
│   ├── templates/            # HTMLテンプレート
│   ├── static/               # 静的ファイル
│   ├── main.py               # FastAPIアプリケーション
│   ├── dependencies.py       # DI設定
│   ├── model_loader.py       # MLモデルローダー
│   └── settings.py           # API設定
├── domain/                    # Domain層（ORM非依存）
│   ├── models/               # ドメインモデル（dataclass）
│   ├── protocols/            # Protocol定義（DIP）
│   └── prompt_generator.py   # プロンプト生成
├── domain_service/            # Domain Service層
│   ├── enrollment.py         # 登録サービス
│   ├── verify.py             # 認証サービス
│   └── settings.py           # サービス設定
├── database/                  # Database層
│   ├── stores/               # Store実装
│   ├── models.py             # SQLModelモデル
│   ├── session.py            # セッション管理
│   └── settings.py           # DB設定
├── engine/                    # Engine層（AI/ML）
│   ├── vad/silero.py         # VAD実装
│   ├── asr/sensevoice.py     # ASR実装
│   ├── voiceprint/campp.py   # Voiceprint実装
│   └── settings.py           # エンジン設定
└── audio/                     # Audio層
    └── converter.py          # 音声変換
```

---

## Phase 1: ディレクトリ構造の準備 ✅

1. プロジェクトルートに `voiceauth/` ディレクトリを作成
2. サブディレクトリを作成:
   - `voiceauth/domain/`
   - `voiceauth/domain/models/`
   - `voiceauth/domain/protocols/`
   - `voiceauth/domain_service/`
   - `voiceauth/app/`
   - `voiceauth/database/`
   - `voiceauth/audio/`
   - `voiceauth/engine/`
3. 各ディレクトリに `__init__.py` を作成

## Phase 2: domain 層の移行 ✅

1. `vca_auth/models/speaker.py` → `voiceauth/domain/models/speaker.py`
   - SQLModel 依存を削除し、純粋な Python クラスに変換
2. `vca_auth/models/digit_voiceprint.py` → `voiceauth/domain/models/voiceprint.py`
   - ファイル名をリネーム
   - SQLModel 依存を削除
3. `vca_auth/services/prompt_generator.py` → `voiceauth/domain/prompt_generator.py`
4. Protocol 定義を新規作成:
   - `voiceauth/domain/protocols/store.py`
   - `voiceauth/domain/protocols/vad.py`
   - `voiceauth/domain/protocols/asr.py`
   - `voiceauth/domain/protocols/voiceprint.py`
   - `voiceauth/domain/protocols/audio.py`

## Phase 3: engine 層の移行 ✅

1. `vca_engine/settings.py` → `voiceauth/engine/settings.py`
2. `vca_engine/exceptions.py` → `voiceauth/engine/exceptions.py`
3. `vca_engine/vad.py` → `voiceauth/engine/vad/silero.py`
4. `vca_engine/asr.py` → `voiceauth/engine/asr/sensevoice.py`
5. `vca_engine/segmentation.py` → `voiceauth/engine/asr/segmentation.py`
6. `vca_engine/voiceprint.py` → `voiceauth/engine/voiceprint/campp.py`
7. 各モジュールが `domain/protocols/` の Protocol を実装するよう修正

## Phase 4: audio 層の移行 ✅

1. `vca_engine/audio_converter.py` → `voiceauth/audio/converter.py`
2. `vca_engine/audio_processor.py` は削除（Facade 廃止）

## Phase 5: database 層の移行 ✅

1. `vca_infra/settings.py` → `voiceauth/database/settings.py`
2. `voiceauth/database/session.py` を作成
3. `voiceauth/database/models.py` を作成（SQLModel 定義）
4. `vca_auth/repositories/` → `voiceauth/database/stores/`
   - Store が `domain/protocols/store.py` を実装するよう修正
5. `voiceauth/database/exceptions.py` を作成

## Phase 6: domain_service 層の移行 ✅

1. `vca_auth/services/enrollment_service.py` → `voiceauth/domain_service/enrollment.py`
   - Protocol 経由で依存を受け取るよう修正
2. `vca_auth/services/verify_service.py` → `voiceauth/domain_service/verify.py`
   - Protocol 経由で依存を受け取るよう修正
3. `voiceauth/domain_service/settings.py` を作成

## Phase 7: app 層の移行 ✅

1. `vca_api/settings.py` → `voiceauth/app/settings.py`
2. `vca_api/dependencies.py` → `voiceauth/app/dependencies.py`
   - Protocol 実装の注入を設定
3. `vca_engine/model_loader.py` → `voiceauth/app/model_loader.py`
4. `vca_api/routes/` → `voiceauth/app/routers/`
5. `vca_api/websocket/` → `voiceauth/app/websocket/`
6. `vca_api/templates/` → `voiceauth/app/templates/`
7. `vca_api/static/` → `voiceauth/app/static/`
8. `voiceauth/app/main.py` を作成

## Phase 8: エントリポイントとクリーンアップ ✅

1. `main.py` を更新して `voiceauth.app` を使用
2. `pyproject.toml` を更新:
   - Workspace 設定を削除
   - 依存関係を統合
   - パッケージ名を `voiceauth` に変更

## 残作業

以下は手動で実行してください:

1. **packages/ ディレクトリの削除**
   ```bash
   rm -rf packages/
   ```

2. **依存関係の再インストール**
   ```bash
   uv sync
   ```

3. **動作確認**
   ```bash
   python main.py
   ```

4. **テストの実行**（テストファイル移行後）
   ```bash
   pytest voiceauth/
   ```

## 環境変数プレフィックス

| 層 | プレフィックス |
|---|---|
| API | `VOICEAUTH_API_` |
| Database | `VOICEAUTH_DB_` |
| Engine | `VOICEAUTH_ENGINE_` |
| Service | `VOICEAUTH_SERVICE_` |
