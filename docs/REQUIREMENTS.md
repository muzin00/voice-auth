# 要件定義書

> VCA Server - Voice Cognition Authentication Server

## 概要

音声によるランダムプロンプト認証システム。ユーザーが事前に登録した「数字（0〜9）」の音声データに基づき、認証時にランダムに指定される数字列（例：「4326」）を発声させることで、**「本人であるか（声紋）」** と **「正しい言葉を話しているか（ASR検証）」** を同時に検証する。

推論エンジンには `sherpa-onnx` を採用し、一般的な CPU 環境での低遅延動作を実現する。

## 認証方式

| 認証要素 | 種類                     | 判定基準                     |
| -------- | ------------------------ | ---------------------------- |
| 声紋     | 生体認証（What you are） | 類似度がしきい値以上         |
| 発話内容 | 知識認証（What you say） | ASRテキストがプロンプトと一致 |

### 認証ロジック

```
認証成功条件 = ASR一致 AND 声紋類似度 ≧ しきい値（0.75）
```

## 技術スタック

| コンポーネント       | 技術                        |
| -------------------- | --------------------------- |
| フレームワーク       | FastAPI                     |
| 音声区間検出 (VAD)   | sherpa-onnx (Silero VAD)    |
| 音声認識 (ASR)       | sherpa-onnx (Paraformer)    |
| 声紋抽出 (SV)        | sherpa-onnx (CAM++)         |
| データベース         | PostgreSQL / SQLite         |
| ストレージ           | GCS / ローカル              |
| 処理方式             | 同期処理                    |
| ハードウェア要件     | CPU（AVX命令セット対応推奨）|

### モデル役割

- **Silero VAD（VAD）**: 人の声が含まれる区間を検出、無音/環境音を除去
- **Paraformer（ASR）**: 発話内容のテキスト化、および各数字の発話タイミング（タイムスタンプ）の取得
- **CAM++（SV）**: 切り出された音声区間からの特徴ベクトル抽出（192次元）

## 認証フロー

```
プロンプト生成（例：「4326」）
       ↓
ユーザー音声入力
       ↓
┌──────────────────────────────────────┐
│  1. VAD検出（sherpa-onnx Silero VAD） │
│     → 人の声が含まれる区間を検出     │
│     → 無音/環境音なら即時リトライ    │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│  2. ASR検証（sherpa-onnx Paraformer） │
│     → 発話内容をテキスト化           │
│     → プロンプトと一致するか判定     │
│     → 不一致なら即時NG               │
│     → 各数字のタイムスタンプ取得     │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│  3. 声紋検証（sherpa-onnx CAM++）     │
│     → タイムスタンプで音声を分割     │
│     → 各数字の声紋ベクトル抽出       │
│     → 登録済みベクトルと類似度計算   │
│     → 平均スコア算出                 │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│  4. 認証判定                          │
│     └─ 平均類似度 ≧ 0.75 で成功      │
└──────────────────────────────────────┘
       ↓
   認証結果（成功 / 失敗）
```

## 機能要件

### 登録フェーズ（Enrollment）

ユーザーごとに「0〜9」の数字を**4桁×5セット（計20文字）**で発話させ、各数字2サンプルの平均ベクトルを登録する。バックアップ用PINも同時に登録する。

| ID     | 機能                     | 説明                                                              |
| ------ | ------------------------ | ----------------------------------------------------------------- |
| FR-1-1 | バランスド・プロンプト生成 | 0〜9が**各2回ずつ**出現する4桁×5セットを生成（例: 4326, 8105, ...）|
| FR-1-2 | 厳格なASR検証            | 認識テキスト≠プロンプトなら**即時破棄してリトライ**                |
| FR-1-3 | セグメンテーション       | Paraformerのタイムスタンプで連続発話を個別数字に切り出し           |
| FR-1-4 | ベクトル化               | 切り出した区間ごとにCAM++で声紋ベクトル（192次元）を抽出           |
| FR-1-5 | 重心計算（Centroid）     | 各数字2サンプルの**平均ベクトル**をマスター登録ベクトルとする      |
| FR-1-6 | PIN登録                  | 4桁数字をUI入力、**SHA-256ハッシュ化**して保存（バックアップ認証用）|
| FR-1-7 | 保存                     | speaker_idに紐づけて数字別ベクトル（計10個）とPINハッシュを保存    |

#### 登録処理フロー

```
1. プロンプト生成
   → ["4326", "8105", "9718", "5029", "3674"] (0〜9が各2回)

2. 5セット分ループ (i = 0 to 4):
   ┌─────────────────────────────────────────┐
   │  While True (リトライループ):            │
   │    音声入力 → Paraformer ASR            │
   │    IF 認識テキスト ≠ プロンプト:         │
   │      → エラー表示、再録音               │
   │    ELSE:                                │
   │      → タイムスタンプで4分割            │
   │      → 各断片をCAM++でベクトル化        │
   │      → temp_vectors[digit].append()    │
   │      → Break (次のセットへ)             │
   └─────────────────────────────────────────┘

3. 重心計算:
   FOR digit in 0〜9:
     final_vector[digit] = mean(temp_vectors[digit])  # 2サンプル平均

4. PIN登録:
   → UIでPIN入力 → SHA-256ハッシュ化

5. DB保存:
   → speaker_id, final_vectors, hashed_pin を保存
```

#### 登録時の制約

| 項目           | 制約                                                         |
| -------------- | ------------------------------------------------------------ |
| リトライ上限   | 1プロンプトに対し5回連続失敗で警告、フローやり直し           |
| 録音時間       | 1秒未満 or 10秒以上はエラー                                  |
| 無音検知       | VAD有効化、無音ファイルはASRに渡さない                       |

### 認証フェーズ（Authentication）

ランダムな数字列を提示し、リアルタイムで検証を行う。

| ID     | 機能           | 説明                                                          |
| ------ | -------------- | ------------------------------------------------------------- |
| FR-2-1 | プロンプト生成 | ランダムな数字列（4〜6桁）を生成・提示                         |
| FR-2-2 | 音声取得       | マイクまたはファイルからユーザー音声を取得                     |
| FR-2-3 | ASR検証        | Paraformerでテキスト化し、プロンプトと一致するか判定           |
| FR-2-4 | タイムスタンプ | ASRで各数字の発話タイミングを取得                              |
| FR-2-5 | 音声分割       | タイムスタンプに基づき各数字の音声区間を切り出し               |
| FR-2-6 | 声紋照合       | 切り出した音声と登録済みベクトルのコサイン類似度を計算         |
| FR-2-7 | スコア算出     | 全数字の類似度から平均スコアを算出                             |
| FR-2-8 | 認証判定       | ASR一致 AND 平均スコア ≧ 0.75 で成功                           |

### その他機能

| ID   | 機能     | 説明                                   |
| ---- | -------- | -------------------------------------- |
| FR-3 | 話者識別 | 登録済み話者から最も類似する話者を特定 |
| FR-4 | デモ画面 | 音声登録・認証のデモUI（1画面）        |

## エッジケースと対策

| 項目           | 課題                                                    | 対策                                                                    |
| -------------- | ------------------------------------------------------- | ----------------------------------------------------------------------- |
| 読みの揺れ     | 「0」を「ゼロ/レイ/マル」、「7」を「ナナ/シチ」と読む   | 正規化ロジック：ASR結果を数字記号に変換する辞書マッピングを実装         |
| 無音・ノイズ   | 発話の前後に長い無音や環境音が入る                      | sherpa-onnx内蔵のVAD（Voice Activity Detection）を有効にし発話区間のみ処理 |
| 早口・遅口     | ユーザーによって話す速度が違う                          | Paraformerのタイムスタンプ機能により動的に区間を切り出すため自動対応    |
| 声紋不一致     | ASRは正解したが声紋スコアが低い                         | なりすまし（録音再生など）の可能性が高いため認証失敗とする              |

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
   └── (N) DigitVoiceprint ─────┘
              │
              └── digit: "0"〜"9"
```

### Speaker

| フィールド   | 型          | 説明                              |
| ------------ | ----------- | --------------------------------- |
| id           | int         | PK                                |
| public_id    | str         | 公開ID                            |
| speaker_id   | str         | ユーザー識別子                    |
| speaker_name | str \| None | 話者名                            |
| pin_hash     | str \| None | バックアップPIN（SHA-256ハッシュ）|
| created_at   | datetime    | 作成日時                          |
| updated_at   | datetime    | 更新日時                          |

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

### DigitVoiceprint

数字ごとの声紋ベクトルを保存する。1ユーザーにつき10個（0〜9）のレコードを持つ。

| フィールド      | 型       | 説明                           |
| --------------- | -------- | ------------------------------ |
| id              | int      | PK                             |
| public_id       | str      | 公開ID                         |
| speaker_id      | int      | FK to Speaker                  |
| voice_sample_id | int      | FK to VoiceSample              |
| digit           | str      | 数字（"0"〜"9"）               |
| embedding       | bytes    | 声紋ベクトル（192次元）        |
| created_at      | datetime | 登録日時                       |

**ユニーク制約:** (speaker_id, digit) の組み合わせでユニーク

### データ構造例（JSON形式）

```json
{
  "user_id": "user_123456",
  "created_at": "2024-01-01T10:00:00",
  "auth_data": {
    "voice_embeddings": {
      "0": [0.123, -0.567, ...],
      "1": [0.890, 0.112, ...],
      "2": [...],
      ...
      "9": [-0.445, 0.998, ...]
    },
    "backup_pin_hash": "e3b0c44298fc1c149afbf4c8996fb924..."
  },
  "metadata": {
    "model_version": "cam++_v1",
    "sample_rate": 16000
  }
}
```

## API エンドポイント

| メソッド | パス                              | 説明                                   |
| -------- | --------------------------------- | -------------------------------------- |
| GET      | `/api/v1/auth/enrollment/prompt`  | 登録用バランスド・プロンプト生成       |
| POST     | `/api/v1/auth/enrollment/audio`   | 登録用音声送信（1セット分）            |
| POST     | `/api/v1/auth/enrollment/pin`     | PIN登録                                |
| POST     | `/api/v1/auth/enrollment/complete`| 登録完了・ベクトル確定                 |
| GET      | `/api/v1/auth/prompt`             | 認証用プロンプト生成                   |
| POST     | `/api/v1/auth/verify`             | 認証（ASR + 声紋照合）                 |
| POST     | `/api/v1/auth/verify-pin`         | PIN認証（バックアップ）                |
| POST     | `/api/v1/auth/identify`           | 識別（1:N照合）                        |

## API 詳細

### GET /api/v1/auth/enrollment/prompt

登録用のバランスド・プロンプト（0〜9が各2回出現する4桁×5セット）を生成する。

**クエリパラメータ:**

| パラメータ  | 型  | 必須 | 説明             |
| ----------- | --- | ---- | ---------------- |
| speaker_id  | str | Yes  | ユーザー識別子   |

**レスポンス:**

```json
{
  "speaker_id": "user123",
  "enrollment_id": "enr_abc123",
  "prompts": ["4326", "8105", "9718", "5029", "3674"],
  "total_sets": 5,
  "current_set": 0
}
```

### POST /api/v1/auth/enrollment/audio

登録用音声を1セット分送信し、ASR検証を行う。

**リクエスト:**

```json
{
  "enrollment_id": "enr_abc123",
  "set_index": 0,
  "prompt": "4326",
  "audio_data": "base64エンコードされた音声データ",
  "audio_format": "wav"
}
```

**レスポンス（成功）:**

```json
{
  "success": true,
  "asr_result": "4326",
  "set_index": 0,
  "remaining_sets": 4,
  "message": "OK！次へ進みます"
}
```

**レスポンス（ASR不一致）:**

```json
{
  "success": false,
  "asr_result": "4327",
  "set_index": 0,
  "retry_count": 1,
  "max_retries": 5,
  "message": "聞き取れませんでした。もう一度、はっきりとお願いします"
}
```

### POST /api/v1/auth/enrollment/pin

バックアップ用PINを登録する。

**リクエスト:**

```json
{
  "enrollment_id": "enr_abc123",
  "pin": "1234"
}
```

**レスポンス:**

```json
{
  "success": true,
  "message": "PINを登録しました"
}
```

### POST /api/v1/auth/enrollment/complete

5セット分の音声とPINが揃った後、重心計算を行い登録を確定する。

**リクエスト:**

```json
{
  "enrollment_id": "enr_abc123"
}
```

**レスポンス:**

```json
{
  "speaker_id": "user123",
  "registered_digits": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
  "has_pin": true,
  "status": "registered"
}
```

### GET /api/v1/auth/prompt

認証用のランダムプロンプト（数字列）を生成する。

**クエリパラメータ:**

| パラメータ | 型  | 必須 | 説明                               |
| ---------- | --- | ---- | ---------------------------------- |
| length     | int | No   | 数字列の長さ（デフォルト4、範囲4〜6）|

**レスポンス:**

```json
{
  "prompt": "4326",
  "prompt_id": "p_abc123",
  "expires_at": "2024-01-01T12:00:30Z"
}
```

### POST /api/v1/auth/verify

1:1認証。プロンプトに対する発話音声を検証する。

1. ASRでテキスト化し、プロンプトと一致するか確認
2. 各数字のタイムスタンプで音声を分割
3. 各数字の声紋を登録済みベクトルと照合
4. ASR一致 AND 平均類似度 ≧ 0.75 で認証成功

**リクエスト:**

```json
{
  "speaker_id": "user123",
  "prompt": "4326",
  "audio_data": "base64エンコードされた音声データ",
  "audio_format": "wav"
}
```

**レスポンス（成功）:**

```json
{
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

**レスポンス（ASR不一致）:**

```json
{
  "authenticated": false,
  "speaker_id": "user123",
  "asr_result": "4327",
  "asr_matched": false,
  "voice_similarity": null,
  "digit_scores": null,
  "message": "発話内容がプロンプトと一致しません"
}
```

**レスポンス（声紋不一致）:**

```json
{
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
  "message": "声紋が一致しません"
}
```

### POST /api/v1/auth/identify

1:N識別。登録済み話者の中から最も類似する話者を特定する。

**リクエスト:**

```json
{
  "prompt": "4326",
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
  "asr_result": "4326",
  "asr_matched": true,
  "voice_similarity": 0.85,
  "message": "識別成功"
}
```

### POST /api/v1/auth/verify-pin

PIN認証（バックアップ認証）。声紋認証が失敗した場合や利用できない場合の代替手段。

**リクエスト:**

```json
{
  "speaker_id": "user123",
  "pin": "1234"
}
```

**レスポンス（成功）:**

```json
{
  "authenticated": true,
  "speaker_id": "user123",
  "auth_method": "pin",
  "message": "PIN認証成功"
}
```

**レスポンス（失敗）:**

```json
{
  "authenticated": false,
  "speaker_id": "user123",
  "auth_method": "pin",
  "message": "PINが一致しません"
}
```

## デモ画面（FR-4）

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

| ID     | 機能                   | 説明                                                |
| ------ | ---------------------- | --------------------------------------------------- |
| FR-4-1 | 音声入力（マイク）     | ブラウザのMediaRecorder APIで録音                   |
| FR-4-2 | 音声入力（ファイル）   | wav/mp3/m4a等の音声ファイルをアップロード           |
| FR-4-3 | 登録プロンプト表示     | 現在のプロンプト + 進捗（1/5回目）を表示            |
| FR-4-4 | 登録フィードバック     | ASR成功時「OK！」、失敗時「もう一度お願いします」   |
| FR-4-5 | PIN設定画面            | 音声登録完了後、4桁PIN入力（確認含め2回）           |
| FR-4-6 | 認証プロンプト表示     | ランダムな数字列を画面に表示                        |
| FR-4-7 | 認証デモ               | speaker_id入力 + プロンプト発話音声で認証           |
| FR-4-8 | PIN認証フォールバック  | 声紋認証失敗時にPIN入力で代替認証                   |
| FR-4-9 | 結果表示               | ASR結果・声紋スコア・認証結果をリアルタイム表示     |

### 画面構成（登録）

```
┌─────────────────────────────────────────────────────────────┐
│                    VCA 話者登録                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐        │
│  │   Speaker ID: [____________]                    │        │
│  │   Name:       [____________]                    │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           進捗: ● ● ○ ○ ○  (2 / 5 回目)         │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           「 8  1  0  5 」                       │        │
│  │           ↑ 大きく表示                          │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           [🎤 押しながら話す]                   │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │  フィードバック:                                 │        │
│  │  ✓ OK！次へ進みます / ✗ もう一度お願いします    │        │
│  └─────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘

（5セット完了後 → PIN設定画面へ）

┌─────────────────────────────────────────────────────────────┐
│                    PIN設定                                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐        │
│  │   4桁のPINを入力してください                    │        │
│  │   PIN:     [____]                               │        │
│  │   確認:    [____]                               │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           [登録完了]                             │        │
│  └─────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### 画面構成（認証）

```
┌─────────────────────────────────────────────────────────────┐
│                    VCA 認証                                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐        │
│  │   Speaker ID: [____________]                    │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           「 4  3  2  6 」を発話してください     │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           [🎤 録音開始]                         │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │  結果:                                          │        │
│  │  - ASR: 4326 ✓                                  │        │
│  │  - 声紋スコア: 0.82 (4:0.85, 3:0.79, 2:0.81, 6:0.83) │   │
│  │  - 認証: 成功 ✓                                 │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │  [PIN認証に切り替え] （声紋認証失敗時）         │        │
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

## 音声処理の詳細

### sherpa-onnx (Silero VAD) - 音声区間検出

VAD（Voice Activity Detection）は音声処理パイプラインの**最初に配置する必須コンポーネント**。

#### VADの役割

| 工程 | 役割 | 防ぐ問題 |
|------|------|----------|
| ASR前処理 | 人が喋っている区間だけをParaformerに渡す | 無音/環境音でAIが**幻覚（ハルシネーション）**を起こすのを防止 |
| 切り出し精度向上 | 録音開始〜発話開始までの「間」を自動カット | 喋り出しの瞬間をより正確に検知 |

#### なぜ必須か

- Paraformerに長い無音や環境ノイズだけの音声を入力すると、無理やり言葉を探して誤認識する
- 例: エアコンの音 → 「あ」と誤認識
- VADが抜けると、環境音を「1」と誤認して学習してしまうリスクがある

#### 実装コード

```python
import sherpa_onnx

# VADの設定（Silero VADベース）
vad_config = sherpa_onnx.VadModelConfig()
vad_config.silero_vad.model_path = "silero_vad.onnx"
vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=60)

def process_audio(audio_data):
    # まずVADに通す
    if not vad.is_speech(audio_data):
        return None  # 人の声じゃないなら捨てる（ASRに渡さない）

    # 声と判定されたら Paraformer へ
    text = recognizer.decode(audio_data)
    return text
```

#### モデル

- **Silero VAD**: sherpa-onnxに組み込み済みの高精度VADモデル
- **モデルファイル**: `silero_vad.onnx`

### sherpa-onnx (Paraformer) - 音声認識

- **モデル**: Paraformer（量子化済み ONNX モデル推奨）
- **役割**:
  - 発話内容のテキスト化
  - 各数字の発話タイミング（タイムスタンプ）の取得
- **対応言語**: 日本語/中国語
- **参考リンク**:
  - [sherpa-onnx ASR models](https://github.com/k2-fsa/sherpa-onnx/releases)

```python
import sherpa_onnx

# Paraformer ASR設定
recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
    paraformer="/path/to/paraformer.onnx",
    tokens="/path/to/tokens.txt",
    num_threads=2,
)

# 音声認識（タイムスタンプ付き）
stream = recognizer.create_stream()
stream.accept_waveform(sample_rate, samples)
recognizer.decode(stream)
result = stream.result

# result.text: 認識テキスト
# result.timestamps: 各トークンのタイムスタンプ
```

### sherpa-onnx (CAM++) - 声紋抽出

- **モデル**: CAM++ (`3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx`)
- **出力**: 192次元の特徴量ベクトル
- **類似度計算**: コサイン類似度
- **しきい値**: 0.75（ランダムプロンプト認証用）
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
is_same_speaker = score >= 0.75
```

### セグメンテーション時のマージン処理

ASRが出力するタイムスタンプは「人間が文字として認識できる最小限の範囲」を指すため、そのまま切り出すとCAM++にとって不都合が生じる。

#### マージンが必要な理由

| 問題 | 説明 |
|------|------|
| 語頭の欠損（Attack） | 「よん」の「Y」等の子音立ち上がりはエネルギーが弱くASRが切り捨てる。発声の癖が消える |
| 語尾の余韻（Decay） | 息の抜け方・声の響きの残りも声紋情報だがASRはバッサリ切る |
| クリックノイズ | 振幅が大きい場所で切ると「プチッ」音が発生しCAM++に悪影響 |

#### 推奨値

- **前の余白（Pre-padding）**: 50ms〜100ms
- **後ろの余白（Post-padding）**: 50ms〜100ms

#### 実装コード

```python
import numpy as np

def cut_segment_with_padding(audio_array, sample_rate, start_sec, end_sec, padding_sec=0.1):
    """
    音声配列から、指定した時間をマージン付きで切り出す関数

    Args:
        audio_array (np.array): 元の音声データ (1次元配列)
        sample_rate (int): サンプリングレート (例: 16000)
        start_sec (float): Paraformerが検知した開始時間 (秒)
        end_sec (float): Paraformerが検知した終了時間 (秒)
        padding_sec (float): 追加する余白の時間 (秒) デフォルト0.1秒

    Returns:
        np.array: 切り出された音声データ
    """
    # 秒数をサンプル数に変換
    start_index = int(start_sec * sample_rate)
    end_index = int(end_sec * sample_rate)
    pad_samples = int(padding_sec * sample_rate)

    # マージンを適用
    new_start = start_index - pad_samples
    new_end = end_index + pad_samples

    # 安全装置（配列の範囲外に出ないように）
    new_start = max(0, new_start)
    new_end = min(len(audio_array), new_end)

    return audio_array[new_start:new_end]

# 使用例
segment_4 = cut_segment_with_padding(
    audio_array=audio_data,
    sample_rate=16000,
    start_sec=0.52,
    end_sec=0.88,
    padding_sec=0.08  # 80msの余白
)
```

#### 注意：隣の数字との衝突

早口の場合、余白を広げると隣の数字と重複する可能性がある。

```python
# 次の数字の開始時間を超えないようにする
safe_end = min(end_sec + padding_sec, next_start_sec)
```

ただし「4桁×5回」の登録フローでは、早口すぎる場合はASRが失敗してリトライになるため、厳密な対応は不要。

### 認証パイプライン

```
入力: 音声波形, プロンプト "4326"
           ↓
┌──────────────────────────────────────┐
│  1. Paraformer ASR処理                │
│     → テキスト: "4326"               │
│     → タイムスタンプ: [(0.1,0.3), (0.4,0.6), ...]  │
│     → "4326" と一致しなければ即時NG  │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  2. 音声セグメント切り出し            │
│     → "4": samples[start_4:end_4]    │
│     → "3": samples[start_3:end_3]    │
│     → ...                            │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  3. CAM++ 声紋照合（各数字）          │
│     → embed_4 = CAM++(segment_4)     │
│     → score_4 = cosine(embed_4, registered_4)  │
│     → 全数字について繰り返し         │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  4. 最終判定                          │
│     → avg_score = mean(scores)       │
│     → avg_score >= 0.75 なら認証成功 │
└──────────────────────────────────────┘
```
