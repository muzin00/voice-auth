"""プロンプト生成のテスト."""

from collections import Counter

from vca_auth.services.prompt_generator import generate_balanced_prompts


class TestGenerateBalancedPrompts:
    """バランスド・プロンプト生成のテスト."""

    def test_generates_5_sets(self):
        """5セット生成されること."""
        prompts = generate_balanced_prompts()
        assert len(prompts) == 5

    def test_each_set_has_4_digits(self):
        """各セットが4桁であること."""
        prompts = generate_balanced_prompts()
        for prompt in prompts:
            assert len(prompt) == 4
            assert prompt.isdigit()

    def test_each_digit_appears_twice(self):
        """各数字（0〜9）が全体で2回ずつ出現すること."""
        prompts = generate_balanced_prompts()
        all_digits = "".join(prompts)

        counter = Counter(all_digits)

        # 0〜9の各数字が2回ずつ出現
        for digit in "0123456789":
            assert counter[digit] == 2, f"Digit {digit} appears {counter[digit]} times"

    def test_total_digits_is_20(self):
        """合計20桁（4桁×5セット）であること."""
        prompts = generate_balanced_prompts()
        all_digits = "".join(prompts)
        assert len(all_digits) == 20

    def test_randomness(self):
        """異なる呼び出しで異なる結果が生成されること（確率的）."""
        results = [generate_balanced_prompts() for _ in range(10)]
        unique_results = {tuple(r) for r in results}
        # 10回呼び出して少なくとも2種類以上の結果が出ること
        assert len(unique_results) >= 2

    def test_all_digits_are_valid(self):
        """すべての文字が0〜9の数字であること."""
        prompts = generate_balanced_prompts()
        for prompt in prompts:
            for char in prompt:
                assert char in "0123456789"
