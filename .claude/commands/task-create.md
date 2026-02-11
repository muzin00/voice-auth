# タスク作成ワークフロー

AI エージェントが一連のワークフローに沿ってタスクを遂行します。

## ワークフロー

### Phase 1: タスクのヒアリング

1. ユーザーにタスクの内容を質問:
   - **タイトル**: 何をするか（簡潔に）
   - **説明**: 詳細な要件、背景、期待する結果

2. 内容を確認し、不明点があれば追加で質問

### Phase 2: 環境準備

1. タスク内容からブランチ名を自動生成:
   - 新機能: `feature/<slug>`
   - バグ修正: `fix/<slug>`
   - リファクタリング: `refactor/<slug>`
   - その他: `chore/<slug>`

2. git worktree を作成:
   ```bash
   git worktree add ../<repo>-<branch-slug> -b <branch-name>
   ```

3. ユーザーに worktree への移動を案内

### Phase 3: 実装

1. やりたいことを入念にヒアリング:
   - 技術的な要件
   - 制約条件
   - 優先順位

2. 実装方針を提案し、ユーザーの承認を得る

3. 承認後、実装を進める

4. 実装中も必要に応じて確認を取る

### Phase 4: 完了

ユーザーから「完了」の報告を受けたら:

1. 変更内容を確認:
   ```bash
   git status
   git diff
   ```

2. コミット:
   ```bash
   git add <files>
   git commit -m "<conventional commit message>"
   ```

3. main ブランチにマージ:
   ```bash
   git checkout main
   git merge <branch-name>
   ```

4. worktree とブランチを削除:
   ```bash
   git worktree remove ../<worktree-dir>
   git branch -d <branch-name>
   ```

5. 完了報告

## 開始

「タスクの内容を教えてください。何を実装・修正したいですか？」と質問してワークフローを開始してください。
