# 要件定義書

> VCA Server - Voice Cognition Authentication Server

## 概要

音声による二要素認証システム。パスフレーズ（知識認証）と声紋（生体認証）を組み合わせてユーザーを識別・認証する。

## 認証方式

| 認証要素     | 種類                      | 役割             | 判定基準                      |
| ------------ | ------------------------- | ---------------- | ----------------------------- |
| パスフレーズ | 知識認証（What you know） | 主要な認証要素   | 文字起こし結果の **完全一致** |
| 声紋         | 生体認証（What you are）  | 補助的な認証要素 | 類似度がしきい値以上          |

### 認証ロジック

```
認証成功条件 = パスフレーズ完全一致 AND 声紋類似度 ≧ しきい値
```

| パスフレーズ | 声紋 | 結果         |
| ------------ | ---- | ------------ |
| 一致         | OK   | **認証成功** |
| 一致         | NG   | **認証失敗** |
| 不一致       | -    | **認証失敗** |

## 技術スタック

| コンポーネント       | 技術           |
| -------------------- | -------------- |
| フレームワーク       | FastAPI        |
| タスクキュー         | Celery         |
| メッセージブローカー | Redis          |
| 文字起こし           | faster-whisper |
| 声紋抽出             | Resemblyzer    |
| データベース         | PostgreSQL     |
| ストレージ           | GCS / ローカル |
| 処理方式             | 同期処理       |

## 認証フロー

```
ユーザー音声入力
       ↓
┌──────────────────────────────────────┐
│  1. 文字起こし（faster-whisper）      │
│     → パスフレーズ抽出               │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│  2. 声紋抽出（Resemblyzer）           │
│     → 256次元特徴量ベクトル生成      │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│  3. 認証判定                          │
│     ├─ パスフレーズ一致？ → 必須     │
│     └─ 声紋類似度？ → 補助的         │
└──────────────────────────────────────┘
       ↓
   認証結果（成功 / 失敗）
```

## 機能要件

| ID   | 機能           | 説明                                   |
| ---- | -------------- | -------------------------------------- |
| FR-1 | 話者登録       | speaker_id、パスフレーズ、声紋を登録   |
| FR-2 | 文字起こし     | faster-whisperで音声→テキスト変換      |
| FR-3 | テキスト正規化 | 小文字化、句読点除去、空白正規化       |
| FR-4 | 声紋抽出       | Resemblyzerで256次元ベクトル抽出       |
| FR-5 | 声紋照合       | コサイン類似度でしきい値判定           |
| FR-6 | 認証判定       | パスフレーズ一致 AND 声紋OK で成功     |
| FR-7 | 話者識別       | 登録済み話者から最も類似する話者を特定 |

## 依存パッケージ

```
faster-whisper
resemblyzer
numpy
```

## 非機能要件

| 項目       | 要件                         |
| ---------- | ---------------------------- |
| スケール   | 個人利用（スケール要件なし） |
| 処理方式   | 同期処理                     |
| レスポンス | 数秒以内                     |
| 対応言語   | 日本語                       |

---

# 設計

## アーキテクチャ

### コンテナ構成

| コンテナ   | 役割                 | 主要パッケージ                      |
| ---------- | -------------------- | ----------------------------------- |
| vca_api    | REST API             | FastAPI                             |
| vca_worker | 音声処理ワーカー     | Celery, faster-whisper, Resemblyzer |
| Redis      | メッセージブローカー | -                                   |
| PostgreSQL | データベース         | -                                   |

### パッケージ構成

| パッケージ | 役割                                       |
| ---------- | ------------------------------------------ |
| vca_core   | インターフェース、モデル、ビジネスロジック |
| vca_api    | REST API（FastAPI）                        |
| vca_infra  | DB/ストレージ実装                          |
| vca_worker | 音声処理タスク（Celery）                   |

### 処理フロー（話者登録）

```
クライアント
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  vca_api（APIコンテナ）                                  │
│  1. リクエスト受信                                       │
│  2. 音声データをストレージに保存                         │
│  3. Celeryタスク呼び出し（同期待ち）────────┐            │
│                                              │            │
└──────────────────────────────────────────────│────────────┘
                                               │
                                               ▼
                                    ┌──────────────────┐
                                    │  Redis（ブローカー）│
                                    └──────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────┐
│  vca_worker（Workerコンテナ）                            │
│  4. 文字起こし（faster-whisper）                         │
│  5. 声紋抽出（Resemblyzer）                              │
│  6. 結果を返却 ─────────────────────────────┐            │
└─────────────────────────────────────────────│────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────┐
│  vca_api（APIコンテナ）                                  │
│  7. Passphrase/VoiceprintをDBに保存                      │
│  8. レスポンス返却                                       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
クライアント
```

### Celeryタスク

| タスク名           | 入力        | 出力                      | 説明                       |
| ------------------ | ----------- | ------------------------- | -------------------------- |
| transcribe         | audio_bytes | str（文字起こしテキスト） | faster-whisperで文字起こし |
| extract_voiceprint | audio_bytes | bytes（256次元ベクトル）  | Resemblyzerで声紋抽出      |

### vca_worker 構成

```
vca_worker/
  __init__.py
  celery_app.py           # Celeryアプリ設定
  tasks/
    __init__.py
    transcription.py      # 文字起こしタスク
    voiceprint.py         # 声紋抽出タスク
  services/
    __init__.py
    transcription_service.py  # faster-whisper wrapper
    voiceprint_service.py     # Resemblyzer wrapper
```

## データモデル

```
Speaker (1) ←─────────── (N) VoiceSample
   ↑                            ↑
   ├── (N) Voiceprint ──────────┤
   │                            │
   └── (N) Passphrase ──────────┘
              (最大3つ)
```

### Speaker

| フィールド   | 型          | 説明           |
| ------------ | ----------- | -------------- |
| id           | int         | PK             |
| public_id    | str         | 公開ID         |
| speaker_id   | str         | ユーザー識別子 |
| speaker_name | str \| None | 話者名         |
| created_at   | datetime    | 作成日時       |
| updated_at   | datetime    | 更新日時       |

### VoiceSample

| フィールド      | 型          | 説明               |
| --------------- | ----------- | ------------------ |
| id              | int         | PK                 |
| public_id       | str         | 公開ID             |
| speaker_id      | int         | FK to Speaker      |
| audio_file_path | str         | 音声ファイルパス   |
| audio_format    | str         | 音声フォーマット   |
| sample_rate     | int \| None | サンプリングレート |
| channels        | int \| None | チャンネル数       |
| created_at      | datetime    | 作成日時           |

### Voiceprint

| フィールド      | 型       | 説明                    |
| --------------- | -------- | ----------------------- |
| id              | int      | PK                      |
| public_id       | str      | 公開ID                  |
| speaker_id      | int      | FK to Speaker           |
| voice_sample_id | int      | FK to VoiceSample       |
| embedding       | bytes    | 声紋ベクトル（256次元） |
| created_at      | datetime | 登録日時                |

### Passphrase

| フィールド      | 型       | 説明                   |
| --------------- | -------- | ---------------------- |
| id              | int      | PK                     |
| public_id       | str      | 公開ID                 |
| speaker_id      | int      | FK to Speaker          |
| voice_sample_id | int      | FK to VoiceSample      |
| phrase          | str      | 正規化済みパスフレーズ |
| created_at      | datetime | 登録日時               |

※ Passphraseは1人のSpeakerにつき最大3つまで登録可能

## API エンドポイント

| メソッド | パス                    | 説明                                           |
| -------- | ----------------------- | ---------------------------------------------- |
| POST     | `/api/v1/auth/register` | 話者登録（音声ファイル + パスフレーズ + 声紋） |
| POST     | `/api/v1/auth/verify`   | 認証（1:1照合）                                |
| POST     | `/api/v1/auth/identify` | 識別（1:N照合）                                |

## API 詳細

### POST /api/v1/auth/register

話者の登録。音声ファイルを保存し、パスフレーズと声紋を抽出して保存する。

**リクエスト:**

```json
{
  "speaker_id": "user123",
  "speaker_name": "山田太郎",
  "audio_data": "base64エンコードされた音声データ",
  "audio_format": "wav"
}
```

**レスポンス:**

```json
{
  "speaker_id": "user123",
  "speaker_name": "山田太郎",
  "voice_sample_id": "vs_abc123",
  "voiceprint_id": "vp_xyz789",
  "passphrase": "こんにちは世界",
  "status": "registered"
}
```

### POST /api/v1/auth/verify

1:1認証。指定した話者との照合を行う。

**リクエスト:**

```json
{
  "speaker_id": "user123",
  "audio_data": "base64エンコードされた音声データ",
  "audio_format": "wav"
}
```

**レスポンス:**

```json
{
  "authenticated": true,
  "speaker_id": "user123",
  "passphrase_match": true,
  "voice_similarity": 0.85,
  "message": "認証成功"
}
```

### POST /api/v1/auth/identify

1:N識別。登録済み話者の中から最も類似する話者を特定する。

**リクエスト:**

```json
{
  "audio_data": "base64エンコードされた音声データ",
  "audio_format": "wav"
}
```

**レスポンス:**

```json
{
  "identified": true,
  "speaker_id": "user123",
  "speaker_name": "山田太郎",
  "passphrase_match": true,
  "voice_similarity": 0.85,
  "message": "識別成功"
}
```

## テキスト正規化ルール

パスフレーズの比較時に適用する正規化処理:

1. **小文字化**: 大文字→小文字に変換
2. **句読点除去**: 句読点・記号を削除
3. **空白正規化**: 連続空白→単一空白、前後の空白をトリム

```python
def normalize_text(text: str) -> str:
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = ' '.join(text.split())
    return text
```

**例:**

| 入力                   | 正規化後           |
| ---------------------- | ------------------ |
| `"Hello, World!"`      | `"hello world"`    |
| `"こんにちは、世界！"` | `"こんにちは世界"` |
| `"  test   test  "`    | `"test test"`      |

## 声紋照合の詳細

### Resemblyzer

- **出力**: 256次元の特徴量ベクトル
- **類似度計算**: コサイン類似度（内積）
- **しきい値**: 0.75（調整可能）

```python
from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np

encoder = VoiceEncoder()

# 声紋抽出
wav = preprocess_wav(audio_path)
embedding = encoder.embed_utterance(wav)  # shape: (256,)

# 類似度計算
similarity = np.dot(embedding1, embedding2)  # -1.0 ~ 1.0
is_same_speaker = similarity >= 0.75
```
