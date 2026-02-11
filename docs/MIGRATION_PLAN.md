# 移行計画

> vca-server から voiceauth への移行計画

## Phase 1: ディレクトリ構造の準備

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

## Phase 2: domain 層の移行

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

## Phase 3: engine 層の移行

1. `vca_engine/settings.py` → `voiceauth/engine/settings.py`
2. `vca_engine/exceptions.py` → `voiceauth/engine/exceptions.py`
3. `vca_engine/vad.py` → `voiceauth/engine/vad/silero.py`
4. `vca_engine/asr.py` → `voiceauth/engine/asr/sensevoice.py`
5. `vca_engine/segmentation.py` → `voiceauth/engine/asr/segmentation.py`
6. `vca_engine/voiceprint.py` → `voiceauth/engine/voiceprint/campp.py`
7. 各モジュールが `domain/protocols/` の Protocol を実装するよう修正

## Phase 4: audio 層の移行

1. `vca_engine/audio_converter.py` → `voiceauth/audio/converter.py`
2. `voiceauth/audio/processor.py` を新規作成（必要に応じて）
3. `vca_engine/audio_processor.py` は削除（Facade 廃止）

## Phase 5: database 層の移行

1. `vca_infra/settings.py` → `voiceauth/database/settings.py`
2. `voiceauth/database/session.py` を作成
3. `voiceauth/database/models.py` を作成（SQLModel 定義）
4. `vca_auth/repositories/` → `voiceauth/database/stores/`
   - Store が `domain/protocols/store.py` を実装するよう修正
5. Alembic 設定を `voiceauth/database/` に移動

## Phase 6: domain_service 層の移行

1. `vca_auth/services/enrollment_service.py` → `voiceauth/domain_service/enrollment.py`
   - Protocol 経由で依存を受け取るよう修正
2. `vca_auth/services/verify_service.py` → `voiceauth/domain_service/verify.py`
   - Protocol 経由で依存を受け取るよう修正
3. `voiceauth/domain_service/settings.py` を作成

## Phase 7: app 層の移行

1. `vca_api/settings.py` → `voiceauth/app/settings.py`
2. `vca_api/dependencies.py` → `voiceauth/app/dependencies.py`
   - Protocol 実装の注入を設定
3. `vca_engine/model_loader.py` → `voiceauth/app/model_loader.py`
4. `vca_api/routes/` → `voiceauth/app/routers/`
5. `vca_api/websocket/` → `voiceauth/app/websocket/auth.py`（統合）
6. `vca_api/templates/` → `voiceauth/app/templates/`
7. `vca_api/static/` → `voiceauth/app/static/`
8. `voiceauth/app/exception_handlers.py` を作成

## Phase 8: エントリポイントとクリーンアップ

1. `main.py` を更新して `voiceauth.app` を使用
2. `pyproject.toml` を更新:
   - Workspace 設定を削除
   - 依存関係を統合
3. `packages/` ディレクトリを削除
4. 全テストを実行して動作確認
5. import パスを全て `voiceauth.*` に更新

## 移行時の注意点

- 各 Phase 完了後にテストを実行
- Protocol 定義を先に作成し、実装クラスが適合することを確認
- import パスの変更は一括置換で対応
- Git ブランチを Phase ごとに分けて管理を推奨
