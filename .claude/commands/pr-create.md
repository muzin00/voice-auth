# Pull Request 作成

現在のブランチの変更を分析し、Pull Request を作成します。

## 手順

1. `git log main..HEAD` で現在のブランチのコミットを確認
2. `git diff main...HEAD` で変更内容を確認
3. 変更を分析して PR タイトルと説明を生成
4. `gh pr create` で PR を作成

## PR テンプレート

```markdown
## 概要

[変更の概要を1-2文で説明]

## 変更内容

- [変更点1]
- [変更点2]

## テスト

- [ ] 単体テストを追加/更新
- [ ] `make test` が通る
- [ ] `make typecheck` が通る

## 関連 Issue

closes #XXX
```

## 実行

ブランチの変更を分析して PR を作成してください。タイトルと説明を提案し、ユーザーが承認したら PR を作成します。
