# ADR-001: 声紋抽出ライブラリをsherpa-onnxに移行

**日付**: 2025-01-25

**ステータス**: 採用

## コンテキスト

Cloud Run上でのコールドスタート時間が長く、ユーザー体験を損なっていた。原因はwespeakerruntimeが依存するPyTorch/torchaudioの読み込みに約10秒かかることにあった。

## 決定

wespeakerruntime + torch + torchaudio から sherpa-onnx (CAM++) に移行する。

## 結果

| 項目 | 移行前 | 移行後 |
|------|--------|--------|
| ライブラリ | wespeakerruntime | sherpa-onnx |
| モデル | WeSpeaker ResNet34 | CAM++ |
| 埋め込み次元 | 256 | 192 |
| イメージサイズ | ~3GB | ~200MB |
| モデル読み込み時間 | ~10秒 | < 0.5秒 |

## トレードオフ

- 埋め込み次元が変わるため、既存の声紋データは再登録が必要
- モデルファイル（29.6MB）をDockerイメージに含める必要がある

## 参考リンク

- [HuggingFace: csukuangfj/speaker-embedding-models](https://huggingface.co/csukuangfj/speaker-embedding-models/tree/main)
- [3D-Speaker (CAM++)](https://github.com/modelscope/3D-Speaker)
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
