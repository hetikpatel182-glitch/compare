# ====================================================
# Indian Languages Paragraph Compare Pro
# app.py — Flask Backend Application
# ====================================================
# Main Flask application with routes for:
#   - / (index page)
#   - /compare (JSON API for 3-way comparison)
#   - /upload (file upload handler)
#   - /report/html (HTML report download)
#   - /report/pdf (PDF report download)
# ====================================================

import os
import json
import datetime
from typing import Optional

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    abort,
)

from utils.parser import TextParser
from utils.compare import ComparisonEngine
from utils.similarity import SimilarityCalculator

# ====================================================
# App Configuration
# ====================================================

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max upload
# Serverless environments (like Vercel) only allow writing to /tmp
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'

# Ensure upload directory exists
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception:
    pass

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'json'}


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ====================================================
# Routes
# ====================================================

@app.route('/')
def index():
    """Serve the main comparison interface."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle .txt file upload.

    Expects a multipart form with a 'file' field.
    Returns the text content of the uploaded file as JSON.

    Response JSON:
        {
            "success": true,
            "content": "<file text content>",
            "filename": "<original filename>",
            "stats": { char_count, word_count, sentence_count, has_non_ascii }
        }
    """
    # Validate file presence
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': 'Only .txt and .json files are allowed.'
        }), 400

    try:
        # Read file content as UTF-8
        content = file.read().decode('utf-8')

        # Get text statistics
        parser = TextParser()
        stats = parser.get_text_stats(content)

        return jsonify({
            'success': True,
            'content': content,
            'filename': file.filename,
            'stats': stats,
        })

    except UnicodeDecodeError:
        return jsonify({
            'success': False,
            'error': 'File is not valid UTF-8 encoded text.'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error reading file: {str(e)}'
        }), 500


@app.route('/compare', methods=['POST'])
def compare():
    """
    Perform 3-way comparison of three paragraphs.

    Expects JSON body:
        {
            "text_a": "...",
            "text_b": "...",
            "text_c": "...",
            "mode": "word" | "sentence",
            "ignore_case": true | false,
            "ignore_extra_spaces": true | false,
            "remove_special_chars": true | false,
            "flag_script_mismatch": true | false
        }

    Response JSON:
        {
            "success": true,
            "comparison": { a_vs_b, a_vs_c, b_vs_c, panels },
            "similarity": { a_vs_b, a_vs_c, b_vs_c },
            "stats": {
                "a": { char_count, word_count, ... },
                "b": { ... },
                "c": { ... }
            },
            "timestamp": "ISO 8601 timestamp"
        }
    """
    # Parse request JSON
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided.'}), 400

    text_a = data.get('text_a', '')
    text_b = data.get('text_b', '')
    text_c = data.get('text_c', '')
    mode = data.get('mode', 'word')
    ignore_case = data.get('ignore_case', False)
    ignore_extra_spaces = data.get('ignore_extra_spaces', False)
    remove_special_chars = data.get('remove_special_chars', False)
    flag_script_mismatch = data.get('flag_script_mismatch', True)
    flag_ignore_punctuation = data.get('flag_ignore_punctuation', False)

    # Validate at least two paragraphs are provided
    filled = sum(1 for t in [text_a, text_b, text_c] if t.strip())
    if filled < 2:
        return jsonify({
            'success': False,
            'error': 'Please provide at least two paragraphs to compare.'
        }), 400

    # Validate mode
    if mode not in ('word', 'sentence'):
        return jsonify({
            'success': False,
            'error': "Mode must be 'word' or 'sentence'."
        }), 400

    try:
        # Create parser with user settings
        parser = TextParser(
            ignore_case=ignore_case,
            ignore_extra_spaces=ignore_extra_spaces,
            remove_special_chars=remove_special_chars,
        )

        # Initialize engines with shared parser
        engine = ComparisonEngine(parser=parser)
        similarity_calc = SimilarityCalculator(parser=parser)

        # Perform 3-way comparison
        comparison = engine.compare_three(
            text_a, text_b, text_c,
            mode=mode,
            flag_script_mismatch=flag_script_mismatch,
            flag_ignore_punctuation=flag_ignore_punctuation
        )

        # Compute similarity percentages
        similarity = similarity_calc.compute_pairwise_percentage(
            text_a, text_b, text_c, mode='word'
        )

        # Compute text statistics
        stats = {
            'a': parser.get_text_stats(text_a),
            'b': parser.get_text_stats(text_b),
            'c': parser.get_text_stats(text_c),
        }

        # Timestamp
        timestamp = datetime.datetime.now().isoformat()

        return jsonify({
            'success': True,
            'comparison': comparison,
            'similarity': similarity,
            'stats': stats,
            'timestamp': timestamp,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Comparison failed: {str(e)}'
        }), 500


@app.route('/report/html', methods=['POST'])
def report_html():
    """
    Generate and return an HTML comparison report.

    Expects same JSON body as /compare.
    Returns an HTML file as attachment download.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided.'}), 400

    try:
        # Extract comparison data from the request
        comparison_data = data.get('comparison_data', {})
        similarity_data = data.get('similarity_data', {})
        stats_data = data.get('stats_data', {})
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        texts = data.get('texts', {})

        # Generate HTML report
        html_content = _generate_html_report(
            comparison_data, similarity_data, stats_data,
            timestamp, texts
        )

        # Write to temp file and send
        report_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            f'report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        )
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return send_file(
            report_path,
            as_attachment=True,
            download_name='indian_compare_report.html',
            mimetype='text/html',
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Report generation failed: {str(e)}'
        }), 500


@app.route('/report/pdf', methods=['POST'])
def report_pdf():
    """
    Generate and return a PDF comparison report.

    Uses WeasyPrint to convert the HTML report to PDF.
    Falls back to an error message if WeasyPrint is not installed.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided.'}), 400

    try:
        # Extract comparison data
        comparison_data = data.get('comparison_data', {})
        similarity_data = data.get('similarity_data', {})
        stats_data = data.get('stats_data', {})
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        texts = data.get('texts', {})
        language = data.get('language', 'Hindi')

        # Generate HTML report first
        html_content = _generate_html_report(
            comparison_data, similarity_data, stats_data,
            timestamp, texts
        )

        # Convert to PDF using WeasyPrint
        try:
            from weasyprint import HTML
            pdf_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                f'report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            )
            HTML(string=html_content).write_pdf(pdf_path)

            return send_file(
                pdf_path,
                as_attachment=True,
                download_name='indian_compare_report.pdf',
                mimetype='application/pdf',
            )

        except ImportError:
            return jsonify({
                'success': False,
                'error': (
                    'WeasyPrint is not installed. '
                    'Install it with: pip install WeasyPrint'
                )
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'PDF generation failed: {str(e)}'
        }), 500


# ====================================================
# Report Generation Helper
# ====================================================

def _generate_html_report(
    comparison_data: dict,
    similarity_data: dict,
    stats_data: dict,
    timestamp: str,
    texts: dict
) -> str:
    """
    Generate a standalone HTML comparison report.

    The report includes:
        - Header with timestamp
        - Original texts
        - Similarity percentages
        - Diff highlights for all pairwise comparisons
        - Statistics summary

    Args:
        comparison_data: Structured comparison results.
        similarity_data: Pairwise similarity percentages.
        stats_data: Text statistics for each paragraph.
        timestamp: ISO 8601 timestamp of the comparison.
        texts: Dictionary with keys 'a', 'b', 'c' containing original texts.

    Returns:
        Complete HTML string for the report.
    """
    # Escape text for HTML
    def esc(text):
        return (
            str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )

    # Build similarity rows
    sim_a_b = similarity_data.get('a_vs_b', 0)
    sim_a_c = similarity_data.get('a_vs_c', 0)
    sim_b_c = similarity_data.get('b_vs_c', 0)

    # Build diff HTML for each comparison pair
    def render_diff_pair(pair_data, label):
        if not pair_data:
            return f'<p>No data for {label}</p>'

        html = f'<h3>{esc(label)}</h3>'
        html += '<div class="diff-pair">'

        # Stats
        stats = pair_data.get('stats', {})
        html += '<div class="diff-stats">'
        html += f'<span class="stat">Added: {stats.get("added_count", 0)}</span>'
        html += f'<span class="stat">Deleted: {stats.get("deleted_count", 0)}</span>'
        html += f'<span class="stat">Changed: {stats.get("changed_count", 0)}</span>'
        html += '</div>'

        # Left diffs
        html += '<div class="diff-side"><h4>Left</h4><div class="diff-content">'
        for d in pair_data.get('left_diffs', []):
            op = d.get('operation', 'equal')
            text = esc(d.get('text', ''))
            if op != 'equal':
                html += f'<span class="diff-{op}">{text}</span> '
            else:
                html += f'{text} '
        html += '</div></div>'

        # Right diffs
        html += '<div class="diff-side"><h4>Right</h4><div class="diff-content">'
        for d in pair_data.get('right_diffs', []):
            op = d.get('operation', 'equal')
            text = esc(d.get('text', ''))
            if op != 'equal':
                html += f'<span class="diff-{op}">{text}</span> '
            else:
                html += f'{text} '
        html += '</div></div>'

        html += '</div>'
        return html

    # Build the full report HTML
    language = data.get('language', 'Hindi')
    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Indian Languages Compare Pro — Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Noto Sans Gujarati', sans-serif;
            background: #1a1a2e;
            color: #e0e0e0;
            padding: 40px;
            line-height: 1.6;
        }}
        .report-header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: linear-gradient(135deg, #16213e, #0f3460);
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .report-header h1 {{
            font-size: 28px;
            background: linear-gradient(135deg, #e94560, #f5a623);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        .report-header .timestamp {{
            color: #888;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 30px;
            padding: 24px;
            background: #16213e;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .section h2 {{
            color: #e94560;
            margin-bottom: 16px;
            font-size: 20px;
        }}
        .similarity-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }}
        .sim-card {{
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            text-align: center;
        }}
        .sim-card .label {{ color: #aaa; font-size: 14px; }}
        .sim-card .value {{
            font-size: 32px;
            font-weight: 700;
            color: #4caf50;
        }}
        .text-panel {{
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin: 10px 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-size: 15px;
        }}
        .diff-pair {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin: 16px 0;
        }}
        .diff-side {{
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }}
        .diff-side h4 {{ color: #aaa; margin-bottom: 10px; }}
        .diff-content {{
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.8;
        }}
        .diff-stats {{
            grid-column: span 2;
            display: flex;
            gap: 20px;
            padding: 10px 0;
        }}
        .stat {{
            padding: 6px 14px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            font-size: 13px;
        }}
        .diff-added {{
            background: rgba(76, 175, 80, 0.3);
            color: #81c784;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .diff-deleted {{
            background: rgba(244, 67, 54, 0.3);
            color: #ef5350;
            padding: 2px 6px;
            border-radius: 4px;
            text-decoration: line-through;
        }}
        .diff-changed {{
            background: rgba(255, 235, 59, 0.3);
            color: #fff176;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .diff-missing {{
            background: rgba(158, 158, 158, 0.3);
            color: #bdbdbd;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        @media print {{
            body {{ background: white; color: #333; padding: 20px; }}
            .report-header {{ background: #f5f5f5; border: 1px solid #ddd; }}
            .report-header h1 {{ color: #e94560; -webkit-text-fill-color: #e94560; }}
            .section {{ background: #fafafa; border: 1px solid #eee; }}
            .diff-added {{ background: #c8e6c9; color: #2e7d32; }}
            .diff-deleted {{ background: #ffcdd2; color: #c62828; }}
            .diff-changed {{ background: #fff9c4; color: #f57f17; }}
            .diff-missing {{ background: #eeeeee; color: #616161; }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>Indian Languages Paragraph Compare Pro</h1>
        <div class="timestamp">Language: {esc(language)} &nbsp;|&nbsp; Report generated: {esc(timestamp)}</div>
    </div>

    <div class="section">
        <h2>Similarity</h2>
        <div class="similarity-grid">
            <div class="sim-card">
                <div class="label">A ↔ B</div>
                <div class="value">{sim_a_b}%</div>
            </div>
            <div class="sim-card">
                <div class="label">A ↔ C</div>
                <div class="value">{sim_a_c}%</div>
            </div>
            <div class="sim-card">
                <div class="label">B ↔ C</div>
                <div class="value">{sim_b_c}%</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Original Texts</h2>
        <h3>Paragraph A</h3>
        <div class="text-panel">{esc(texts.get('a', ''))}</div>
        <h3>Paragraph B</h3>
        <div class="text-panel">{esc(texts.get('b', ''))}</div>
        <h3>Paragraph C</h3>
        <div class="text-panel">{esc(texts.get('c', ''))}</div>
    </div>

    <div class="section">
        <h2>Differences</h2>
        {render_diff_pair(comparison_data.get('a_vs_b', {}), 'A vs B')}
        {render_diff_pair(comparison_data.get('a_vs_c', {}), 'A vs C')}
        {render_diff_pair(comparison_data.get('b_vs_c', {}), 'B vs C')}
    </div>

    <div class="section">
        <h2>Statistics</h2>
        <table style="width:100%; border-collapse:collapse;">
            <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
                <th style="text-align:left; padding:10px; color:#aaa;">Metric</th>
                <th style="text-align:center; padding:10px; color:#aaa;">Paragraph A</th>
                <th style="text-align:center; padding:10px; color:#aaa;">Paragraph B</th>
                <th style="text-align:center; padding:10px; color:#aaa;">Paragraph C</th>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:10px;">Characters</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('a', {}).get('char_count', 0)}</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('b', {}).get('char_count', 0)}</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('c', {}).get('char_count', 0)}</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:10px;">Words</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('a', {}).get('word_count', 0)}</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('b', {}).get('word_count', 0)}</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('c', {}).get('word_count', 0)}</td>
            </tr>
            <tr>
                <td style="padding:10px;">Sentences</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('a', {}).get('sentence_count', 0)}</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('b', {}).get('sentence_count', 0)}</td>
                <td style="text-align:center; padding:10px;">{stats_data.get('c', {}).get('sentence_count', 0)}</td>
            </tr>
        </table>
    </div>
</body>
</html>"""

    return report_html


# ====================================================
# Entry Point
# ====================================================

if __name__ == '__main__':
    print("=" * 52)
    print("  Indian Languages Paragraph Compare Pro")
    print("  Running at: http://0.0.0.0:5000")
    print("=" * 52)
    app.run(debug=True, host='0.0.0.0', port=5000)
