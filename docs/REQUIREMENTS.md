# 要件定義書

> VCA Server - Voice Cognition Authentication Server

## 概要

音声による声紋認証システム。声紋（生体認証）によりユーザーを識別・認証する。

## 認証方式

| 認証要素 | 種類                     | 判定基準             |
| -------- | ------------------------ | -------------------- |
| 声紋     | 生体認証（What you are） | 類似度がしきい値以上 |

### 認証ロジック

```
認証成功条件 = 声紋類似度 ≧ しきい値（0.4）
```

## 技術スタック

| コンポーネント | 技術                |
| -------------- | ------------------- |
| フレームワーク | FastAPI             |
| 声紋抽出       | sherpa-onnx (CAM++) |
| データベース   | PostgreSQL / SQLite |
| ストレージ     | GCS / ローカル      |
| 処理方式       | 同期処理            |

## 認証フロー

```
ユーザー音声入力
       ↓
┌──────────────────────────────────────┐
│  1. 声紋抽出（sherpa-onnx CAM++）     │
│     → 192次元特徴量ベクトル生成      │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│  2. 認証判定                          │
│     └─ 声紋類似度 ≧ 0.4 で成功       │
└──────────────────────────────────────┘
       ↓
   認証結果（成功 / 失敗）
```

## 機能要件

| ID   | 機能     | 説明                                      |
| ---- | -------- | ----------------------------------------- |
| FR-1 | 話者登録 | speaker_id、声紋を登録                    |
| FR-2 | 声紋抽出 | sherpa-onnx (CAM++) で192次元ベクトル抽出 |
| FR-3 | 声紋照合 | コサイン類似度でしきい値判定              |
| FR-4 | 認証判定 | 声紋類似度 ≧ 0.4 で成功                   |
| FR-5 | 話者識別 | 登録済み話者から最も類似する話者を特定    |
| FR-6 | デモ画面 | 音声登録・認証のデモUI（1画面）           |

## 依存パッケージ

```
sherpa-onnx
soundfile
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

| コンテナ   | 役割         | 主要パッケージ       |
| ---------- | ------------ | -------------------- |
| vca_api    | REST API     | FastAPI, sherpa-onnx |
| PostgreSQL | データベース | -                    |

### パッケージ構成

| パッケージ | 役割                                       |
| ---------- | ------------------------------------------ |
| vca_core   | インターフェース、モデル、ビジネスロジック |
| vca_api    | REST API（FastAPI）、デモ画面              |
| vca_infra  | DB/ストレージ実装                          |

### 処理フロー（話者登録）

```
クライアント
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  vca_api（APIコンテナ）                                  │
│  1. リクエスト受信                                       │
│  2. 音声データをストレージに保存                         │
│  3. 声紋抽出（sherpa-onnx）                              │
│  4. VoiceprintをDBに保存                                 │
│  5. レスポンス返却                                       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
クライアント
```

## データモデル

```
Speaker (1) ←─────────── (N) VoiceSample
   ↑                            ↑
   └── (N) Voiceprint ──────────┘
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
| embedding       | bytes    | 声紋ベクトル（192次元） |
| created_at      | datetime | 登録日時                |

## API エンドポイント

| メソッド | パス                    | 説明            |
| -------- | ----------------------- | --------------- |
| POST     | `/api/v1/auth/register` | 話者登録（声紋）|
| POST     | `/api/v1/auth/verify`   | 認証（1:1照合） |
| POST     | `/api/v1/auth/identify` | 識別（1:N照合） |

## API 詳細

### POST /api/v1/auth/register

話者の登録。音声ファイルを保存し、声紋を抽出して保存する。

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
  "voice_similarity": 0.85,
  "message": "識別成功"
}
```

## デモ画面（FR-6）

### 概要

音声認証システムの動作確認用デモUI。1画面で登録・認証の両機能をテストできる。

### 技術スタック

| 技術        | 用途                            |
| ----------- | ------------------------------- |
| htmx        | 非同期フォーム送信、部分DOM更新 |
| TailwindCSS | スタイリング（CDN経由）         |
| Jinja2      | テンプレートレンダリング        |
| Web Audio   | マイク録音（MediaRecorder API） |

### 機能要件

| ID     | 機能                 | 説明                                      |
| ------ | -------------------- | ----------------------------------------- |
| FR-6-1 | 音声入力（マイク）   | ブラウザのMediaRecorder APIで録音         |
| FR-6-2 | 音声入力（ファイル） | wav/mp3/m4a等の音声ファイルをアップロード |
| FR-6-3 | 話者登録デモ         | speaker_id入力 + 音声で登録APIを呼び出し  |
| FR-6-4 | 認証デモ             | speaker_id入力 + 音声で認証APIを呼び出し  |
| FR-6-5 | 結果表示             | 登録/認証結果をリアルタイムで画面に表示   |

### 画面構成

```
┌─────────────────────────────────────────────────────────────┐
│                    VCA Voice Auth Demo                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │   音声入力方法       │    │   話者情報          │        │
│  │ ○ マイク入力        │    │ Speaker ID: [____] │        │
│  │ ○ ファイルアップロード│    │ Name: [____]       │        │
│  └─────────────────────┘    └─────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           [録音開始] / [ファイル選択]            │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │      登録        │  │      認証        │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │                    結果表示                      │        │
│  │  - ステータス / 声紋類似度                       │        │
│  └─────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### エンドポイント

| メソッド | パス             | 説明                     |
| -------- | ---------------- | ------------------------ |
| GET      | `/demo/`         | デモ画面表示             |
| POST     | `/demo/register` | 登録デモ（HTML部分返却） |
| POST     | `/demo/verify`   | 認証デモ（HTML部分返却） |

### ファイル構成

```
packages/vca_api/vca_api/
├── templates/
│   └── demo/
│       ├── index.html           # メイン画面
│       └── partials/
│           └── result.html      # 結果表示（htmx部分更新用）
├── static/
│   └── js/
│       └── audio.js             # マイク録音・ファイル処理
└── routes/
    ├── auth.py
    └── demo.py                  # デモ用ルーティング
```

### 注意事項

- マイク入力はHTTPS環境（またはlocalhost）でのみ動作
- MediaRecorderは通常 `webm` 形式で録音
- ファイルアップロードはBase64エンコードしてAPIに送信

## 声紋照合の詳細

### sherpa-onnx (CAM++)

- **モデル**: CAM++ (`3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx`)
- **出力**: 192次元の特徴量ベクトル
- **類似度計算**: コサイン類似度
- **しきい値**: 0.4（調整可能）
- **モデル配布**: Dockerイメージに含める
- **参考リンク**:
  - [HuggingFace: csukuangfj/speaker-embedding-models](https://huggingface.co/csukuangfj/speaker-embedding-models/tree/main)
  - [3D-Speaker (CAM++)](https://github.com/modelscope/3D-Speaker)
  - [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)

```python
import sherpa_onnx
import soundfile as sf

# コンフィグの設定
config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
    model="/path/to/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx",
    num_threads=1,
    debug=False
)

# エクストラクタの初期化
extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)

# 音声の読み込み
samples, sample_rate = sf.read("audio.wav")

# 声紋抽出
stream = extractor.create_stream()
stream.accept_waveforms(sample_rate, samples)
embedding = extractor.compute(stream)  # shape: (192,)

# 類似度計算（コサイン類似度）
import numpy as np
score = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
is_same_speaker = score >= 0.4
```
