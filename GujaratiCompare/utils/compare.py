# ====================================================
# Gujarati Paragraph Compare Pro
# utils/compare.py — Comparison Engine Module (v2)
# ====================================================
# Accurate 3-way comparison engine with:
#   - Per-word diff via SequenceMatcher
#   - Character-level sub-diff inside changed words (diff-match-patch)
#   - Word-index-based 3-panel merge (not text-equality)
#   - Proper handling of empty panels when < 3 texts are given
# ====================================================

import difflib
from typing import Dict, List, Tuple, Optional, Any

import diff_match_patch as dmp_module

from utils.parser import TextParser


# ====================================================
# Data Classes
# ====================================================

class DiffResult:
    """
    A single diff segment with an operation tag and text.

    operation: 'equal' | 'added' | 'deleted' | 'changed' | 'missing'
    text:      the text content for this segment.
    source:    which paragraph ('a', 'b', 'c') this belongs to.
    """

    EQUAL = 'equal'
    ADDED = 'added'
    DELETED = 'deleted'
    CHANGED = 'changed'
    MISSING = 'missing'
    SCRIPT_MISMATCH = 'script_mismatch'

    def __init__(self, operation: str, text: str, source: str = ''):
        self.operation = operation
        self.text = text
        self.source = source

    def to_dict(self) -> dict:
        return {
            'operation': self.operation,
            'text': self.text,
            'source': self.source,
        }

    def __repr__(self) -> str:
        return f"DiffResult({self.operation!r}, {self.text!r})"


class PairwiseDiff:
    """
    Container for one pairwise comparison (e.g. A vs B).

    left_diffs / right_diffs:  ordered DiffResult lists for each side.
    added_words, deleted_words, changed_words, missing_words: summary lists.
    """

    def __init__(
        self,
        label: str,
        left_diffs: List[DiffResult],
        right_diffs: List[DiffResult],
        added_words: List[str],
        deleted_words: List[str],
        changed_words: List[Tuple[str, str]],
        missing_words: List[str],
    ):
        self.label = label
        self.left_diffs = left_diffs
        self.right_diffs = right_diffs
        self.inline_diffs = []
        self.added_words = added_words
        self.deleted_words = deleted_words
        self.changed_words = changed_words
        self.missing_words = missing_words

    def to_dict(self) -> dict:
        return {
            'label': self.label,
            'left_diffs': [d.to_dict() for d in self.left_diffs],
            'right_diffs': [d.to_dict() for d in self.right_diffs],
            'inline_diffs': [d.to_dict() for d in self.inline_diffs],
            'added_words': self.added_words,
            'deleted_words': self.deleted_words,
            'changed_words': [
                {'old': o, 'new': n} for o, n in self.changed_words
            ],
            'missing_words': self.missing_words,
            'stats': {
                'added_count': len(self.added_words),
                'deleted_count': len(self.deleted_words),
                'changed_count': len(self.changed_words),
                'missing_count': len(self.missing_words),
            },
        }


# ====================================================
# Comparison Engine
# ====================================================

class ComparisonEngine:
    """
    Accurate 3-way Gujarati paragraph comparison engine.

    Accuracy improvements over v1:
        1. Per-word SequenceMatcher produces individual word-level
           DiffResults instead of lumping entire replace-blocks together.
        2. For each "replace" pair, a secondary character-level diff
           (via diff-match-patch) is run to sub-classify words as
           CHANGED (partially different) vs DELETED+ADDED (completely
           different).
        3. 3-panel merge uses word-index maps instead of text-equality
           matching, so different segment boundaries from different
           pairwise diffs don't break the merge.
        4. Empty panels (< 3 texts provided) are handled gracefully.
    """

    def __init__(self, parser: Optional[TextParser] = None):
        self._parser = parser if parser is not None else TextParser()
        self._dmp = dmp_module.diff_match_patch()
        self._dmp.Diff_Timeout = 10.0  # generous timeout for large texts

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
    # Pairwise Word-Level Comparison (core accuracy logic)
    # ------------------------------------------------

    def compare_words(self, text_a: str, text_b: str, flag_script_mismatch: bool = False, flag_ignore_punctuation: bool = False) -> PairwiseDiff:
        """
        Word-level pairwise comparison.

        Produces one DiffResult PER WORD (not per opcode block),
        giving precise per-word highlighting in the UI.
        """
        words_a = self._parser.tokenize_words(text_a)
        words_b = self._parser.tokenize_words(text_b)

        # SequenceMatcher with autojunk=False for accuracy on large texts
        matcher = difflib.SequenceMatcher(None, words_a, words_b, autojunk=False)
        opcodes = matcher.get_opcodes()

        left_diffs: List[DiffResult] = []
        right_diffs: List[DiffResult] = []
        inline_diffs: List[DiffResult] = []
        added_words: List[str] = []
        deleted_words: List[str] = []
        changed_words: List[Tuple[str, str]] = []

        for tag, i1, i2, j1, j2 in opcodes:

            if tag == 'equal':
                # Each word gets its own EQUAL DiffResult for precise indexing
                for k in range(i1, i2):
                    left_diffs.append(
                        DiffResult(DiffResult.EQUAL, words_a[k], 'a')
                    )
                    inline_diffs.append(
                        DiffResult(DiffResult.EQUAL, words_a[k], 'a')
                    )
                for k in range(j1, j2):
                    right_diffs.append(
                        DiffResult(DiffResult.EQUAL, words_b[k], 'b')
                    )

            elif tag == 'delete':
                for k in range(i1, i2):
                    left_diffs.append(
                        DiffResult(DiffResult.DELETED, words_a[k], 'a')
                    )
                    inline_diffs.append(
                        DiffResult(DiffResult.DELETED, words_a[k], 'a')
                    )
                    deleted_words.append(words_a[k])

            elif tag == 'insert':
                for k in range(j1, j2):
                    right_diffs.append(
                        DiffResult(DiffResult.ADDED, words_b[k], 'b')
                    )
                    inline_diffs.append(
                        DiffResult(DiffResult.ADDED, words_b[k], 'b')
                    )
                    added_words.append(words_b[k])

            elif tag == 'replace':
                # Block-level script mismatch check
                # This makes it much more accurate when word counts differ
                # (e.g. 1 English word replacing 2 Gujarati words)
                is_block_mismatch = False
                if flag_script_mismatch:
                    left_text = " ".join(words_a[i1:i2])
                    right_text = " ".join(words_b[j1:j2])
                    a_has_en = self._parser.contains_english(left_text)
                    a_has_gu = self._parser.contains_gujarati(left_text)
                    b_has_en = self._parser.contains_english(right_text)
                    b_has_gu = self._parser.contains_gujarati(right_text)

                    # Strict block mismatch: One side is exclusively EN (or EN+nums),
                    # and the other side is exclusively GU (or GU+nums).
                    is_en_to_gu = a_has_en and not a_has_gu and b_has_gu and not b_has_en
                    is_gu_to_en = a_has_gu and not a_has_en and b_has_en and not b_has_gu

                    if is_en_to_gu or is_gu_to_en:
                        is_block_mismatch = True

                # For the Wrong Words list, we consider the entire replaced phrase block
                # as a single change, rather than splitting it up.
                phrase_a = " ".join(words_a[i1:i2])
                phrase_b = " ".join(words_b[j1:j2])
                changed_words.append((phrase_a, phrase_b))

                if is_block_mismatch:
                    for k in range(i1, i2):
                        left_diffs.append(DiffResult(DiffResult.SCRIPT_MISMATCH, words_a[k], 'a'))
                        inline_diffs.append(DiffResult(DiffResult.SCRIPT_MISMATCH, words_a[k], 'a'))
                        deleted_words.append(words_a[k])
                    for k in range(j1, j2):
                        right_diffs.append(DiffResult(DiffResult.SCRIPT_MISMATCH, words_b[k], 'b'))
                        inline_diffs.append(DiffResult(DiffResult.SCRIPT_MISMATCH, words_b[k], 'b'))
                        added_words.append(words_b[k])
                else:
                    # === Accuracy improvement: per-word sub-diff ===
                    # Pair up words 1-to-1 where possible, then handle
                    # the tail as pure deletes or inserts.
                    left_count = i2 - i1
                    right_count = j2 - j1
                    paired = min(left_count, right_count)
                    
                    a_inline = []
                    b_inline = []

                    for offset in range(paired):
                        old_word = words_a[i1 + offset]
                        new_word = words_b[j1 + offset]

                        if old_word == new_word:
                            # Identical within a replace block (rare but possible
                            # with autojunk=False)
                            left_diffs.append(
                                DiffResult(DiffResult.EQUAL, old_word, 'a')
                            )
                            a_inline.append(
                                DiffResult(DiffResult.EQUAL, old_word, 'a')
                            )
                            right_diffs.append(
                                DiffResult(DiffResult.EQUAL, new_word, 'b')
                            )
                            b_inline.append(
                                DiffResult(DiffResult.EQUAL, new_word, 'b')
                            )
                        else:
                            # Word-level script mismatch check
                            is_word_mismatch = False
                            if flag_script_mismatch:
                                # Don't flag if it's just a misaligned common word
                                if old_word not in words_b[j1:j2] and new_word not in words_a[i1:i2]:
                                    a_is_en = self._parser.contains_english(old_word)
                                    a_is_gu = self._parser.contains_gujarati(old_word)
                                    b_is_en = self._parser.contains_english(new_word)
                                    b_is_gu = self._parser.contains_gujarati(new_word)
                                    
                                    # Strict check
                                    is_en_to_gu = a_is_en and not a_is_gu and b_is_gu and not b_is_en
                                    is_gu_to_en = a_is_gu and not a_is_en and b_is_en and not b_is_gu
                                    
                                    if is_en_to_gu or is_gu_to_en:
                                        is_word_mismatch = True

                            if is_word_mismatch:
                                left_diffs.append(DiffResult(DiffResult.SCRIPT_MISMATCH, old_word, 'a'))
                                right_diffs.append(DiffResult(DiffResult.SCRIPT_MISMATCH, new_word, 'b'))
                                a_inline.append(DiffResult(DiffResult.SCRIPT_MISMATCH, old_word, 'a'))
                                b_inline.append(DiffResult(DiffResult.SCRIPT_MISMATCH, new_word, 'b'))
                            else:
                                # Use character-level similarity to decide
                                # CHANGED (partially same) vs fully different
                                char_ratio = difflib.SequenceMatcher(
                                    None, old_word, new_word
                                ).ratio()

                            if char_ratio >= 0.3:
                                # Partially similar → CHANGED (yellow)
                                left_diffs.append(
                                    DiffResult(DiffResult.CHANGED, old_word, 'a')
                                )
                                right_diffs.append(
                                    DiffResult(DiffResult.CHANGED, new_word, 'b')
                                )
                                # In merged view, we always just show DELETED followed by ADDED
                                a_inline.append(
                                    DiffResult(DiffResult.DELETED, old_word, 'a')
                                )
                                b_inline.append(
                                    DiffResult(DiffResult.ADDED, new_word, 'b')
                                )
                            else:
                                # Completely different → DELETE old + ADD new
                                left_diffs.append(
                                    DiffResult(DiffResult.DELETED, old_word, 'a')
                                )
                                right_diffs.append(
                                    DiffResult(DiffResult.ADDED, new_word, 'b')
                                )
                                a_inline.append(
                                    DiffResult(DiffResult.DELETED, old_word, 'a')
                                )
                                b_inline.append(
                                    DiffResult(DiffResult.ADDED, new_word, 'b')
                                )
                                deleted_words.append(old_word)
                                added_words.append(new_word)

                    # Remaining unpaired words on the left → deleted
                    for k in range(i1 + paired, i2):
                        left_diffs.append(
                            DiffResult(DiffResult.DELETED, words_a[k], 'a')
                        )
                        a_inline.append(
                            DiffResult(DiffResult.DELETED, words_a[k], 'a')
                        )
                        deleted_words.append(words_a[k])

                    # Remaining unpaired words on the right → added
                    for k in range(j1 + paired, j2):
                        right_diffs.append(
                            DiffResult(DiffResult.ADDED, words_b[k], 'b')
                        )
                        b_inline.append(
                            DiffResult(DiffResult.ADDED, words_b[k], 'b')
                        )
                        added_words.append(words_b[k])
                    
                    # Append all A words first, then B words for sequential inline display
                    inline_diffs.extend(a_inline)
                    inline_diffs.extend(b_inline)

        # Missing words: words in A that don't appear anywhere in B
        set_a = set(words_a)
        set_b = set(words_b)
        missing_words = sorted(set_a - set_b)

        # Post-process to ignore common punctuation if requested
        if flag_ignore_punctuation:
            punct_set = {'.', ',', '?', '!', '।', '"', "'", '“', '”', '‘', '’'}
            
            # Convert ADDED, DELETED, SCRIPT_MISMATCH to EQUAL for these puncts
            for diff_list in [left_diffs, right_diffs, inline_diffs]:
                for d in diff_list:
                    if d.operation in (DiffResult.ADDED, DiffResult.DELETED, DiffResult.SCRIPT_MISMATCH):
                        if d.text in punct_set:
                            d.operation = DiffResult.EQUAL
            
            # Remove from added and deleted tracking
            added_words = [w for w in added_words if w not in punct_set]
            deleted_words = [w for w in deleted_words if w not in punct_set]
            
            # Remove from changed words if the only difference is punctuation
            # Example: changed_words = [(".", ",")] or [("hello", "hello.")]
            # If we filter out punctuation from the old and new phrase and they become equal, we remove it.
            new_changed = []
            for old_phrase, new_phrase in changed_words:
                clean_old = " ".join([w for w in old_phrase.split() if w not in punct_set])
                clean_new = " ".join([w for w in new_phrase.split() if w not in punct_set])
                if clean_old != clean_new:
                    new_changed.append((old_phrase, new_phrase))
            changed_words = new_changed

            # Remove from missing words
            missing_words = [w for w in missing_words if w not in punct_set]

        diff_result = PairwiseDiff(
            label='',
            left_diffs=left_diffs,
            right_diffs=right_diffs,
            added_words=added_words,
            deleted_words=deleted_words,
            changed_words=changed_words,
            missing_words=missing_words,
        )
        diff_result.inline_diffs = inline_diffs
        return diff_result

    # ------------------------------------------------
    # Pairwise Sentence-Level Comparison
    # ------------------------------------------------

    def compare_sentences(self, text_a: str, text_b: str, flag_script_mismatch: bool = False, flag_ignore_punctuation: bool = False) -> PairwiseDiff:
        """
        Sentence-level pairwise comparison.

        Each sentence is diffed as a unit.  For 'replace' blocks,
        a secondary word-level diff is run within each sentence pair
        to produce accurate per-word highlights.
        """
        sents_a = self._parser.tokenize_sentences(text_a)
        sents_b = self._parser.tokenize_sentences(text_b)

        matcher = difflib.SequenceMatcher(
            None, sents_a, sents_b, autojunk=False
        )
        opcodes = matcher.get_opcodes()

        left_diffs: List[DiffResult] = []
        right_diffs: List[DiffResult] = []
        added_words: List[str] = []
        deleted_words: List[str] = []
        changed_words: List[Tuple[str, str]] = []

        for tag, i1, i2, j1, j2 in opcodes:

            if tag == 'equal':
                for k in range(i1, i2):
                    left_diffs.append(
                        DiffResult(DiffResult.EQUAL, sents_a[k], 'a')
                    )
                for k in range(j1, j2):
                    right_diffs.append(
                        DiffResult(DiffResult.EQUAL, sents_b[k], 'b')
                    )

            elif tag == 'delete':
                for k in range(i1, i2):
                    left_diffs.append(
                        DiffResult(DiffResult.DELETED, sents_a[k], 'a')
                    )
                    deleted_words.extend(
                        self._parser.tokenize_words(sents_a[k])
                    )

            elif tag == 'insert':
                for k in range(j1, j2):
                    right_diffs.append(
                        DiffResult(DiffResult.ADDED, sents_b[k], 'b')
                    )
                    added_words.extend(
                        self._parser.tokenize_words(sents_b[k])
                    )

            elif tag == 'replace':
                paired = min(i2 - i1, j2 - j1)
                for offset in range(paired):
                    old_sent = sents_a[i1 + offset]
                    new_sent = sents_b[j1 + offset]
                    if old_sent == new_sent:
                        left_diffs.append(
                            DiffResult(DiffResult.EQUAL, old_sent, 'a')
                        )
                        right_diffs.append(
                            DiffResult(DiffResult.EQUAL, new_sent, 'b')
                        )
                    else:
                        left_diffs.append(
                            DiffResult(DiffResult.CHANGED, old_sent, 'a')
                        )
                        right_diffs.append(
                            DiffResult(DiffResult.CHANGED, new_sent, 'b')
                        )
                        changed_words.append((old_sent, new_sent))

                for k in range(i1 + paired, i2):
                    left_diffs.append(
                        DiffResult(DiffResult.DELETED, sents_a[k], 'a')
                    )
                    deleted_words.extend(
                        self._parser.tokenize_words(sents_a[k])
                    )
                for k in range(j1 + paired, j2):
                    right_diffs.append(
                        DiffResult(DiffResult.ADDED, sents_b[k], 'b')
                    )
                    added_words.extend(
                        self._parser.tokenize_words(sents_b[k])
                    )

        set_a = set(sents_a)
        set_b = set(sents_b)
        missing_words = sorted(set_a - set_b)

        return PairwiseDiff(
            label='',
            left_diffs=left_diffs,
            right_diffs=right_diffs,
            added_words=added_words,
            deleted_words=deleted_words,
            changed_words=changed_words,
            missing_words=missing_words,
        )

    # ------------------------------------------------
    # Character-Level diff-match-patch (utility)
    # ------------------------------------------------

    def compare_chars_dmp(self, text_a: str, text_b: str) -> List[DiffResult]:
        """Character-level diff using Google diff-match-patch."""
        norm_a = self._parser.normalize(text_a)
        norm_b = self._parser.normalize(text_b)

        diffs = self._dmp.diff_main(norm_a, norm_b)
        self._dmp.diff_cleanupSemantic(diffs)

        op_map = {0: DiffResult.EQUAL, -1: DiffResult.DELETED, 1: DiffResult.ADDED}
        return [DiffResult(op_map[op], text) for op, text in diffs]

    # ------------------------------------------------
    # 3-Way Comparison (Main Entry Point)
    # ------------------------------------------------

    def compare_three(
        self,
        text_a: str,
        text_b: str,
        text_c: str,
        mode: str = 'word',
        flag_script_mismatch: bool = False,
        flag_ignore_punctuation: bool = False,
    ) -> Dict[str, Any]:
        """
        Full 3-way comparison producing pairwise diffs and
        merged per-word panel data for synchronized display.
        """
        if mode == 'word':
            compare_func = self.compare_words
        elif mode == 'sentence':
            compare_func = self.compare_sentences
        else:
            raise ValueError(f"Invalid mode: '{mode}'. Use 'word' or 'sentence'.")

        # Helper to safely compare only non-empty texts
        def safe_compare(t1: str, t2: str) -> 'PairwiseDiff':
            if not t1.strip() or not t2.strip():
                return PairwiseDiff('', [], [], [], [], [], [])
            return compare_func(t1, t2, flag_script_mismatch=flag_script_mismatch, flag_ignore_punctuation=flag_ignore_punctuation)

        # Pairwise diffs
        diff_ab = safe_compare(text_a, text_b)
        diff_ab.label = 'A vs B'

        diff_ac = safe_compare(text_a, text_c)
        diff_ac.label = 'A vs C'

        diff_bc = safe_compare(text_b, text_c)
        diff_bc.label = 'B vs C'

        # Build accurate per-word panel data using word-index maps
        panels = self._build_panel_data(
            text_a, text_b, text_c,
            diff_ab, diff_ac, diff_bc, mode,
        )

        return {
            'a_vs_b': diff_ab.to_dict(),
            'a_vs_c': diff_ac.to_dict(),
            'b_vs_c': diff_bc.to_dict(),
            'panels': panels,
        }

    # ------------------------------------------------
    # Accurate Panel Data Builder (word-index merge)
    # ------------------------------------------------

    def _build_panel_data(
        self,
        text_a: str,
        text_b: str,
        text_c: str,
        diff_ab: PairwiseDiff,
        diff_ac: PairwiseDiff,
        diff_bc: PairwiseDiff,
        mode: str,
    ) -> Dict[str, List[dict]]:
        """
        Build per-word highlight data for each of the 3 result panels.

        Strategy (much more accurate than v1):
            1. For each panel's paragraph, build the word list.
            2. For each word at index i, look up that word's operation
               in each relevant pairwise diff (using index counters, not
               text equality).
            3. Take the HIGHEST-PRIORITY operation across all pairwise
               comparisons involving this panel.

        This correctly handles cases where different pairwise diffs
        split text into different segment boundaries.
        """
        tokenize = (self._parser.tokenize_words if mode == 'word'
                     else self._parser.tokenize_sentences)

        words_a = tokenize(text_a)
        words_b = tokenize(text_b)
        words_c = tokenize(text_c)

        # Build per-word operation maps from the pairwise diffs
        # Map: word_index → operation string
        ops_a_from_ab = self._extract_word_ops(diff_ab.left_diffs)
        ops_a_from_ac = self._extract_word_ops(diff_ac.left_diffs)
        ops_b_from_ab = self._extract_word_ops(diff_ab.right_diffs)
        ops_b_from_bc = self._extract_word_ops(diff_bc.left_diffs)
        ops_c_from_ac = self._extract_word_ops(diff_ac.right_diffs)
        ops_c_from_bc = self._extract_word_ops(diff_bc.right_diffs)

        # Merge operations for each panel
        panel_a = self._merge_word_ops(words_a, ops_a_from_ab, ops_a_from_ac, 'a')
        panel_b = self._merge_word_ops(words_b, ops_b_from_ab, ops_b_from_bc, 'b')
        panel_c = self._merge_word_ops(words_c, ops_c_from_ac, ops_c_from_bc, 'c')

        return {
            'panel_a': [d.to_dict() for d in panel_a],
            'panel_b': [d.to_dict() for d in panel_b],
            'panel_c': [d.to_dict() for d in panel_c],
        }

    def _extract_word_ops(self, diffs: List[DiffResult]) -> List[str]:
        """
        Extract a flat list of per-word operations from a DiffResult list.

        Each DiffResult may contain one word (per-word mode) or a
        multi-word sentence.  This method produces one operation entry
        per token.

        Returns:
            List of operation strings, one per word, in order.
        """
        ops: List[str] = []
        for diff in diffs:
            # Count how many tokens are in this diff segment
            tokens = diff.text.split() if diff.text else ['']
            token_count = max(1, len(tokens))
            ops.extend([diff.operation] * token_count)
        return ops

    def _merge_word_ops(
        self,
        words: List[str],
        ops_1: List[str],
        ops_2: List[str],
        source: str,
    ) -> List[DiffResult]:
        """
        Merge two operation lists for the same word list.

        For each word at index i, pick the highest-priority operation
        from ops_1[i] and ops_2[i].

        Priority (highest first):
            script_mismatch(5) > deleted(4) > added(3) > changed(2) > missing(1) > equal(0)
        """
        priority = {
            DiffResult.SCRIPT_MISMATCH: 5,
            DiffResult.DELETED: 4,
            DiffResult.ADDED: 3,
            DiffResult.CHANGED: 2,
            DiffResult.MISSING: 1,
            DiffResult.EQUAL: 0,
        }

        results: List[DiffResult] = []

        for i, word in enumerate(words):
            op1 = ops_1[i] if i < len(ops_1) else DiffResult.EQUAL
            op2 = ops_2[i] if i < len(ops_2) else DiffResult.EQUAL

            # Pick the higher-priority operation
            if priority.get(op1, 0) >= priority.get(op2, 0):
                best_op = op1
            else:
                best_op = op2

            results.append(DiffResult(best_op, word, source))

        return results

    # ------------------------------------------------
    # Utility: Generate HTML Diff Markup
    # ------------------------------------------------

    def generate_html_diff(self, diffs: List[DiffResult]) -> str:
        """Convert DiffResult list to HTML with CSS classes."""
        css_map = {
            DiffResult.EQUAL: '',
            DiffResult.ADDED: 'diff-added',
            DiffResult.DELETED: 'diff-deleted',
            DiffResult.CHANGED: 'diff-changed',
            DiffResult.MISSING: 'diff-missing',
            DiffResult.SCRIPT_MISMATCH: 'diff-script-mismatch',
        }

        parts = []
        for d in diffs:
            cls = css_map.get(d.operation, '')
            escaped = (d.text.replace('&', '&amp;')
                             .replace('<', '&lt;')
                             .replace('>', '&gt;'))
            if cls:
                parts.append(f'<span class="{cls}">{escaped}</span>')
            else:
                parts.append(f'<span>{escaped}</span>')

        return ' '.join(parts)

    def __repr__(self) -> str:
        return f"ComparisonEngine(parser={self._parser!r})"
