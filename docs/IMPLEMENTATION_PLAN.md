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
| Phase 1 | SenseVoice調査・検証 | 未着手 |
| Phase 2 | 音声処理パイプライン | 未着手 |
| Phase 3 | データモデル刷新 | 未着手 |
| Phase 4 | 登録フロー | 未着手 |
| Phase 5 | 認証フロー | 未着手 |
| Phase 6 | デモUI | 未着手 |

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

- [ ] sherpa-onnxのSenseVoice対応状況を調査
- [ ] 利用可能なモデルファイルを特定
- [ ] タイムスタンプ出力の動作確認
- [ ] 日本語数字認識の精度確認
- [ ] モデルファイルのダウンロード・配置方法を決定

### 成果物
- モデルファイル名・パスの確定
- サンプルコードによる動作確認結果
- REQUIREMENTS.mdへの反映（必要に応じて）

---

## Phase 2: 音声処理パイプライン

### 目的
VAD + ASR + セグメンテーションの基盤を構築する。

### タスク

- [ ] Silero VAD実装
- [ ] SenseVoice ASR実装（タイムスタンプ付き）
- [ ] 音声セグメンテーション実装
- [ ] CAM++声紋抽出実装（192次元）
- [ ] PyAV音声変換（webm → wav）
- [ ] 単体テスト作成

### 成果物
- `vca_engine`パッケージ
  - `vad.py` - VAD処理
  - `asr.py` - ASR処理
  - `speaker.py` - 声紋抽出
  - `segmentation.py` - 音声分割
  - `converter.py` - フォーマット変換

---

## Phase 3: データモデル刷新

### 目的
Speaker + DigitVoiceprintモデルとマイグレーションを作成する。

### タスク

- [ ] Speakerモデル作成（pin_hash含む）
- [ ] DigitVoiceprintモデル作成（digit, embedding）
- [ ] Alembicマイグレーション作成
- [ ] リポジトリ層作成
- [ ] 単体テスト作成

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

- [ ] バランスド・プロンプト生成ロジック
- [ ] WebSocketエンドポイント作成
- [ ] 登録フロー状態管理
- [ ] ASR検証 + リトライロジック
- [ ] 声紋ベクトル平均化（重心計算）
- [ ] PIN登録（SHA-256ハッシュ化）
- [ ] 結合テスト作成

### 成果物
- `vca_api`パッケージ
  - `websocket/enrollment.py`
- `vca_auth`パッケージ
  - `services/enrollment_service.py`
  - `services/prompt_generator.py`

---

## Phase 5: 認証フロー

### 目的
WebSocket `/ws/verify`エンドポイントとPIN認証フォールバックを実装する。

### タスク

- [ ] WebSocketエンドポイント作成
- [ ] 認証フロー状態管理
- [ ] プロンプト生成・送信
- [ ] ASR検証
- [ ] 声紋照合（数字ごとのスコア計算）
- [ ] PIN認証フォールバック
- [ ] 結合テスト作成

### 成果物
- `vca_api`パッケージ
  - `websocket/verify.py`
- `vca_auth`パッケージ
  - `services/verify_service.py`

---

## Phase 6: デモUI

### 目的
htmx + WebSocketによる新規デモUIを作成する。

### タスク

- [ ] 登録画面（プロンプト表示、進捗、録音ボタン）
- [ ] PIN設定画面
- [ ] 認証画面（プロンプト表示、録音、結果表示）
- [ ] WebSocket通信のJavaScript実装
- [ ] TailwindCSSによるスタイリング
- [ ] E2Eテスト（手動確認）

### 成果物
- `vca_api`パッケージ
  - `templates/demo.html`
  - `static/js/demo.js`
  - `routes/demo.py`

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
