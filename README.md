## Setup

1. Create and activate a virtual environment
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add desired RSS feed links to `rssfeeds.txt` (one link on each line)
4. Add desired keywords to match job postings against to `keywords.txt` (one keyword on each line)

## Usage

```bash
python run.py
```

Results will be appended to `output.html`