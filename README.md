# Gujarati Paragraph Compare Pro

A professional offline web application for comparing 3 Gujarati paragraphs simultaneously with word-level diff highlighting, similarity scoring, and downloadable reports.

---

## Features

- **3-Way Comparison** — Compare three Gujarati transcripts side-by-side
- **Word & Sentence Mode** — Toggle between word-level and sentence-level diffing
- **Color-Coded Highlights** — Green (added), Red (deleted), Yellow (changed), Gray (missing)
- **Similarity Scoring** — SequenceMatcher-based pairwise similarity percentages (A↔B, A↔C, B↔C)
- **Synchronized Scrolling** — All three result panels scroll together proportionally
- **File Upload** — Drag & drop or click to upload `.txt` files (UTF-8)
- **Copy/Paste** — Directly paste Gujarati text into the editors
- **Ignore Case / Ignore Spaces** — Configurable normalization options
- **HTML Report** — Download a styled HTML comparison report
- **PDF Report** — Download a PDF report (requires WeasyPrint)
- **Fully Offline** — No CDN, no external fonts, no network requests
- **Gujarati Unicode** — Full UTF-8 / Gujarati Unicode support
- **Performance** — Handles paragraphs up to 100,000+ words

---

## Project Structure

```
GujaratiCompare/
│
├── app.py                          # Flask backend application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── templates/
│   └── index.html                  # Main HTML page
│
├── static/
│   ├── style.css                   # Dark theme CSS
│   ├── script.js                   # Frontend JavaScript
│   └── diff_match_patch.js         # Google's diff-match-patch (bundled)
│
├── uploads/                        # Temporary upload directory
│
└── utils/
    ├── __init__.py                 # Package initializer
    ├── parser.py                   # Text parser (UTF-8, tokenization)
    ├── similarity.py               # Similarity calculator (SequenceMatcher)
    └── compare.py                  # Comparison engine (diff-match-patch + difflib)
```

---

## Setup

### Prerequisites

- Python 3.13 or higher
- pip (Python package manager)

### Installation

1. **Clone or download** this project.

2. **Navigate** to the project directory:
   ```bash
   cd GujaratiCompare
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment**:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   > **Note:** WeasyPrint requires GTK libraries on some systems.
   > If PDF generation fails, HTML reports will still work.
   > See [WeasyPrint docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for platform-specific setup.

---

## Usage

### Start the Server

```bash
python app.py
```

The application will start at: **http://127.0.0.1:5000**

### Using the Application

1. **Enter text** — Paste Gujarati text into the 3 editor panels, or upload `.txt` files.

2. **Configure options** — Choose Word Mode or Sentence Mode. Toggle Ignore Case / Ignore Spaces.

3. **Click Compare** — The application computes:
   - Pairwise similarity percentages (A↔B, A↔C, B↔C)
   - Word/sentence-level differences
   - Color-coded highlights in synchronized panels

4. **Review results** — Scroll through the three aligned result panels. Highlights show:
   - 🟢 **Green** — Added words
   - 🔴 **Red** — Deleted words
   - 🟡 **Yellow** — Changed words
   - ⚪ **Gray** — Missing words

5. **Download reports** — Click HTML Report or PDF Report to download.

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.13+, Flask                 |
| Frontend   | HTML5, CSS3, Vanilla JavaScript     |
| Comparison | diff-match-patch, difflib, SequenceMatcher |
| PDF        | WeasyPrint                          |

---

## API Endpoints

| Method | Endpoint        | Description                    |
|--------|-----------------|--------------------------------|
| GET    | `/`             | Main application page          |
| POST   | `/upload`       | Upload .txt file               |
| POST   | `/compare`      | 3-way comparison (JSON API)    |
| POST   | `/report/html`  | Generate HTML report           |
| POST   | `/report/pdf`   | Generate PDF report            |

---

## License

This project is for internal/personal use. The bundled `diff_match_patch.js` is licensed under Apache 2.0 by Google.
