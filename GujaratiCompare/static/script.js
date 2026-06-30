/**
 * ====================================================
 * Gujarati Paragraph Compare Pro
 * static/script.js — Frontend Application Logic
 * ====================================================
 * Handles:
 *   - File upload (drag & drop + click)
 *   - API communication with Flask backend
 *   - Diff result rendering in 3 synchronized panels
 *   - Synchronized scrolling across result panels
 *   - Report download (HTML & PDF)
 *   - Toast notifications
 *   - Loading states
 * ====================================================
 */

(function () {
    'use strict';

    // ================================================
    // State Management
    // ================================================

    /**
     * Application state object.
     * Stores current comparison settings, results, and UI state.
     */
    const AppState = {
        mode: 'word',            // 'word' or 'sentence'
        ignoreCase: false,
        ignoreExtraSpaces: false,
        removeSpecialChars: false,
        flagScriptMismatch: true,  // flag English↔Gujarati word mismatches
        ignorePunctuation: false,  // ignore . , ? !
        comparisonResult: null,  // Last comparison response from API
        isComparing: false,      // Whether a comparison is in progress
    };

    // =    ===========================================
    // DOM References
    // ================================================

    const DOM = {
        // Text editors
        editorA: document.getElementById('editor-a'),
        editorB: document.getElementById('editor-b'),
        editorC: document.getElementById('editor-c'),

        // File inputs
        fileInputA: document.getElementById('file-input-a'),
        fileInputB: document.getElementById('file-input-b'),
        fileInputC: document.getElementById('file-input-c'),

        // Drop zones
        dropZoneA: document.getElementById('drop-zone-a'),
        dropZoneB: document.getElementById('drop-zone-b'),
        dropZoneC: document.getElementById('drop-zone-c'),

        // Footer stats
        statsA: document.getElementById('stats-a'),
        statsB: document.getElementById('stats-b'),
        statsC: document.getElementById('stats-c'),

        // Buttons
        btnCompare: document.getElementById('btn-compare'),
        btnClear: document.getElementById('btn-clear'),
        btnDownloadHTML: document.getElementById('btn-download-html'),
        btnDownloadPDF: document.getElementById('btn-download-pdf'),

        // Toggles
        toggleIgnoreCase: document.getElementById('toggle-ignore-case'),
        toggleIgnoreSpaces: document.getElementById('toggle-ignore-spaces'),
        toggleRemoveSpecial: document.getElementById('toggle-remove-special'),
        toggleScriptMismatch: document.getElementById('toggle-script-mismatch'),
        toggleIgnorePunctuation: document.getElementById('toggle-ignore-punctuation'),

        // Mode buttons
        modeWord: document.getElementById('mode-word'),
        modeSentence: document.getElementById('mode-sentence'),

        // Result panels
        resultPanelA: document.getElementById('result-panel-a'),
        resultPanelB: document.getElementById('result-panel-b'),
        resultPanelC: document.getElementById('result-panel-c'),

        // Similarity cards
        simAB: document.getElementById('sim-ab'),
        simAC: document.getElementById('sim-ac'),
        simBC: document.getElementById('sim-bc'),
        simBarAB: document.getElementById('sim-bar-ab'),
        simBarAC: document.getElementById('sim-bar-ac'),
        simBarBC: document.getElementById('sim-bar-bc'),

        // Diff summary
        summaryAB: document.getElementById('summary-ab'),
        summaryAC: document.getElementById('summary-ac'),
        summaryBC: document.getElementById('summary-bc'),

        // Results section container
        resultsSection: document.getElementById('results-section'),

        // Loading overlay
        loadingOverlay: document.getElementById('loading-overlay'),

        // Toast container
        toastContainer: document.getElementById('toast-container'),
    };

    // ================================================
    // Initialization
    // ================================================

    /**
     * Initialize the application when DOM is ready.
     */
    function init() {
        bindEventListeners();
        updateAllStats();
    }

    // ================================================
    // Event Binding
    // ================================================

    /**
     * Bind all event listeners for the application.
     */
    function bindEventListeners() {
        // Compare & Clear buttons
        DOM.btnCompare.addEventListener('click', handleCompare);
        DOM.btnClear.addEventListener('click', handleClear);

        // Report download buttons
        DOM.btnDownloadHTML.addEventListener('click', handleDownloadHTML);
        DOM.btnDownloadPDF.addEventListener('click', handleDownloadPDF);

        // Toggle switches
        DOM.toggleIgnoreCase.addEventListener('change', function () {
            AppState.ignoreCase = this.checked;
        });
        DOM.toggleIgnoreSpaces.addEventListener('change', function () {
            AppState.ignoreExtraSpaces = this.checked;
        });
        DOM.toggleRemoveSpecial.addEventListener('change', function () {
            AppState.removeSpecialChars = this.checked;
        });
        DOM.toggleScriptMismatch.addEventListener('change', function () {
            AppState.flagScriptMismatch = this.checked;
        });
        DOM.toggleIgnorePunctuation.addEventListener('change', function () {
            AppState.ignorePunctuation = this.checked;
        });

        // Mode selector buttons
        DOM.modeWord.addEventListener('click', function () {
            setMode('word');
        });
        DOM.modeSentence.addEventListener('click', function () {
            setMode('sentence');
        });

        // Text editor input events (for live stats)
        DOM.editorA.addEventListener('input', function () {
            updateStats('a', this.value);
        });
        DOM.editorB.addEventListener('input', function () {
            updateStats('b', this.value);
        });
        DOM.editorC.addEventListener('input', function () {
            updateStats('c', this.value);
        });

        // File upload — click triggers
        setupFileUpload('a', DOM.dropZoneA, DOM.fileInputA, DOM.editorA);
        setupFileUpload('b', DOM.dropZoneB, DOM.fileInputB, DOM.editorB);
        setupFileUpload('c', DOM.dropZoneC, DOM.fileInputC, DOM.editorC);

        // Synchronized scrolling for result panels
        setupSyncScroll();
    }

    // ================================================
    // Mode Selector
    // ================================================

    /**
     * Set the comparison mode (word or sentence).
     * @param {string} mode - 'word' or 'sentence'.
     */
    function setMode(mode) {
        AppState.mode = mode;

        // Update UI
        DOM.modeWord.classList.toggle('active', mode === 'word');
        DOM.modeSentence.classList.toggle('active', mode === 'sentence');
    }

    // ================================================
    // File Upload
    // ================================================

    /**
     * Setup file upload for a panel (drag & drop + click).
     * @param {string} panelId - 'a', 'b', or 'c'.
     * @param {HTMLElement} dropZone - The drop zone element.
     * @param {HTMLInputElement} fileInput - The hidden file input.
     * @param {HTMLTextAreaElement} editor - The text editor textarea.
     */
    function setupFileUpload(panelId, dropZone, fileInput, editor) {
        // Click to upload
        dropZone.addEventListener('click', function () {
            fileInput.click();
        });

        // File input change
        fileInput.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                uploadFile(this.files[0], editor, panelId);
                this.value = ''; // Reset input to allow re-uploading the same file
            }
        });

        // Drag & drop events
        dropZone.addEventListener('dragover', function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');

            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                uploadFile(e.dataTransfer.files[0], editor, panelId);
            }
        });
    }

    /**
     * Upload a file to the backend and populate the editor.
     * @param {File} file - The file to upload.
     * @param {HTMLTextAreaElement} editor - The target editor.
     * @param {string} panelId - 'a', 'b', or 'c'.
     */
    async function uploadFile(file, editor, panelId) {
        // Validate file type
        if (!file.name.toLowerCase().endsWith('.txt')) {
            showToast('Only .txt files are allowed.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.success) {
                editor.value = data.content;
                updateStats(panelId, data.content);
                showToast(`File "${data.filename}" loaded successfully.`, 'success');
            } else {
                showToast(data.error || 'Upload failed.', 'error');
            }
        } catch (error) {
            // Fallback: read file locally if server is not available
            const reader = new FileReader();
            reader.onload = function (e) {
                editor.value = e.target.result;
                updateStats(panelId, e.target.result);
                showToast(`File "${file.name}" loaded locally.`, 'success');
            };
            reader.onerror = function () {
                showToast('Failed to read file.', 'error');
            };
            reader.readAsText(file, 'UTF-8');
        }
    }

    // ================================================
    // Comparison
    // ================================================

    /**
     * Handle the Compare button click.
     * Sends texts to the backend for 3-way comparison.
     */
    async function handleCompare() {
        const textA = DOM.editorA.value.trim();
        const textB = DOM.editorB.value.trim();
        const textC = DOM.editorC.value.trim();

        // Validate: need at least 2 paragraphs
        const filled = [textA, textB, textC].filter(t => t.length > 0).length;
        if (filled < 2) {
            showToast('Please enter at least 2 paragraphs to compare.', 'error');
            return;
        }

        // Prevent double-click
        if (AppState.isComparing) return;
        AppState.isComparing = true;

        showLoading(true);

        try {
            const response = await fetch('/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text_a: textA,
                    text_b: textB,
                    text_c: textC,
                    mode: AppState.mode,
                    ignore_case: AppState.ignoreCase,
                    ignore_extra_spaces: AppState.ignoreExtraSpaces,
                    remove_special_chars: AppState.removeSpecialChars,
                    flag_script_mismatch: AppState.flagScriptMismatch,
                    flag_ignore_punctuation: AppState.ignorePunctuation,
                }),
            });

            const data = await response.json();

            if (data.success) {
                AppState.comparisonResult = data;
                renderResults(data);
                showToast('Comparison complete!', 'success');
            } else {
                showToast(data.error || 'Comparison failed.', 'error');
            }
        } catch (error) {
            showToast('Server error. Please ensure Flask is running.', 'error');
            console.error('Compare error:', error);
        } finally {
            showLoading(false);
            AppState.isComparing = false;
        }
    }

    // ================================================
    // Result Rendering
    // ================================================

    /**
     * Render comparison results into the UI.
     * @param {Object} data - The comparison response from the API.
     */
    function renderResults(data) {
        // Show results section
        DOM.resultsSection.classList.add('visible');

        // Render similarity cards
        renderSimilarity(data.similarity, data.comparison);

        // Render diff summaries
        renderDiffSummary(data.comparison);

        // Render diff view panels
        renderPanels(data.comparison);

        // Scroll to results
        DOM.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Render similarity percentage cards.
     * @param {Object} similarity - { a_vs_b, a_vs_c, b_vs_c } percentages.
     * @param {Object} comparison - The comparison object to check for empty panels.
     */
    function renderSimilarity(similarity, comparison) {
        const hasA = comparison.panels.panel_a && comparison.panels.panel_a.length > 0;
        const hasB = comparison.panels.panel_b && comparison.panels.panel_b.length > 0;
        const hasC = comparison.panels.panel_c && comparison.panels.panel_c.length > 0;

        const cardsContainer = document.querySelector('.similarity-grid');
        let visibleCards = 0;

        // A vs B
        const cardAB = DOM.simAB.closest('.sim-card');
        if (hasA && hasB) {
            DOM.simAB.textContent = similarity.a_vs_b.toFixed(1) + '%';
            DOM.simBarAB.style.width = similarity.a_vs_b + '%';
            cardAB.style.display = 'block';
            visibleCards++;
        } else {
            cardAB.style.display = 'none';
        }

        // A vs C
        const cardAC = DOM.simAC.closest('.sim-card');
        if (hasA && hasC) {
            DOM.simAC.textContent = similarity.a_vs_c.toFixed(1) + '%';
            DOM.simBarAC.style.width = similarity.a_vs_c + '%';
            cardAC.style.display = 'block';
            visibleCards++;
        } else {
            cardAC.style.display = 'none';
        }

        // B vs C
        const cardBC = DOM.simBC.closest('.sim-card');
        if (hasB && hasC) {
            DOM.simBC.textContent = similarity.b_vs_c.toFixed(1) + '%';
            DOM.simBarBC.style.width = similarity.b_vs_c + '%';
            cardBC.style.display = 'block';
            visibleCards++;
        } else {
            cardBC.style.display = 'none';
        }
        
        // Update grid layout
        if (visibleCards === 1) {
            cardsContainer.style.gridTemplateColumns = '1fr';
        } else if (visibleCards === 2) {
            cardsContainer.style.gridTemplateColumns = 'repeat(2, 1fr)';
        } else {
            cardsContainer.style.gridTemplateColumns = 'repeat(3, 1fr)';
        }
    }

    /**
     * Render diff summary statistics for each comparison pair.
     * @param {Object} comparison - Comparison result object.
     */
    function renderDiffSummary(comparison) {
        const pairs = [
            { el: DOM.summaryAB, data: comparison.a_vs_b },
            { el: DOM.summaryAC, data: comparison.a_vs_c },
            { el: DOM.summaryBC, data: comparison.b_vs_c },
        ];

        pairs.forEach(function (pair) {
            if (!pair.data || !pair.data.stats) {
                pair.el.innerHTML = '<p style="color: var(--text-muted);">No data</p>';
                // If it's B vs C or A vs C and we only have 2 texts, we can hide its parent container
                pair.el.closest('.summary-card').style.display = 'none';
                return;
            }
            
            pair.el.closest('.summary-card').style.display = 'block';

            const stats = pair.data.stats;
            pair.el.innerHTML =
                '<span class="stat-badge added">+ ' + stats.added_count + ' Added</span>' +
                '<span class="stat-badge deleted">− ' + stats.deleted_count + ' Deleted</span>' +
                '<span class="stat-badge changed">~ ' + stats.changed_count + ' Changed</span>' +
                '<span class="stat-badge missing">? ' + stats.missing_count + ' Missing</span>';

            // Clean up any old list
            const existingList = pair.el.closest('.summary-card').querySelector('.word-changes-list');
            if (existingList) {
                existingList.remove();
            }

            // Append word changes list (ONLY wrong words)
            if (pair.data.changed_words && pair.data.changed_words.length > 0) {
                // Header with Download PDF button
                let listHtml = '<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; margin-bottom: 8px;">' +
                               '<h5 style="margin: 0; color: var(--text-secondary); font-size: 0.85rem;">Wrong Words</h5>' +
                               '<button class="btn btn-secondary btn-sm" onclick="downloadWrongWordsPdf(\'' + pair.el.id + '\')" style="padding: 4px 8px; font-size: 0.75rem;">⬇ Download PDF</button>' +
                               '</div>';
                listHtml += '<table class="wrong-words-table" id="wrong-words-list-' + pair.el.id + '">';
                listHtml += '<tbody>';
                pair.data.changed_words.forEach(function(change) {
                    listHtml += '<tr>' +
                        '<td><span class="diff-deleted">' + escapeHtml(change.old) + '</span></td>' +
                        '<td><span class="diff-added">' + escapeHtml(change.new) + '</span></td>' +
                    '</tr>';
                });
                listHtml += '</tbody></table>';
                pair.el.insertAdjacentHTML('afterend', listHtml);
            }
        });
    }

    /**
     * Download the wrong words list as a PDF using the browser's print dialog.
     * @param {string} pairId - The ID of the summary container.
     */
    window.downloadWrongWordsPdf = function(pairId) {
        const listContainer = document.getElementById('wrong-words-list-' + pairId);
        if (!listContainer) return;
        
        const listHtml = listContainer.outerHTML;
        const printWindow = window.open('', '_blank');
        
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Wrong Words Report</title>
                <style>
                    body { 
                        font-family: 'Noto Sans Gujarati', sans-serif, Arial; 
                        padding: 40px; 
                        color: #000; 
                        -webkit-print-color-adjust: exact; 
                        print-color-adjust: exact; 
                    }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 16px; }
                    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: middle; }
                    th { background-color: #f8f9fa; color: #333; font-weight: bold; }
                    .diff-deleted { 
                        background-color: #ffcdd2; 
                        padding: 2px 6px; 
                        border-radius: 3px; 
                        font-weight: bold; 
                        display: inline-block;
                    }
                    .diff-added { 
                        background-color: #c8e6c9; 
                        padding: 2px 6px; 
                        border-radius: 3px; 
                        font-weight: bold; 
                        display: inline-block;
                    }
                </style>
            </head>
            <body>
                <div style="margin-top: 20px;">
                    ${listHtml}
                </div>
                <script>
                    window.onload = function() {
                        window.print();
                        setTimeout(function() { window.close(); }, 500);
                    }
                </script>
            </body>
            </html>
        `);
        printWindow.document.close();
    };

    /**
     * Download the full merged view panel as a PDF using the browser's print dialog.
     */
    window.downloadMergedViewPdf = function() {
        const listHtml = document.getElementById('result-panel-a').innerHTML;
        const printWindow = window.open('', '_blank');
        
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Merged Transcript Report</title>
                <style>
                    body { 
                        font-family: 'Noto Sans Gujarati', sans-serif, Arial; 
                        padding: 40px; 
                        color: #000; 
                        line-height: 1.8; 
                        font-size: 16px; 
                        -webkit-print-color-adjust: exact; 
                        print-color-adjust: exact; 
                    }
                    h2 { color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }
                    
                    /* Inline diff styles for PDF */
                    span { display: inline; }
                    .diff-deleted { 
                        background-color: #ffcdd2; 
                        padding: 0 4px; 
                        border-radius: 3px; 
                        font-weight: bold;
                    }
                    .diff-added { 
                        background-color: #c8e6c9; 
                        padding: 0 4px; 
                        border-radius: 3px; 
                        font-weight: bold;
                    }
                    .diff-changed {
                        background-color: #fff9c4;
                    }
                    .diff-script-mismatch {
                        background-color: #e1bee7;
                    }
                </style>
            </head>
            <body>
                <div style="margin-top: 20px;">
                    ${listHtml}
                </div>
                <script>
                    window.onload = function() {
                        window.print();
                        setTimeout(function() { window.close(); }, 500);
                    }
                </script>
            </body>
            </html>
        `);
        printWindow.document.close();
    };

    /**
     * Render the synchronized diff view.
     * @param {Object} comparison - The comparison object from API.
     */
    function renderPanels(comparison) {
        const panels = comparison.panels;
        // Find containers
        const resultPanelsContainer = document.querySelector('.result-panels');
        const summaryCardsContainer = document.querySelector('.diff-summary');
        
        const hasC = panels.panel_c && panels.panel_c.length > 0;

        if (!hasC && comparison.a_vs_b && comparison.a_vs_b.inline_diffs) {
            // 2-Way Inline Merged View
            const panelA = DOM.resultPanelA.closest('.result-panel');
            panelA.style.display = 'block';
            
            const headerA = panelA.querySelector('.result-panel-header');
            headerA.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <h3 style="margin: 0;">Transcript 1 ↔ Transcript 2 Merged View</h3>
                    <button class="btn btn-secondary btn-sm" onclick="downloadMergedViewPdf()" style="padding: 4px 8px; font-size: 0.85rem;">⬇ Download PDF</button>
                </div>
            `;
            
            DOM.resultPanelA.innerHTML = renderDiffSegments(comparison.a_vs_b.inline_diffs);
            
            DOM.resultPanelB.closest('.result-panel').style.display = 'none';
            DOM.resultPanelB.innerHTML = '';
            DOM.resultPanelC.closest('.result-panel').style.display = 'none';
            DOM.resultPanelC.innerHTML = '';

            resultPanelsContainer.style.gridTemplateColumns = '1fr';
            summaryCardsContainer.style.gridTemplateColumns = '1fr';
        } else {
            // Standard Multi-Panel View
            const headerA = DOM.resultPanelA.closest('.result-panel').querySelector('.result-panel-header');
            headerA.innerHTML = `
                <h3>
                    <span class="panel-label panel-label-a">A</span>
                    Paragraph A
                </h3>
            `;
            
            const panelData = [
                { el: DOM.resultPanelA, data: panels.panel_a },
                { el: DOM.resultPanelB, data: panels.panel_b },
                { el: DOM.resultPanelC, data: panels.panel_c }
            ];

            let visibleCount = 0;

            panelData.forEach(panel => {
                const parent = panel.el.closest('.result-panel');
                if (!panel.data || panel.data.length === 0) {
                    parent.style.display = 'none';
                    panel.el.innerHTML = '';
                } else {
                    parent.style.display = 'block';
                    panel.el.innerHTML = renderDiffSegments(panel.data);
                    visibleCount++;
                }
            });

            // Update grid layouts based on visible panels
            if (visibleCount === 2) {
                resultPanelsContainer.style.gridTemplateColumns = 'repeat(2, 1fr)';
                summaryCardsContainer.style.gridTemplateColumns = '1fr';
            } else {
                resultPanelsContainer.style.gridTemplateColumns = 'repeat(3, 1fr)';
                summaryCardsContainer.style.gridTemplateColumns = 'repeat(3, 1fr)';
            }
        }
    }

    /**
     * Convert an array of diff segments into HTML markup.
     * @param {Array} segments - Array of { operation, text } objects.
     * @returns {string} HTML string with highlighted spans.
     */
    function renderDiffSegments(segments) {
        if (!segments || segments.length === 0) {
            return '<span style="color: var(--text-muted); font-style: italic;">No text provided</span>';
        }

        var html = '';
        for (var i = 0; i < segments.length; i++) {
            var seg = segments[i];
            var escapedText = escapeHtml(seg.text);
            var cssClass = '';

            switch (seg.operation) {
                case 'added':
                    cssClass = 'diff-added';
                    break;
                case 'deleted':
                    cssClass = 'diff-deleted';
                    break;
                case 'changed':
                    cssClass = 'diff-changed';
                    break;
                case 'missing':
                    cssClass = 'diff-missing';
                    break;
                case 'script_mismatch':
                    cssClass = 'diff-script-mismatch';
                    break;
                default:
                    cssClass = '';
            }

            if (cssClass) {
                html += '<span class="' + cssClass + '" title="' + seg.operation + '">' + escapedText + '</span> ';
            } else {
                html += '<span>' + escapedText + '</span> ';
            }
        }

        return html;
    }

    // ================================================
    // Synchronized Scrolling
    // ================================================

    /**
     * Setup synchronized scrolling across the 3 result panels.
     * Scrolling one panel scrolls all others proportionally.
     */
    function setupSyncScroll() {
        var panels = [DOM.resultPanelA, DOM.resultPanelB, DOM.resultPanelC];
        var isSyncing = false;

        panels.forEach(function (panel) {
            if (!panel) return;

            panel.addEventListener('scroll', function () {
                if (isSyncing) return;
                isSyncing = true;

                var scrollTop = this.scrollTop;
                var scrollHeight = this.scrollHeight - this.clientHeight;
                var scrollRatio = scrollHeight > 0 ? scrollTop / scrollHeight : 0;

                panels.forEach(function (otherPanel) {
                    if (otherPanel !== panel && otherPanel) {
                        var otherScrollHeight = otherPanel.scrollHeight - otherPanel.clientHeight;
                        otherPanel.scrollTop = scrollRatio * otherScrollHeight;
                    }
                });

                // Use requestAnimationFrame to release the sync lock
                requestAnimationFrame(function () {
                    isSyncing = false;
                });
            });
        });
    }

    // ================================================
    // Clear
    // ================================================

    /**
     * Handle the Clear button click.
     * Resets all editors and hides results.
     */
    function handleClear() {
        // Clear editors
        DOM.editorA.value = '';
        DOM.editorB.value = '';
        DOM.editorC.value = '';

        // Clear result panels
        DOM.resultPanelA.innerHTML = '';
        DOM.resultPanelB.innerHTML = '';
        DOM.resultPanelC.innerHTML = '';

        // Hide results section
        DOM.resultsSection.classList.remove('visible');

        // Reset stats
        updateAllStats();

        // Clear stored result
        AppState.comparisonResult = null;

        showToast('All cleared.', 'info');
    }

    // ================================================
    // Report Downloads
    // ================================================

    /**
     * Handle HTML report download.
     */
    async function handleDownloadHTML() {
        if (!AppState.comparisonResult) {
            showToast('Run a comparison first.', 'error');
            return;
        }

        showLoading(true);

        try {
            const response = await fetch('/report/html', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    comparison_data: AppState.comparisonResult.comparison,
                    similarity_data: AppState.comparisonResult.similarity,
                    stats_data: AppState.comparisonResult.stats,
                    timestamp: AppState.comparisonResult.timestamp,
                    texts: {
                        a: DOM.editorA.value,
                        b: DOM.editorB.value,
                        c: DOM.editorC.value,
                    },
                }),
            });

            if (response.ok) {
                const blob = await response.blob();
                downloadBlob(blob, 'gujarati_compare_report.html');
                showToast('HTML report downloaded.', 'success');
            } else {
                const data = await response.json();
                showToast(data.error || 'Report generation failed.', 'error');
            }
        } catch (error) {
            showToast('Failed to generate report.', 'error');
            console.error('Report error:', error);
        } finally {
            showLoading(false);
        }
    }

    /**
     * Handle PDF report download.
     */
    async function handleDownloadPDF() {
        if (!AppState.comparisonResult) {
            showToast('Run a comparison first.', 'error');
            return;
        }

        showLoading(true);

        try {
            const response = await fetch('/report/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    comparison_data: AppState.comparisonResult.comparison,
                    similarity_data: AppState.comparisonResult.similarity,
                    stats_data: AppState.comparisonResult.stats,
                    timestamp: AppState.comparisonResult.timestamp,
                    texts: {
                        a: DOM.editorA.value,
                        b: DOM.editorB.value,
                        c: DOM.editorC.value,
                    },
                }),
            });

            if (response.ok) {
                const blob = await response.blob();
                downloadBlob(blob, 'gujarati_compare_report.pdf');
                showToast('PDF report downloaded.', 'success');
            } else {
                const data = await response.json();
                showToast(data.error || 'PDF generation failed.', 'error');
            }
        } catch (error) {
            showToast('Failed to generate PDF report.', 'error');
            console.error('PDF report error:', error);
        } finally {
            showLoading(false);
        }
    }

    /**
     * Download a Blob as a file.
     * @param {Blob} blob - The file blob.
     * @param {string} filename - The download filename.
     */
    function downloadBlob(blob, filename) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // ================================================
    // Statistics
    // ================================================

    /**
     * Update word/character stats for a panel.
     * @param {string} panelId - 'a', 'b', or 'c'.
     * @param {string} text - The current text content.
     */
    function updateStats(panelId, text) {
        var words = text.trim() ? text.trim().split(/\s+/).length : 0;
        var chars = text.length;

        var statsEl = panelId === 'a' ? DOM.statsA :
                      panelId === 'b' ? DOM.statsB : DOM.statsC;

        if (statsEl) {
            statsEl.textContent = words + ' words · ' + chars + ' chars';
        }
    }

    /**
     * Update stats for all panels.
     */
    function updateAllStats() {
        updateStats('a', DOM.editorA ? DOM.editorA.value : '');
        updateStats('b', DOM.editorB ? DOM.editorB.value : '');
        updateStats('c', DOM.editorC ? DOM.editorC.value : '');
    }

    // ================================================
    // Loading Overlay
    // ================================================

    /**
     * Show or hide the loading overlay.
     * @param {boolean} show - Whether to show the overlay.
     */
    function showLoading(show) {
        if (DOM.loadingOverlay) {
            DOM.loadingOverlay.classList.toggle('visible', show);
        }
    }

    // ================================================
    // Toast Notifications
    // ================================================

    /**
     * Show a toast notification.
     * @param {string} message - The message to display.
     * @param {string} type - 'success', 'error', or 'info'.
     * @param {number} duration - Duration in ms (default 3500).
     */
    function showToast(message, type, duration) {
        type = type || 'info';
        duration = duration || 3500;

        var toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.textContent = message;

        DOM.toastContainer.appendChild(toast);

        // Auto-remove after duration
        setTimeout(function () {
            toast.classList.add('fade-out');
            setTimeout(function () {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);
    }

    // ================================================
    // Utility Functions
    // ================================================

    /**
     * Escape HTML special characters to prevent XSS.
     * @param {string} text - Raw text.
     * @returns {string} Escaped HTML-safe text.
     */
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // ================================================
    // Run on DOM Ready
    // ================================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
