"""Tests for prompt generator."""

from collections import Counter

import pytest
from vca_auth.services.prompt_generator import (
    PromptGenerator,
    generate_enrollment_prompts,
    generate_verification_prompt,
)


class TestPromptGenerator:
    """Tests for PromptGenerator class."""

    def test_generates_five_prompts(self) -> None:
        """Should generate exactly 5 prompts."""
        generator = PromptGenerator(seed=42)
        prompts = generator.generate()
        assert len(prompts) == 5

    def test_each_prompt_has_four_digits(self) -> None:
        """Each prompt should have exactly 4 digits."""
        generator = PromptGenerator(seed=42)
        prompts = generator.generate()
        for prompt in prompts:
            assert len(prompt) == 4
            assert prompt.isdigit()

    def test_each_digit_appears_exactly_twice(self) -> None:
        """Each digit 0-9 should appear exactly twice across all prompts."""
        generator = PromptGenerator(seed=42)
        prompts = generator.generate()

        all_digits = "".join(prompts)
        counter = Counter(all_digits)

        for digit in "0123456789":
            assert counter[digit] == 2, f"Digit {digit} appears {counter[digit]} times"

    def test_no_consecutive_duplicates_within_prompt(self) -> None:
        """No digit should repeat consecutively within a prompt."""
        generator = PromptGenerator(seed=42)
        prompts = generator.generate()

        for prompt in prompts:
            for i in range(len(prompt) - 1):
                assert prompt[i] != prompt[i + 1], f"Consecutive duplicate in {prompt}"

    def test_no_consecutive_duplicates_between_prompts(self) -> None:
        """Last digit of one prompt should not equal first digit of next prompt."""
        generator = PromptGenerator(seed=42)
        prompts = generator.generate()

        for i in range(len(prompts) - 1):
            last_digit = prompts[i][-1]
            first_digit = prompts[i + 1][0]
            assert last_digit != first_digit, (
                f"Consecutive duplicate between prompts: "
                f"{prompts[i]} -> {prompts[i + 1]}"
            )

    def test_reproducible_with_seed(self) -> None:
        """Same seed should produce same prompts."""
        gen1 = PromptGenerator(seed=123)
        gen2 = PromptGenerator(seed=123)

        assert gen1.generate() == gen2.generate()

    def test_different_seeds_produce_different_prompts(self) -> None:
        """Different seeds should produce different prompts."""
        gen1 = PromptGenerator(seed=1)
        gen2 = PromptGenerator(seed=2)

        # Not guaranteed to be different, but very likely
        # Run multiple times to ensure randomness
        assert gen1.generate() != gen2.generate()

    def test_multiple_generations_produce_valid_results(self) -> None:
        """Multiple generations should all produce valid results."""
        for seed in range(100):
            generator = PromptGenerator(seed=seed)
            prompts = generator.generate()

            # Verify basic constraints
            assert len(prompts) == 5
            all_digits = "".join(prompts)
            assert len(all_digits) == 20

            # Verify each digit appears twice
            counter = Counter(all_digits)
            for digit in "0123456789":
                assert counter[digit] == 2


class TestGenerateEnrollmentPrompts:
    """Tests for generate_enrollment_prompts function."""

    def test_convenience_function(self) -> None:
        """Should work as a convenience wrapper."""
        prompts = generate_enrollment_prompts(seed=42)
        assert len(prompts) == 5
        assert all(len(p) == 4 for p in prompts)

    def test_without_seed(self) -> None:
        """Should work without seed (random)."""
        prompts = generate_enrollment_prompts()
        assert len(prompts) == 5


class TestGenerateVerificationPrompt:
    """Tests for generate_verification_prompt function."""

    def test_default_length(self) -> None:
        """Should generate 4-digit prompt by default."""
        prompt = generate_verification_prompt(seed=42)
        assert len(prompt) == 4
        assert prompt.isdigit()

    def test_custom_lengths(self) -> None:
        """Should support lengths 4-6."""
        for length in [4, 5, 6]:
            prompt = generate_verification_prompt(length=length, seed=42)
            assert len(prompt) == length
            assert prompt.isdigit()

    def test_invalid_length_raises_error(self) -> None:
        """Should raise error for invalid lengths."""
        with pytest.raises(ValueError, match="must be between 4 and 6"):
            generate_verification_prompt(length=3)

        with pytest.raises(ValueError, match="must be between 4 and 6"):
            generate_verification_prompt(length=7)

    def test_no_consecutive_duplicates(self) -> None:
        """Should not have consecutive duplicate digits."""
        for seed in range(100):
            prompt = generate_verification_prompt(length=6, seed=seed)
            for i in range(len(prompt) - 1):
                assert prompt[i] != prompt[i + 1], f"Consecutive duplicate in {prompt}"

    def test_reproducible_with_seed(self) -> None:
        """Same seed should produce same prompt."""
        assert generate_verification_prompt(seed=42) == generate_verification_prompt(
            seed=42
        )
