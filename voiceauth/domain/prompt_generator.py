"""Prompt generator for enrollment and verification.

Generates random digit prompts for voice enrollment and verification.
"""

import random


class PromptGenerator:
    """Generates random digit prompts for voice enrollment."""

    NUM_SETS = 5
    DIGITS_PER_SET = 4

    def __init__(self, seed: int | None = None) -> None:
        """Initialize generator with optional seed.

        Args:
            seed: Random seed for reproducibility.
        """
        self._rng = random.Random(seed)

    def generate(self) -> list[str]:
        """Generate 5 random 4-digit prompts.

        Each prompt has no consecutive duplicate digits.

        Returns:
            List of 5 four-digit strings.
        """
        prompts: list[str] = []
        for _ in range(self.NUM_SETS):
            digits: list[str] = []
            for j in range(self.DIGITS_PER_SET):
                d = str(self._rng.randint(0, 9))
                if j > 0:
                    while d == digits[-1]:
                        d = str(self._rng.randint(0, 9))
                digits.append(d)
            prompts.append("".join(digits))
        return prompts


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
