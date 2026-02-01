"""Balanced prompt generator for enrollment.

Generates 5 sets of 4-digit prompts where:
- Each digit (0-9) appears exactly twice
- No consecutive digits are the same within a set or between sets
"""

import random


class PromptGenerator:
    """Generates balanced digit prompts for voice enrollment."""

    NUM_SETS = 5
    DIGITS_PER_SET = 4
    OCCURRENCES_PER_DIGIT = 2
    MAX_ATTEMPTS = 1000

    def __init__(self, seed: int | None = None) -> None:
        """Initialize generator with optional seed.

        Args:
            seed: Random seed for reproducibility.
        """
        self._rng = random.Random(seed)

    def generate(self) -> list[str]:
        """Generate 5 balanced prompts.

        Returns:
            List of 5 four-digit strings where each digit 0-9 appears exactly twice.

        Raises:
            RuntimeError: If unable to generate valid prompts after max attempts.
        """
        for _ in range(self.MAX_ATTEMPTS):
            prompts = self._try_generate()
            if prompts is not None:
                return prompts

        raise RuntimeError(
            f"Failed to generate valid prompts after {self.MAX_ATTEMPTS} attempts"
        )

    def _try_generate(self) -> list[str] | None:
        """Attempt to generate valid prompts.

        Returns:
            List of prompts if successful, None otherwise.
        """
        # Create pool: each digit 0-9 appears exactly twice
        pool = list("01234567890123456789")
        self._rng.shuffle(pool)

        # Try to arrange into valid prompts
        prompts: list[str] = []
        remaining = pool.copy()

        for _ in range(self.NUM_SETS):
            prompt = self._build_prompt(remaining, prompts)
            if prompt is None:
                return None
            prompts.append(prompt)

        return prompts

    def _build_prompt(
        self,
        remaining: list[str],
        previous_prompts: list[str],
    ) -> str | None:
        """Build a single prompt avoiding consecutive duplicates.

        Args:
            remaining: Remaining digits to use.
            previous_prompts: Previously built prompts.

        Returns:
            A 4-digit prompt string, or None if impossible.
        """
        prompt_digits: list[str] = []

        # Get the last digit of previous prompt (if any) to avoid initial collision
        last_digit = previous_prompts[-1][-1] if previous_prompts else None

        for position in range(self.DIGITS_PER_SET):
            # Find valid candidates (not same as last digit)
            candidates = [
                (i, d)
                for i, d in enumerate(remaining)
                if d != last_digit and d not in prompt_digits[position:]
            ]

            if not candidates:
                # No valid candidate, try simpler approach
                candidates = [
                    (i, d) for i, d in enumerate(remaining) if d != last_digit
                ]

            if not candidates:
                return None

            # Pick a random valid candidate
            idx, digit = self._rng.choice(candidates)
            prompt_digits.append(digit)
            remaining.pop(idx)
            last_digit = digit

        return "".join(prompt_digits)


def generate_enrollment_prompts(seed: int | None = None) -> list[str]:
    """Generate enrollment prompts.

    Convenience function wrapping PromptGenerator.

    Args:
        seed: Optional random seed for reproducibility.

    Returns:
        List of 5 four-digit strings for enrollment.

    Example:
        >>> prompts = generate_enrollment_prompts()
        >>> len(prompts)
        5
        >>> all(len(p) == 4 for p in prompts)
        True
    """
    return PromptGenerator(seed).generate()


def generate_verification_prompt(
    length: int = 4,
    seed: int | None = None,
) -> str:
    """Generate a random prompt for verification.

    Args:
        length: Number of digits in the prompt (4-6).
        seed: Optional random seed for reproducibility.

    Returns:
        Random digit string for verification.

    Raises:
        ValueError: If length is not between 4 and 6.
    """
    if not 4 <= length <= 6:
        raise ValueError("Prompt length must be between 4 and 6")

    rng = random.Random(seed)
    digits = [str(rng.randint(0, 9)) for _ in range(length)]

    # Ensure no consecutive duplicates
    for i in range(1, len(digits)):
        while digits[i] == digits[i - 1]:
            digits[i] = str(rng.randint(0, 9))

    return "".join(digits)
