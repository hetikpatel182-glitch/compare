/**
 * ====================================================
 * Gujarati Paragraph Compare Pro
 * static/diff_match_patch.js — Google's Diff Match Patch
 * ====================================================
 * Offline-bundled implementation of the core diff-match-patch
 * algorithm for client-side text comparison.
 * Based on Google's diff-match-patch (Apache 2.0 License).
 * ====================================================
 */

/**
 * Diff Match and Patch — Core Implementation
 * @constructor
 */
function diff_match_patch() {
    // Defaults
    this.Diff_Timeout = 1.0;
    this.Diff_EditCost = 4;
    this.Match_Threshold = 0.5;
    this.Match_Distance = 1000;
    this.Patch_DeleteThreshold = 0.5;
    this.Patch_Margin = 4;
    this.Match_MaxBits = 32;
}

// Operation constants
var DIFF_DELETE = -1;
var DIFF_INSERT = 1;
var DIFF_EQUAL = 0;

/**
 * Find the differences between two texts.
 * @param {string} text1 Old string to be diffed.
 * @param {string} text2 New string to be diffed.
 * @param {boolean=} opt_checklines Optional speedup flag.
 * @param {number=} opt_deadline Optional time when computation should stop.
 * @return {!Array.<!Array>} Array of diff tuples.
 */
diff_match_patch.prototype.diff_main = function(text1, text2, opt_checklines, opt_deadline) {
    // Set a deadline for the diff
    if (typeof opt_deadline === 'undefined') {
        if (this.Diff_Timeout <= 0) {
            opt_deadline = Number.MAX_VALUE;
        } else {
            opt_deadline = (new Date).getTime() + this.Diff_Timeout * 1000;
        }
    }
    var deadline = opt_deadline;

    // Check for null inputs
    if (text1 === null || text2 === null) {
        throw new Error('Null input. (diff_main)');
    }

    // Check for equality
    if (text1 === text2) {
        if (text1) {
            return [[DIFF_EQUAL, text1]];
        }
        return [];
    }

    if (typeof opt_checklines === 'undefined') {
        opt_checklines = true;
    }
    var checklines = opt_checklines;

    // Trim off common prefix
    var commonlength = this.diff_commonPrefix(text1, text2);
    var commonprefix = text1.substring(0, commonlength);
    text1 = text1.substring(commonlength);
    text2 = text2.substring(commonlength);

    // Trim off common suffix
    commonlength = this.diff_commonSuffix(text1, text2);
    var commonsuffix = text1.substring(text1.length - commonlength);
    text1 = text1.substring(0, text1.length - commonlength);
    text2 = text2.substring(0, text2.length - commonlength);

    // Compute the diff on the middle block
    var diffs = this.diff_compute_(text1, text2, checklines, deadline);

    // Restore the prefix and suffix
    if (commonprefix) {
        diffs.unshift([DIFF_EQUAL, commonprefix]);
    }
    if (commonsuffix) {
        diffs.push([DIFF_EQUAL, commonsuffix]);
    }
    this.diff_cleanupMerge(diffs);
    return diffs;
};

/**
 * Find the differences between two texts (assumes no common prefix/suffix).
 * @param {string} text1 Old string.
 * @param {string} text2 New string.
 * @param {boolean} checklines Speedup flag.
 * @param {number} deadline Time to stop.
 * @return {!Array.<!Array>} Array of diff tuples.
 * @private
 */
diff_match_patch.prototype.diff_compute_ = function(text1, text2, checklines, deadline) {
    var diffs;

    if (!text1) {
        // Just an insert
        return [[DIFF_INSERT, text2]];
    }

    if (!text2) {
        // Just a delete
        return [[DIFF_DELETE, text1]];
    }

    var longtext = text1.length > text2.length ? text1 : text2;
    var shorttext = text1.length > text2.length ? text2 : text1;
    var i = longtext.indexOf(shorttext);
    if (i !== -1) {
        // Shorter text is inside the longer text
        diffs = [[DIFF_INSERT, longtext.substring(0, i)], [DIFF_EQUAL, shorttext],
                 [DIFF_INSERT, longtext.substring(i + shorttext.length)]];
        // Swap insertions for deletions if diff is reversed
        if (text1.length > text2.length) {
            diffs[0][0] = diffs[2][0] = DIFF_DELETE;
        }
        return diffs;
    }

    if (shorttext.length === 1) {
        // Single character string — can't do half-match optimization
        return [[DIFF_DELETE, text1], [DIFF_INSERT, text2]];
    }

    // Check for a half-match
    var hm = this.diff_halfMatch_(text1, text2);
    if (hm) {
        var text1_a = hm[0];
        var text1_b = hm[1];
        var text2_a = hm[2];
        var text2_b = hm[3];
        var mid_common = hm[4];
        var diffs_a = this.diff_main(text1_a, text2_a, checklines, deadline);
        var diffs_b = this.diff_main(text1_b, text2_b, checklines, deadline);
        return diffs_a.concat([[DIFF_EQUAL, mid_common]], diffs_b);
    }

    if (checklines && text1.length > 100 && text2.length > 100) {
        return this.diff_lineMode_(text1, text2, deadline);
    }

    return this.diff_bisect_(text1, text2, deadline);
};

/**
 * Do a quick line-level diff on both strings, then redo on smaller fragments.
 * @param {string} text1 Old string.
 * @param {string} text2 New string.
 * @param {number} deadline Time to stop.
 * @return {!Array.<!Array>} Array of diff tuples.
 * @private
 */
diff_match_patch.prototype.diff_lineMode_ = function(text1, text2, deadline) {
    // Scan the text on a line-by-line basis first
    var a = this.diff_linesToChars_(text1, text2);
    text1 = a.chars1;
    text2 = a.chars2;
    var linearray = a.lineArray;

    var diffs = this.diff_main(text1, text2, false, deadline);

    // Convert the diff back to original text
    this.diff_charsToLines_(diffs, linearray);
    // Eliminate freak matches (e.g. blank lines)
    this.diff_cleanupSemantic(diffs);

    // Rediff any replacement blocks on a character-by-character basis
    diffs.push([DIFF_EQUAL, '']);  // Add a dummy entry at the end
    var pointer = 0;
    var count_delete = 0;
    var count_insert = 0;
    var text_delete = '';
    var text_insert = '';
    while (pointer < diffs.length) {
        switch (diffs[pointer][0]) {
            case DIFF_INSERT:
                count_insert++;
                text_insert += diffs[pointer][1];
                break;
            case DIFF_DELETE:
                count_delete++;
                text_delete += diffs[pointer][1];
                break;
            case DIFF_EQUAL:
                if (count_delete >= 1 && count_insert >= 1) {
                    diffs.splice(pointer - count_delete - count_insert,
                                 count_delete + count_insert);
                    pointer = pointer - count_delete - count_insert;
                    var subDiff = this.diff_main(text_delete, text_insert, false, deadline);
                    for (var j = subDiff.length - 1; j >= 0; j--) {
                        diffs.splice(pointer, 0, subDiff[j]);
                    }
                    pointer = pointer + subDiff.length;
                }
                count_insert = 0;
                count_delete = 0;
                text_delete = '';
                text_insert = '';
                break;
        }
        pointer++;
    }
    diffs.pop();  // Remove the dummy entry

    return diffs;
};

/**
 * Find the 'middle snake' of a diff, split the problem in two and return the
 * recursively constructed diff.
 * @param {string} text1 Old string.
 * @param {string} text2 New string.
 * @param {number} deadline Time to stop.
 * @return {!Array.<!Array>} Array of diff tuples.
 * @private
 */
diff_match_patch.prototype.diff_bisect_ = function(text1, text2, deadline) {
    var text1_length = text1.length;
    var text2_length = text2.length;
    var max_d = Math.ceil((text1_length + text2_length) / 2);
    var v_offset = max_d;
    var v_length = 2 * max_d;
    var v1 = new Array(v_length);
    var v2 = new Array(v_length);
    for (var x = 0; x < v_length; x++) {
        v1[x] = -1;
        v2[x] = -1;
    }
    v1[v_offset + 1] = 0;
    v2[v_offset + 1] = 0;
    var delta = text1_length - text2_length;
    var front = (delta % 2 !== 0);
    var k1start = 0;
    var k1end = 0;
    var k2start = 0;
    var k2end = 0;
    for (var d = 0; d < max_d; d++) {
        // Bail out if deadline is reached
        if ((new Date).getTime() > deadline) {
            break;
        }

        // Walk the front path one step
        for (var k1 = -d + k1start; k1 <= d - k1end; k1 += 2) {
            var k1_offset = v_offset + k1;
            var x1;
            if (k1 === -d || (k1 !== d && v1[k1_offset - 1] < v1[k1_offset + 1])) {
                x1 = v1[k1_offset + 1];
            } else {
                x1 = v1[k1_offset - 1] + 1;
            }
            var y1 = x1 - k1;
            while (x1 < text1_length && y1 < text2_length &&
                   text1.charAt(x1) === text2.charAt(y1)) {
                x1++;
                y1++;
            }
            v1[k1_offset] = x1;
            if (x1 > text1_length) {
                k1end += 2;
            } else if (y1 > text2_length) {
                k1start += 2;
            } else if (front) {
                var k2_offset = v_offset + delta - k1;
                if (k2_offset >= 0 && k2_offset < v_length && v2[k2_offset] !== -1) {
                    var x2 = text1_length - v2[k2_offset];
                    if (x1 >= x2) {
                        return this.diff_bisectSplit_(text1, text2, x1, y1, deadline);
                    }
                }
            }
        }

        // Walk the reverse path one step
        for (var k2 = -d + k2start; k2 <= d - k2end; k2 += 2) {
            var k2_offset = v_offset + k2;
            var x2;
            if (k2 === -d || (k2 !== d && v2[k2_offset - 1] < v2[k2_offset + 1])) {
                x2 = v2[k2_offset + 1];
            } else {
                x2 = v2[k2_offset - 1] + 1;
            }
            var y2 = x2 - k2;
            while (x2 < text1_length && y2 < text2_length &&
                   text1.charAt(text1_length - x2 - 1) ===
                   text2.charAt(text2_length - y2 - 1)) {
                x2++;
                y2++;
            }
            v2[k2_offset] = x2;
            if (x2 > text1_length) {
                k2end += 2;
            } else if (y2 > text2_length) {
                k2start += 2;
            } else if (!front) {
                var k1_offset = v_offset + delta - k2;
                if (k1_offset >= 0 && k1_offset < v_length && v1[k1_offset] !== -1) {
                    var x1 = v1[k1_offset];
                    var y1 = v_offset + x1 - k1_offset;
                    x2 = text1_length - x2;
                    if (x1 >= x2) {
                        return this.diff_bisectSplit_(text1, text2, x1, y1, deadline);
                    }
                }
            }
        }
    }
    // Diff took too long or # of diffs equals # of characters, no commonality
    return [[DIFF_DELETE, text1], [DIFF_INSERT, text2]];
};

/**
 * Given the location of the 'middle snake', split the diff in two parts and
 * recurse.
 * @param {string} text1 Old string.
 * @param {string} text2 New string.
 * @param {number} x Index of split point in text1.
 * @param {number} y Index of split point in text2.
 * @param {number} deadline Time to stop.
 * @return {!Array.<!Array>} Array of diff tuples.
 * @private
 */
diff_match_patch.prototype.diff_bisectSplit_ = function(text1, text2, x, y, deadline) {
    var text1a = text1.substring(0, x);
    var text2a = text2.substring(0, y);
    var text1b = text1.substring(x);
    var text2b = text2.substring(y);

    var diffs = this.diff_main(text1a, text2a, false, deadline);
    var diffsb = this.diff_main(text1b, text2b, false, deadline);

    return diffs.concat(diffsb);
};

/**
 * Split two texts into an array of strings, reducing diff to a character comparison.
 * @param {string} text1 First string.
 * @param {string} text2 Second string.
 * @return {{chars1: string, chars2: string, lineArray: !Array.<string>}}
 * @private
 */
diff_match_patch.prototype.diff_linesToChars_ = function(text1, text2) {
    var lineArray = [];
    var lineHash = {};
    lineArray[0] = '';

    function diff_linesToCharsMunge_(text) {
        var chars = '';
        var lineStart = 0;
        var lineEnd = -1;
        var lineArrayLength = lineArray.length;
        while (lineEnd < text.length - 1) {
            lineEnd = text.indexOf('\n', lineStart);
            if (lineEnd === -1) {
                lineEnd = text.length - 1;
            }
            var line = text.substring(lineStart, lineEnd + 1);

            if (lineHash.hasOwnProperty ? lineHash.hasOwnProperty(line) :
                (lineHash[line] !== undefined)) {
                chars += String.fromCharCode(lineHash[line]);
            } else {
                lineArrayLength = lineArray.length;
                chars += String.fromCharCode(lineArrayLength);
                lineHash[line] = lineArrayLength;
                lineArray.push(line);
            }
            lineStart = lineEnd + 1;
        }
        return chars;
    }

    var chars1 = diff_linesToCharsMunge_(text1);
    var chars2 = diff_linesToCharsMunge_(text2);
    return {chars1: chars1, chars2: chars2, lineArray: lineArray};
};

/**
 * Rehydrate the text in a diff from a string of line hashes to real lines.
 * @param {!Array.<!Array>} diffs Array of diff tuples.
 * @param {!Array.<string>} lineArray Array of unique strings.
 * @private
 */
diff_match_patch.prototype.diff_charsToLines_ = function(diffs, lineArray) {
    for (var i = 0; i < diffs.length; i++) {
        var chars = diffs[i][1];
        var text = [];
        for (var j = 0; j < chars.length; j++) {
            text[j] = lineArray[chars.charCodeAt(j)];
        }
        diffs[i][1] = text.join('');
    }
};

/**
 * Determine the common prefix of two strings.
 * @param {string} text1 First string.
 * @param {string} text2 Second string.
 * @return {number} The number of characters common to the start of each string.
 */
diff_match_patch.prototype.diff_commonPrefix = function(text1, text2) {
    if (!text1 || !text2 || text1.charAt(0) !== text2.charAt(0)) {
        return 0;
    }
    var pointermin = 0;
    var pointermax = Math.min(text1.length, text2.length);
    var pointermid = pointermax;
    var pointerstart = 0;
    while (pointermin < pointermid) {
        if (text1.substring(pointerstart, pointermid) ===
            text2.substring(pointerstart, pointermid)) {
            pointermin = pointermid;
            pointerstart = pointermin;
        } else {
            pointermax = pointermid;
        }
        pointermid = Math.floor((pointermax - pointermin) / 2 + pointermin);
    }
    return pointermid;
};

/**
 * Determine the common suffix of two strings.
 * @param {string} text1 First string.
 * @param {string} text2 Second string.
 * @return {number} The number of characters common to the end of each string.
 */
diff_match_patch.prototype.diff_commonSuffix = function(text1, text2) {
    if (!text1 || !text2 ||
        text1.charAt(text1.length - 1) !== text2.charAt(text2.length - 1)) {
        return 0;
    }
    var pointermin = 0;
    var pointermax = Math.min(text1.length, text2.length);
    var pointermid = pointermax;
    var pointerend = 0;
    while (pointermin < pointermid) {
        if (text1.substring(text1.length - pointermid, text1.length - pointerend) ===
            text2.substring(text2.length - pointermid, text2.length - pointerend)) {
            pointermin = pointermid;
            pointerend = pointermin;
        } else {
            pointermax = pointermid;
        }
        pointermid = Math.floor((pointermax - pointermin) / 2 + pointermin);
    }
    return pointermid;
};

/**
 * Do the two texts share a substring which is at least half the length of the
 * longer text?
 * @param {string} text1 First string.
 * @param {string} text2 Second string.
 * @return {Array.<string>} Five element Array, or null.
 * @private
 */
diff_match_patch.prototype.diff_halfMatch_ = function(text1, text2) {
    if (this.Diff_Timeout <= 0) {
        return null;
    }
    var longtext = text1.length > text2.length ? text1 : text2;
    var shorttext = text1.length > text2.length ? text2 : text1;
    if (longtext.length < 4 || shorttext.length * 2 < longtext.length) {
        return null;
    }
    var dmp = this;

    function diff_halfMatchI_(longtext, shorttext, i) {
        var seed = longtext.substring(i, i + Math.floor(longtext.length / 4));
        var j = -1;
        var best_common = '';
        var best_longtext_a, best_longtext_b, best_shorttext_a, best_shorttext_b;
        while ((j = shorttext.indexOf(seed, j + 1)) !== -1) {
            var prefixLength = dmp.diff_commonPrefix(longtext.substring(i),
                                                      shorttext.substring(j));
            var suffixLength = dmp.diff_commonSuffix(longtext.substring(0, i),
                                                      shorttext.substring(0, j));
            if (best_common.length < suffixLength + prefixLength) {
                best_common = shorttext.substring(j - suffixLength, j) +
                              shorttext.substring(j, j + prefixLength);
                best_longtext_a = longtext.substring(0, i - suffixLength);
                best_longtext_b = longtext.substring(i + prefixLength);
                best_shorttext_a = shorttext.substring(0, j - suffixLength);
                best_shorttext_b = shorttext.substring(j + prefixLength);
            }
        }
        if (best_common.length * 2 >= longtext.length) {
            return [best_longtext_a, best_longtext_b,
                    best_shorttext_a, best_shorttext_b, best_common];
        } else {
            return null;
        }
    }

    var hm1 = diff_halfMatchI_(longtext, shorttext,
                                Math.ceil(longtext.length / 4));
    var hm2 = diff_halfMatchI_(longtext, shorttext,
                                Math.ceil(longtext.length / 2));
    var hm;
    if (!hm1 && !hm2) {
        return null;
    } else if (!hm2) {
        hm = hm1;
    } else if (!hm1) {
        hm = hm2;
    } else {
        hm = hm1[4].length > hm2[4].length ? hm1 : hm2;
    }

    var text1_a, text1_b, text2_a, text2_b;
    if (text1.length > text2.length) {
        text1_a = hm[0];
        text1_b = hm[1];
        text2_a = hm[2];
        text2_b = hm[3];
    } else {
        text2_a = hm[0];
        text2_b = hm[1];
        text1_a = hm[2];
        text1_b = hm[3];
    }
    var mid_common = hm[4];
    return [text1_a, text1_b, text2_a, text2_b, mid_common];
};

/**
 * Reduce the number of edits by eliminating semantically trivial equalities.
 * @param {!Array.<!Array>} diffs Array of diff tuples.
 */
diff_match_patch.prototype.diff_cleanupSemantic = function(diffs) {
    var changes = false;
    var equalities = [];
    var equalitiesLength = 0;
    var lastEquality = null;
    var pointer = 0;
    var length_insertions1 = 0;
    var length_deletions1 = 0;
    var length_insertions2 = 0;
    var length_deletions2 = 0;
    while (pointer < diffs.length) {
        if (diffs[pointer][0] === DIFF_EQUAL) {
            equalities[equalitiesLength++] = pointer;
            length_insertions1 = length_insertions2;
            length_deletions1 = length_deletions2;
            length_insertions2 = 0;
            length_deletions2 = 0;
            lastEquality = diffs[pointer][1];
        } else {
            if (diffs[pointer][0] === DIFF_INSERT) {
                length_insertions2 += diffs[pointer][1].length;
            } else {
                length_deletions2 += diffs[pointer][1].length;
            }
            if (lastEquality && (lastEquality.length <=
                Math.max(length_insertions1, length_deletions1)) &&
                (lastEquality.length <= Math.max(length_insertions2, length_deletions2))) {
                diffs.splice(equalities[equalitiesLength - 1], 0,
                             [DIFF_DELETE, lastEquality]);
                diffs[equalities[equalitiesLength - 1] + 1][0] = DIFF_INSERT;
                equalitiesLength--;
                equalitiesLength--;
                pointer = equalitiesLength > 0 ? equalities[equalitiesLength - 1] : -1;
                length_insertions1 = 0;
                length_deletions1 = 0;
                length_insertions2 = 0;
                length_deletions2 = 0;
                lastEquality = null;
                changes = true;
            }
        }
        pointer++;
    }

    if (changes) {
        this.diff_cleanupMerge(diffs);
    }
};

/**
 * Reorder and merge like edit sections. Merge equalities.
 * Any edit section can move as long as it doesn't cross an equality.
 * @param {!Array.<!Array>} diffs Array of diff tuples.
 */
diff_match_patch.prototype.diff_cleanupMerge = function(diffs) {
    diffs.push([DIFF_EQUAL, '']);
    var pointer = 0;
    var count_delete = 0;
    var count_insert = 0;
    var text_delete = '';
    var text_insert = '';
    var commonlength;
    while (pointer < diffs.length) {
        switch (diffs[pointer][0]) {
            case DIFF_INSERT:
                count_insert++;
                text_insert += diffs[pointer][1];
                pointer++;
                break;
            case DIFF_DELETE:
                count_delete++;
                text_delete += diffs[pointer][1];
                pointer++;
                break;
            case DIFF_EQUAL:
                if (count_delete + count_insert > 1) {
                    if (count_delete !== 0 && count_insert !== 0) {
                        commonlength = this.diff_commonPrefix(text_insert, text_delete);
                        if (commonlength !== 0) {
                            if ((pointer - count_delete - count_insert) > 0 &&
                                diffs[pointer - count_delete - count_insert - 1][0] ===
                                DIFF_EQUAL) {
                                diffs[pointer - count_delete - count_insert - 1][1] +=
                                    text_insert.substring(0, commonlength);
                            } else {
                                diffs.splice(0, 0, [DIFF_EQUAL,
                                             text_insert.substring(0, commonlength)]);
                                pointer++;
                            }
                            text_insert = text_insert.substring(commonlength);
                            text_delete = text_delete.substring(commonlength);
                        }
                        commonlength = this.diff_commonSuffix(text_insert, text_delete);
                        if (commonlength !== 0) {
                            diffs[pointer][1] = text_insert.substring(text_insert.length -
                                commonlength) + diffs[pointer][1];
                            text_insert = text_insert.substring(0, text_insert.length -
                                commonlength);
                            text_delete = text_delete.substring(0, text_delete.length -
                                commonlength);
                        }
                    }
                    pointer -= count_delete + count_insert;
                    diffs.splice(pointer, count_delete + count_insert);
                    if (text_delete.length) {
                        diffs.splice(pointer, 0, [DIFF_DELETE, text_delete]);
                        pointer++;
                    }
                    if (text_insert.length) {
                        diffs.splice(pointer, 0, [DIFF_INSERT, text_insert]);
                        pointer++;
                    }
                    pointer++;
                } else if (pointer !== 0 && diffs[pointer - 1][0] === DIFF_EQUAL) {
                    diffs[pointer - 1][1] += diffs[pointer][1];
                    diffs.splice(pointer, 1);
                } else {
                    pointer++;
                }
                count_insert = 0;
                count_delete = 0;
                text_delete = '';
                text_insert = '';
                break;
        }
    }
    if (diffs[diffs.length - 1][1] === '') {
        diffs.pop();
    }

    var changes = false;
    pointer = 1;
    while (pointer < diffs.length - 1) {
        if (diffs[pointer - 1][0] === DIFF_EQUAL &&
            diffs[pointer + 1][0] === DIFF_EQUAL) {
            if (diffs[pointer][1].substring(diffs[pointer][1].length -
                diffs[pointer - 1][1].length) === diffs[pointer - 1][1]) {
                diffs[pointer][1] = diffs[pointer - 1][1] +
                    diffs[pointer][1].substring(0, diffs[pointer][1].length -
                    diffs[pointer - 1][1].length);
                diffs[pointer + 1][1] = diffs[pointer - 1][1] + diffs[pointer + 1][1];
                diffs.splice(pointer - 1, 1);
                changes = true;
            } else if (diffs[pointer][1].substring(0, diffs[pointer + 1][1].length) ===
                       diffs[pointer + 1][1]) {
                diffs[pointer - 1][1] += diffs[pointer + 1][1];
                diffs[pointer][1] =
                    diffs[pointer][1].substring(diffs[pointer + 1][1].length) +
                    diffs[pointer + 1][1];
                diffs.splice(pointer + 1, 1);
                changes = true;
            }
        }
        pointer++;
    }
    if (changes) {
        this.diff_cleanupMerge(diffs);
    }
};

// Export for use in modules
if (typeof module !== 'undefined') {
    module.exports = diff_match_patch;
    module.exports['diff_match_patch'] = diff_match_patch;
    module.exports['DIFF_DELETE'] = DIFF_DELETE;
    module.exports['DIFF_INSERT'] = DIFF_INSERT;
    module.exports['DIFF_EQUAL'] = DIFF_EQUAL;
}
