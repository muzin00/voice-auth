# API仕様書

> VoiceAuth - 音声認証サーバー API仕様

## API エンドポイント

### WebSocket エンドポイント

| パス              | 説明                                         |
| ----------------- | -------------------------------------------- |
| `/ws/enrollment`  | 話者登録（プロンプト生成・音声送信・PIN登録）|
| `/ws/verify`      | 認証（声紋認証 + PINフォールバック）         |

### REST API エンドポイント

| メソッド | パス      | 説明             |
| -------- | --------- | ---------------- |
| GET      | `/health` | ヘルスチェック   |
| GET      | `/demo/`  | デモ画面表示     |

#### GET /health

サーバーの稼働状態を確認する。

**レスポンス:**

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## WebSocket 通信仕様

### メッセージフォーマット

WebSocket通信ではJSONとバイナリのハイブリッド方式を採用する。

| 方向 | データ種別 | 用途 |
|------|------------|------|
| Client → Server | JSON | 制御メッセージ（開始、PIN送信等） |
| Client → Server | Binary | 音声データ（webm形式） |
| Server → Client | JSON | 結果・状態通知 |

### 状態管理

- 接続中はサーバーメモリで状態を保持
- 接続切断時は一時データを破棄（最初からやり直し）
- WebSocketタイムアウト: 60秒（音声送信がない場合に自動切断）

### エラーメッセージフォーマット

```json
{
  "type": "error",
  "code": "SPEAKER_NOT_FOUND",
  "message": "指定されたspeaker_idは登録されていません"
}
```

**エラーコード一覧:**
| コード | 説明 |
|--------|------|
| `SPEAKER_NOT_FOUND` | 指定されたspeaker_idが存在しない |
| `SPEAKER_ALREADY_EXISTS` | 登録済みのspeaker_idで再登録しようとした |
| `INVALID_AUDIO` | 音声データが不正（短すぎる、無音等） |
| `ASR_FAILED` | 音声認識に失敗 |
| `TIMEOUT` | タイムアウト |

---

## WS /ws/enrollment（話者登録）

WebSocket接続で登録フロー全体を処理する。

### シーケンス

```
1. Client: 接続確立
2. Client → Server: JSON（登録開始、speaker_id指定）
3. Server → Client: プロンプト送信（5セット分）
4. ループ（5セット分）:
   4.1 Client → Server: Binary（音声データ）
   4.2 Server → Client: JSON（ASR結果）
   4.3 失敗時はリトライ（同じプロンプトを再送）
5. Client → Server: JSON（PIN登録）
6. Server → Client: JSON（登録完了）
7. 接続クローズ
```

### Client → Server: 登録開始

```json
{
  "type": "start_enrollment",
  "speaker_id": "user123",
  "speaker_name": "山田太郎"
}
```

- `speaker_name`はオプション
- 既に登録済みの`speaker_id`の場合はエラーを返す

### Server → Client: プロンプト送信

```json
{
  "type": "prompts",
  "speaker_id": "user123",
  "prompts": ["4326", "8105", "9718", "5029", "3674"],
  "total_sets": 5,
  "current_set": 0
}
```

### Client → Server: 音声送信

- Binary フレームで webm 形式の音声データを送信
- サーバー側で PyAV を使用して wav に変換

### Server → Client: ASR結果（成功）

```json
{
  "type": "asr_result",
  "success": true,
  "asr_result": "4326",
  "set_index": 0,
  "remaining_sets": 4,
  "message": "OK！次へ進みます"
}
```

### Server → Client: ASR結果（失敗）

```json
{
  "type": "asr_result",
  "success": false,
  "asr_result": "4327",
  "set_index": 0,
  "retry_count": 1,
  "max_retries": 5,
  "message": "聞き取れませんでした。もう一度、はっきりとお願いします"
}
```

### Client → Server: PIN登録

```json
{
  "type": "register_pin",
  "pin": "1234"
}
```

### Server → Client: 登録完了

```json
{
  "type": "enrollment_complete",
  "speaker_id": "user123",
  "registered_digits": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
  "has_pin": true,
  "status": "registered"
}
```

---

## WS /ws/verify（認証）

WebSocket接続で声紋認証およびPINフォールバックを処理する。

### シーケンス（声紋認証）

```
1. Client: 接続確立
2. Client → Server: JSON（認証開始、speaker_id指定）
3. Server → Client: JSON（プロンプト送信）
4. Client → Server: Binary（音声データ）
5. Server → Client: JSON（認証結果）
6. 接続クローズ
```

### シーケンス（PINフォールバック）

```
1. 声紋認証失敗後
2. Client → Server: JSON（PIN認証）
3. Server → Client: JSON（認証結果）
4. 接続クローズ
```

### Client → Server: 認証開始

```json
{
  "type": "start_verify",
  "speaker_id": "user123"
}
```

### Server → Client: プロンプト送信

```json
{
  "type": "prompt",
  "prompt": "4326",
  "length": 4
}
```

### Client → Server: 音声送信

- Binary フレームで webm 形式の音声データを送信

### Server → Client: 認証結果（成功）

```json
{
  "type": "verify_result",
  "authenticated": true,
  "speaker_id": "user123",
  "asr_result": "4326",
  "asr_matched": true,
  "voice_similarity": 0.82,
  "digit_scores": {
    "4": 0.85,
    "3": 0.79,
    "2": 0.81,
    "6": 0.83
  },
  "message": "認証成功"
}
```

### Server → Client: 認証結果（ASR不一致）

```json
{
  "type": "verify_result",
  "authenticated": false,
  "speaker_id": "user123",
  "asr_result": "4327",
  "asr_matched": false,
  "voice_similarity": null,
  "digit_scores": null,
  "message": "発話内容がプロンプトと一致しません"
}
```

### Server → Client: 認証結果（声紋不一致）

```json
{
  "type": "verify_result",
  "authenticated": false,
  "speaker_id": "user123",
  "asr_result": "4326",
  "asr_matched": true,
  "voice_similarity": 0.52,
  "digit_scores": {
    "4": 0.55,
    "3": 0.48,
    "2": 0.51,
    "6": 0.54
  },
  "can_fallback_to_pin": true,
  "message": "声紋が一致しません"
}
```

### Client → Server: PIN認証（フォールバック）

```json
{
  "type": "verify_pin",
  "pin": "1234"
}
```

### Server → Client: PIN認証結果

```json
{
  "type": "verify_result",
  "authenticated": true,
  "speaker_id": "user123",
  "auth_method": "pin",
  "message": "PIN認証成功"
}
```

---

## デモ画面

### 概要

音声認証システムの動作確認用デモUI。1画面で登録・認証の両機能をテストできる。

### 技術スタック

| 技術        | 用途                            |
| ----------- | ------------------------------- |
| htmx        | 非同期フォーム送信、部分DOM更新 |
| TailwindCSS | スタイリング（CDN経由）         |
| Jinja2      | テンプレートレンダリング        |
| Web Audio   | マイク録音（MediaRecorder API） |

### 注意事項

- マイク入力はHTTPS環境（またはlocalhost）でのみ動作
- MediaRecorderは通常 `webm` 形式で録音
- 音声データはWebSocketのバイナリフレームで送信（Base64エンコード不要）
- WebSocket接続はwss://（本番）またはws://（localhost）を使用

---

## 音声処理の詳細

### sherpa-onnx (Silero VAD) - 音声区間検出

VAD（Voice Activity Detection）は音声処理パイプラインの**最初に配置する必須コンポーネント**。

#### VADの役割

| 工程 | 役割 | 防ぐ問題 |
|------|------|----------|
| ASR前処理 | 人が喋っている区間だけをSenseVoiceに渡す | 無音/環境音でAIが**幻覚（ハルシネーション）**を起こすのを防止 |
| 切り出し精度向上 | 録音開始〜発話開始までの「間」を自動カット | 喋り出しの瞬間をより正確に検知 |

#### 実装例

```python
import sherpa_onnx

vad_config = sherpa_onnx.VadModelConfig()
vad_config.silero_vad.model_path = "silero_vad.onnx"
vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=60)

def process_audio(audio_data):
    if not vad.is_speech(audio_data):
        return None  # 人の声じゃないなら捨てる
    text = recognizer.decode(audio_data)
    return text
```

### sherpa-onnx (SenseVoice) - 音声認識

- **モデル**: `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17`
- **推奨ファイル**: `model.int8.onnx`（228MB、量子化済み）
- **役割**: 発話内容のテキスト化、各文字のタイムスタンプ取得
- **対応言語**: 日本語/中国語/英語/韓国語/広東語

#### 実装例

```python
import sherpa_onnx

recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model="models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx",
    tokens="models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/tokens.txt",
    num_threads=2,
    use_itn=True,
)

stream = recognizer.create_stream()
stream.accept_waveform(sample_rate, samples)
recognizer.decode_stream(stream)
result = stream.result
# result.text, result.tokens, result.timestamps
```

### sherpa-onnx (CAM++) - 声紋抽出

- **モデル**: `3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx`
- **出力**: 192次元の特徴量ベクトル
- **類似度計算**: コサイン類似度
- **しきい値**: 0.75

#### 実装例

```python
import sherpa_onnx
import numpy as np

config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
    model="3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx",
    num_threads=1,
)
extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)

stream = extractor.create_stream()
stream.accept_waveforms(sample_rate, samples)
embedding = extractor.compute(stream)  # shape: (192,)

# コサイン類似度
score = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
```

### セグメンテーション時のマージン処理

ASRのタイムスタンプをそのまま使うと声紋情報が欠損するため、マージンを追加する。

- **前の余白（Pre-padding）**: 50ms〜100ms
- **後ろの余白（Post-padding）**: 50ms〜100ms

```python
def cut_segment_with_padding(audio_array, sample_rate, start_sec, end_sec, padding_sec=0.1):
    start_index = int(start_sec * sample_rate)
    end_index = int(end_sec * sample_rate)
    pad_samples = int(padding_sec * sample_rate)

    new_start = max(0, start_index - pad_samples)
    new_end = min(len(audio_array), end_index + pad_samples)

    return audio_array[new_start:new_end]
```

---

## 関連ドキュメント

- [要件定義書](./requirements.md) - 機能要件・非機能要件
- [アーキテクチャガイド](./architecture-guide.md) - 設計・ディレクトリ構成
- [デプロイガイド](./deployment.md) - GCP Cloud Runへのデプロイ
