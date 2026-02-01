"""プロンプト生成サービス.

声紋登録用のバランスド・プロンプト（4桁の数字列）を生成する。
0〜9が各2回出現する4桁×5セットを生成。
"""

import random


def generate_balanced_prompts() -> list[str]:
    """バランスド・プロンプトを生成する.

    0〜9の各数字が全体で2回ずつ出現する4桁×5セットを生成。
    合計20桁（4桁×5セット）で、各数字が2回ずつ（10種類×2回=20）となる。

    Returns:
        list[str]: 4桁の数字列5つのリスト
        例: ["4326", "8105", "9718", "5029", "3674"]
    """
    # 0〜9を2回ずつ含むリストを作成（合計20個）
    digits = list("0123456789" * 2)

    # シャッフルしてランダムに配置
    random.shuffle(digits)

    # 4桁ずつに分割して5セット作成
    prompts = []
    for i in range(5):
        start = i * 4
        end = start + 4
        prompts.append("".join(digits[start:end]))

    return prompts
