# タスク作成ワークフロー

AI エージェントが一連のワークフローに沿ってタスクを遂行します。

## ワークフロー

### Phase 1: タスクのヒアリング

AskUserQuestion ツールを使い、1問ずつ質問する。各質問には選択肢を提示し、ユーザーは「Other」で任意の回答も可能。

1. **タスクタイプ** を質問:
   - 選択肢: 新機能 / バグ修正 / リファクタリング / その他

2. **タスク概要** を質問:
   - 何をしたいか簡潔に

3. 必要に応じて **追加の詳細** を質問

### Phase 2: 環境準備

1. タスクタイプに応じてブランチ名を自動生成:
   - 新機能: `feature/<slug>`
   - バグ修正: `fix/<slug>`
   - リファクタリング: `refactor/<slug>`
   - その他: `chore/<slug>`

2. git worktree を作成:
   ```bash
   git worktree add ../<repo>-<branch-slug> -b <branch-name>
   ```

3. 以降は worktree の絶対パスを使って操作する（ユーザーの移動は不要）

### Phase 3: 実装

1. 実装方針を提案し、ユーザーの承認を得る

2. 承認後、実装を進める

3. 実装中も必要に応じて AskUserQuestion で確認を取る

### Phase 4: 完了

ユーザーから「done」の報告を受けたら:

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

AskUserQuestion ツールでタスクタイプを質問し、ワークフローを開始する。
