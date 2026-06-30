# ====================================================
# Gujarati Paragraph Compare Pro
# utils/similarity.py — Similarity Calculator Module (v2)
# ====================================================
# Accurate pairwise similarity using SequenceMatcher with
# autojunk=False and Unicode-NFC-normalized tokens.
# ====================================================

from difflib import SequenceMatcher
from typing import Dict, List, Optional

from utils.parser import TextParser


class SimilarityCalculator:
    """
    Accurate similarity calculator for Gujarati text.

    Accuracy improvements over v1:
        - Uses autojunk=False so SequenceMatcher doesn't discard
          frequently-repeated Gujarati particles / postpositions.
        - Character, word, and sentence-level modes.
        - All text goes through Unicode NFC normalization via TextParser.
    """

    def __init__(self, parser: Optional[TextParser] = None):
        """
        Args:
            parser: TextParser instance (creates default if None).
        """
        self._parser = parser if parser is not None else TextParser()

    # ------------------------------------------------
    # Properties
    # ------------------------------------------------

    @property
    def parser(self) -> TextParser:
        return self._parser

    @parser.setter
    def parser(self, value: TextParser) -> None:
        self._parser = value

    # ------------------------------------------------
    # Core Similarity Methods
    # ------------------------------------------------

    def character_similarity(self, text_a: str, text_b: str) -> float:
        """Character-level similarity ratio (0.0 – 1.0)."""
        norm_a = self._parser.normalize(text_a)
        norm_b = self._parser.normalize(text_b)

        if not norm_a and not norm_b:
            return 1.0
        if not norm_a or not norm_b:
            return 0.0

        return SequenceMatcher(None, norm_a, norm_b, autojunk=False).ratio()

    def word_similarity(self, text_a: str, text_b: str) -> float:
        """Word-level similarity ratio (0.0 – 1.0)."""
        words_a = self._parser.tokenize_words(text_a)
        words_b = self._parser.tokenize_words(text_b)

        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0

        return SequenceMatcher(None, words_a, words_b, autojunk=False).ratio()

    def sentence_similarity(self, text_a: str, text_b: str) -> float:
        """Sentence-level similarity ratio (0.0 – 1.0)."""
        sents_a = self._parser.tokenize_sentences(text_a)
        sents_b = self._parser.tokenize_sentences(text_b)

        if not sents_a and not sents_b:
            return 1.0
        if not sents_a or not sents_b:
            return 0.0

        return SequenceMatcher(None, sents_a, sents_b, autojunk=False).ratio()

    # ------------------------------------------------
    # Pairwise 3-Way Similarity
    # ------------------------------------------------

    def compute_pairwise_similarity(
        self,
        text_a: str,
        text_b: str,
        text_c: str,
        mode: str = 'word',
    ) -> Dict[str, float]:
        """
        Pairwise similarity ratios (0.0 – 1.0) for A↔B, A↔C, B↔C.

        Args:
            text_a, text_b, text_c: The three paragraphs.
            mode: 'character', 'word', or 'sentence'.

        Returns:
            Dict with keys 'a_vs_b', 'a_vs_c', 'b_vs_c'.
        """
        func = self._get_similarity_function(mode)
        return {
            'a_vs_b': func(text_a, text_b),
            'a_vs_c': func(text_a, text_c),
            'b_vs_c': func(text_b, text_c),
        }

    def compute_pairwise_percentage(
        self,
        text_a: str,
        text_b: str,
        text_c: str,
        mode: str = 'word',
    ) -> Dict[str, float]:
        """Same as compute_pairwise_similarity but returns 0–100 percentages."""
        ratios = self.compute_pairwise_similarity(text_a, text_b, text_c, mode)
        return {k: round(v * 100, 2) for k, v in ratios.items()}

    # ------------------------------------------------
    # Detailed Report
    # ------------------------------------------------

    def detailed_report(
        self,
        text_a: str,
        text_b: str,
        text_c: str,
    ) -> Dict[str, Dict[str, float]]:
        """
        Full similarity report across all three modes.

        Returns:
            Nested dict: { mode: { pair: percentage } }
        """
        return {
            'character': self.compute_pairwise_percentage(
                text_a, text_b, text_c, 'character'
            ),
            'word': self.compute_pairwise_percentage(
                text_a, text_b, text_c, 'word'
            ),
            'sentence': self.compute_pairwise_percentage(
                text_a, text_b, text_c, 'sentence'
            ),
        }

    # ------------------------------------------------
    # Common / Unique Words
    # ------------------------------------------------

    def find_common_words(self, text_a: str, text_b: str) -> List[str]:
        """Words that appear in both texts."""
        set_a = set(self._parser.tokenize_words(text_a))
        set_b = set(self._parser.tokenize_words(text_b))
        return sorted(set_a & set_b)

    def find_unique_words(self, text_a: str, text_b: str) -> Dict[str, List[str]]:
        """Words unique to each text."""
        set_a = set(self._parser.tokenize_words(text_a))
        set_b = set(self._parser.tokenize_words(text_b))
        return {
            'only_in_a': sorted(set_a - set_b),
            'only_in_b': sorted(set_b - set_a),
        }

    # ------------------------------------------------
    # Private Helpers
    # ------------------------------------------------

    def _get_similarity_function(self, mode: str):
        """Return the similarity function for the given mode."""
        funcs = {
            'character': self.character_similarity,
            'word': self.word_similarity,
            'sentence': self.sentence_similarity,
        }
        if mode not in funcs:
            raise ValueError(
                f"Invalid mode: '{mode}'. Choose from: {list(funcs.keys())}"
            )
        return funcs[mode]

    def __repr__(self) -> str:
        return f"SimilarityCalculator(parser={self._parser!r})"
