# ====================================================
# Gujarati Paragraph Compare Pro
# utils/parser.py — Text Parser Module
# ====================================================
# Handles UTF-8 text loading, Unicode normalization (NFC),
# whitespace normalization, and Gujarati-aware word /
# sentence tokenization with punctuation separation.
# ====================================================

import re
import os
import unicodedata
from typing import List, Optional


class TextParser:
    """
    OOP text parser for Gujarati Unicode paragraphs.

    Key accuracy features:
        - Unicode NFC normalization (critical for Gujarati combining marks).
        - Punctuation-separated tokenization so "word," and "word"
          produce the same base token.
        - Proper Gujarati sentence-end detection (Purna Viram ।, ॥, etc.)
        - Configurable ignore-case, ignore-spaces, remove-special-chars.
    """

    # ------------------------------------------------
    # Compiled Regex Patterns (class-level, compiled once)
    # ------------------------------------------------

    # Universal sentence-ending punctuation
    SENTENCE_SPLIT_PATTERN = re.compile(
        r'(?<=[।॥.!?؟。،；：])\s+'
    )

    # Define common punctuation marks globally across languages
    PUNCT_STR = r'\.,\?!\;:\"\'\(\)\[\]\{\}\<\>।॥؟。،；：'

    # Word-level tokenizer: captures sequences of word characters or individual punctuation marks
    WORD_TOKEN_PATTERN = re.compile(
        rf'[^{PUNCT_STR}\s]+(?:-[^{PUNCT_STR}\s]+)*|[^\s]',
        re.UNICODE,
    )

    # Non-ASCII character detector (useful for detecting script mismatch vs English)
    NON_ASCII_CHAR_PATTERN = re.compile(r'[^\x00-\x7F]')

    # ASCII letter detector
    ASCII_LETTER_PATTERN = re.compile(r'[a-zA-Z]')

    # Special characters to strip (keeps word characters and whitespace)
    SPECIAL_CHARS_PATTERN = re.compile(
        rf'[{PUNCT_STR}]',
        re.UNICODE,
    )

    # ------------------------------------------------
    # Constructor
    # ------------------------------------------------

    def __init__(
        self,
        ignore_case: bool = False,
        ignore_extra_spaces: bool = False,
        remove_special_chars: bool = False,
    ):
        """
        Initialize the TextParser.

        Args:
            ignore_case: Normalize text to lowercase for comparison.
            ignore_extra_spaces: Collapse multiple spaces into one.
            remove_special_chars: Strip punctuation / special characters
                                  (keeps Gujarati letters, digits, spaces).
        """
        self._ignore_case = ignore_case
        self._ignore_extra_spaces = ignore_extra_spaces
        self._remove_special_chars = remove_special_chars

    # ------------------------------------------------
    # Properties
    # ------------------------------------------------

    @property
    def ignore_case(self) -> bool:
        """Whether case-insensitive comparison is enabled."""
        return self._ignore_case

    @ignore_case.setter
    def ignore_case(self, value: bool) -> None:
        self._ignore_case = value

    @property
    def ignore_extra_spaces(self) -> bool:
        """Whether extra whitespace collapsing is enabled."""
        return self._ignore_extra_spaces

    @ignore_extra_spaces.setter
    def ignore_extra_spaces(self, value: bool) -> None:
        self._ignore_extra_spaces = value

    @property
    def remove_special_chars(self) -> bool:
        """Whether special-character removal is enabled."""
        return self._remove_special_chars

    @remove_special_chars.setter
    def remove_special_chars(self, value: bool) -> None:
        self._remove_special_chars = value

    # ------------------------------------------------
    # File Loading
    # ------------------------------------------------

    def load_from_file(self, file_path: str) -> str:
        """
        Load text content from a UTF-8 encoded .txt file.

        Args:
            file_path: Path to the .txt file.

        Returns:
            The file content as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is not a .txt file.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.lower().endswith('.txt'):
            raise ValueError(f"Only .txt files are supported. Got: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    # ------------------------------------------------
    # Text Normalization
    # ------------------------------------------------

    def normalize(self, text: str) -> str:
        """
        Normalize text with the following pipeline:

            1. Unicode NFC normalization (critical for Gujarati
               combining marks — ensures identical visual chars
               have identical byte sequences).
            2. Normalize line endings (CRLF / CR → LF).
            3. Strip leading / trailing whitespace.
            4. Optionally remove special characters.
            5. Optionally collapse multiple spaces into one.
            6. Optionally convert to lowercase.

        Args:
            text: Raw input text.

        Returns:
            Normalized text string.
        """
        if not text:
            return ""

        # Step 1: Unicode NFC normalization — the single most important
        # step for Gujarati accuracy.  Precomposed vs decomposed forms
        # of the same glyph (e.g. Ka + Nukta vs Qa) will now match.
        result = unicodedata.normalize('NFC', text)

        # Step 2: Normalize line endings
        result = result.replace('\r\n', '\n').replace('\r', '\n')

        # Step 3: Strip leading / trailing whitespace
        result = result.strip()

        # Step 4: Remove special characters if enabled
        if self._remove_special_chars:
            result = self._strip_special_chars(result)

        # Step 5: Collapse extra spaces if enabled
        if self._ignore_extra_spaces:
            result = self._collapse_spaces(result)

        # Step 6: Case folding if enabled
        if self._ignore_case:
            result = result.lower()

        return result

    # ------------------------------------------------
    # Tokenization
    # ------------------------------------------------

    def tokenize_words(self, text: str) -> List[str]:
        """
        Split text into word tokens with punctuation separated.

        Uses a regex tokenizer that produces:
            - Gujarati word tokens (consecutive Gujarati chars).
            - ASCII word tokens.
            - Individual punctuation tokens.

        This separation is critical for accuracy: "word," and "word"
        now produce the same base word token, so the diff engine
        won't flag "word" as changed just because of a trailing comma.

        Args:
            text: Input text.

        Returns:
            List of non-empty tokens.
        """
        if not text:
            return []

        normalized = self.normalize(text)
        tokens = self.WORD_TOKEN_PATTERN.findall(normalized)
        return [t for t in tokens if t.strip()]

    def tokenize_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Recognizes Gujarati terminators (। ॥) and standard (. ! ?).

        Args:
            text: Input text.

        Returns:
            List of non-empty sentence strings.
        """
        if not text:
            return []

        normalized = self.normalize(text)
        sentences = self.SENTENCE_SPLIT_PATTERN.split(normalized)
        return [s.strip() for s in sentences if s.strip()]

    # ------------------------------------------------
    # Private Helpers
    # ------------------------------------------------

    def _strip_special_chars(self, text: str) -> str:
        """Remove special / punctuation characters, collapse resulting gaps."""
        result = self.SPECIAL_CHARS_PATTERN.sub('', text)
        return re.sub(r'  +', ' ', result)

    def _collapse_spaces(self, text: str) -> str:
        """Collapse multiple spaces / tabs into one; multiple newlines into one."""
        result = re.sub(r'[^\S\n]+', ' ', text)
        return re.sub(r'\n\s*\n', '\n', result)

    # ------------------------------------------------
    # Utility Methods
    # ------------------------------------------------

    def contains_non_ascii(self, text: str) -> bool:
        """Check if text contains non-ASCII characters."""
        return bool(self.NON_ASCII_CHAR_PATTERN.search(text))

    def contains_ascii_letters(self, text: str) -> bool:
        """Check if text contains ASCII (English) letter characters."""
        return bool(self.ASCII_LETTER_PATTERN.search(text))

    def word_count(self, text: str) -> int:
        """Count words (excludes standalone punctuation tokens)."""
        tokens = self.tokenize_words(text)
        # Only count tokens that contain actual word characters
        return sum(1 for t in tokens if re.search(r'\w', t, re.UNICODE))

    def sentence_count(self, text: str) -> int:
        """Count sentences."""
        return len(self.tokenize_sentences(text))

    def get_text_stats(self, text: str) -> dict:
        """
        Comprehensive text statistics.

        Returns:
            dict with char_count, word_count, sentence_count, has_gujarati.
        """
        normalized = self.normalize(text)
        return {
            'char_count': len(normalized),
            'word_count': self.word_count(text),
            'sentence_count': self.sentence_count(text),
            'has_non_ascii': self.contains_non_ascii(text),
        }

    def __repr__(self) -> str:
        return (
            f"TextParser("
            f"ignore_case={self._ignore_case}, "
            f"ignore_extra_spaces={self._ignore_extra_spaces}, "
            f"remove_special_chars={self._remove_special_chars})"
        )
