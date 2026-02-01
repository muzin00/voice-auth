# 実装フェーズ計画

> VCA Server - Voice Cognition Authentication Server

## 概要

REQUIREMENTS.mdに基づき、既存実装を完全に作り直す。本ドキュメントで進捗を管理する。

## 進行ルール

- **各フェーズ完了後は次のフェーズに進まず、ユーザーの許可を求めること**
- フェーズ完了時にはステータスを「完了」に更新し、成果物を報告する
- 問題が発生した場合は即座に報告し、判断を仰ぐ

## フェーズ一覧

| フェーズ | 内容 | ステータス |
|---------|------|------------|
| Phase 0 | 既存コード削除 | **完了** |
| Phase 1 | SenseVoice調査・検証 | **完了** |
| Phase 2 | 音声処理パイプライン | **完了** |
| Phase 3 | データモデル刷新 | **完了** |
| Phase 4 | 登録フロー | **完了** |
| Phase 5 | 認証フロー | **完了** |
| Phase 6 | デモUI | **完了** |

---

## Phase 0: 既存コード削除

### 目的
クリーンな状態からREQUIREMENTS.mdに基づいた実装を開始する。

### タスク

- [x] 既存パッケージの削除（packages/配下）
- [x] 既存マイグレーションの削除
- [x] 既存テストの削除
- [x] 空のパッケージ構造を再作成

### 残したもの
- 各パッケージの`pyproject.toml`（依存関係の定義）
- `main.py`（エントリーポイント、Phase 4以降で更新）
- Docker関連ファイル（基本構成）
- 空の`__init__.py`（各パッケージ）

---

## Phase 1: SenseVoice調査・検証

### 目的
sherpa-onnxでSenseVoiceを使用する際の具体的なモデルファイルとタイムスタンプ機能の動作を確認する。

### タスク

- [x] sherpa-onnxのSenseVoice対応状況を調査
- [x] 利用可能なモデルファイルを特定
- [x] タイムスタンプ出力の動作確認
- [x] 日本語認識の動作確認
- [x] モデルファイルのダウンロード・配置方法を決定

### 調査結果

#### モデル情報
- **モデル名**: `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17`
- **推奨ファイル**: `model.int8.onnx` (228MB)
- **対応言語**: 中国語、英語、日本語、韓国語、広東語
- **ダウンロード元**: https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/

#### 動作確認結果
- タイムスタンプ: 各文字（トークン）ごとに取得可能
- 数字認識: 「50」→「5」「0」として別々のトークン・タイムスタンプで認識される
- 追加情報: 言語検出、感情検出、イベント検出も利用可能

#### Python API
```python
recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model="model.int8.onnx",
    tokens="tokens.txt",
    use_itn=True,
    num_threads=2,
)
stream = recognizer.create_stream()
stream.accept_waveform(sample_rate, audio)
recognizer.decode_stream(stream)
# stream.result.text, stream.result.tokens, stream.result.timestamps
```

### 成果物
- `scripts/test_sensevoice.py` - 動作検証スクリプト
- `models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/` - ダウンロード済みモデル

---

## Phase 2: 音声処理パイプライン

### 目的
VAD + ASR + セグメンテーションの基盤を構築する。

### タスク

- [x] Silero VAD実装
- [x] SenseVoice ASR実装（タイムスタンプ付き）
- [x] 音声セグメンテーション実装
- [x] CAM++声紋抽出実装（512次元）
- [x] PyAV音声変換（webm → pcm）
- [x] 単体テスト作成

### 成果物
- `vca_engine`パッケージ
  - `vad.py` - VAD処理（Silero VAD）
  - `asr.py` - ASR処理（SenseVoice）
  - `voiceprint.py` - 声紋抽出（CAM++）
  - `segmentation.py` - 音声分割
  - `audio_converter.py` - フォーマット変換（PyAV）
  - `audio_processor.py` - 処理パイプラインのファサード
  - `model_loader.py` - モデルのシングルトン管理
  - `settings.py` - 設定管理
  - `exceptions.py` - カスタム例外

---

## Phase 3: データモデル刷新

### 目的
Speaker + DigitVoiceprintモデルとマイグレーションを作成する。

### タスク

- [x] Speakerモデル作成（pin_hash含む）
- [x] DigitVoiceprintモデル作成（digit, embedding）
- [x] Alembicマイグレーション作成
- [x] リポジトリ層作成
- [x] 単体テスト作成

### 成果物
- `vca_auth`パッケージ
  - `models/speaker.py`
  - `models/digit_voiceprint.py`
  - `repositories/`
- マイグレーションファイル

---

## Phase 4: 登録フロー

### 目的
WebSocket `/ws/enrollment`エンドポイントと5セット登録ロジックを実装する。

### タスク

- [x] バランスド・プロンプト生成ロジック
- [x] WebSocketエンドポイント作成
- [x] 登録フロー状態管理
- [x] ASR検証 + リトライロジック
- [x] 声紋ベクトル平均化（重心計算）
- [x] PIN登録（SHA-256ハッシュ化）
- [x] 単体テスト作成

### 成果物
- `vca_api`パッケージ
  - `main.py` - FastAPIアプリケーション
  - `settings.py` - API設定
  - `dependencies.py` - 依存性注入
  - `websocket/enrollment.py` - 登録WebSocketエンドポイント
- `vca_auth`パッケージ
  - `services/enrollment_service.py` - 登録サービス
  - `services/prompt_generator.py` - プロンプト生成

---

## Phase 5: 認証フロー

### 目的
WebSocket `/ws/verify`エンドポイントとPIN認証フォールバックを実装する。

### タスク

- [x] WebSocketエンドポイント作成
- [x] 認証フロー状態管理
- [x] プロンプト生成・送信
- [x] ASR検証
- [x] 声紋照合（数字ごとのスコア計算）
- [x] PIN認証フォールバック
- [x] 単体テスト作成

### 成果物
- `vca_api`パッケージ
  - `websocket/verify.py` - 認証WebSocketエンドポイント
- `vca_auth`パッケージ
  - `services/verify_service.py` - 認証サービス

---

## Phase 6: デモUI

### 目的
htmx + WebSocketによる新規デモUIを作成する。

### タスク

- [x] 登録画面（プロンプト表示、進捗、録音ボタン）
- [x] PIN設定画面
- [x] 認証画面（プロンプト表示、録音、結果表示）
- [x] WebSocket通信のJavaScript実装
- [x] TailwindCSSによるスタイリング
- [x] E2Eテスト（手動確認）

### 成果物
- `vca_api`パッケージ
  - `routes/demo.py` - デモページルート（`GET /demo/`）
  - `templates/demo.html` - デモUI（TailwindCSS）
  - `static/js/demo.js` - WebSocket通信・音声録音

---

## 決定事項

以下の確認事項は決定済み（REQUIREMENTS.mdに反映済み）：

| # | 項目 | 決定内容 |
|---|------|----------|
| 1 | 登録フローの開始方法 | クライアントが最初にJSONで`speaker_id`を送信 |
| 2 | 認証フローの再試行 | リトライ可能 |
| 3 | WebSocketエラーメッセージ | `{"type": "error", "code": "...", "message": "..."}` 形式 |
| 4 | バランスド・プロンプト生成 | 同じ数字が連続しない制約あり |
| 5 | 登録の上書き | エラーを返す（`SPEAKER_ALREADY_EXISTS`） |
| 6 | PIN認証の失敗回数制限 | 不要 |
| 7 | WebSocketタイムアウト | 60秒 |
| 8 | ヘルスチェックエンドポイント | `GET /health` を実装する |

---

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-02-01 | 初版作成 |
| 2025-02-01 | 未決定事項を全て決定、REQUIREMENTS.mdに反映 |
| 2025-02-01 | Phase 0 完了 |
| 2025-02-01 | Phase 1 完了（SenseVoice動作確認成功） |
| 2025-02-01 | Phase 2 完了（vca_engineパッケージ実装完了） |
| 2025-02-02 | Phase 3 完了（vca_authパッケージ実装完了） |
| 2025-02-02 | Phase 4 完了（登録フロー実装完了） |
| 2025-02-02 | Phase 5 完了（認証フロー実装完了） |
| 2025-02-02 | Phase 6 完了（デモUI実装完了） |
