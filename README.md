# Job Notifier

A simple Python RSS job-feed monitor that searches job postings for keyword matches and stores matching results in a SQLite database.

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

Enable debug logging:

```bash
python run.py --debug
```

Logs are written to `app.log`.

Results are saved to `output.db`

For continuous monitoring, schedule the script to run periodically using Task Scheduler, cron, or a similar scheduler.

## Roadmap

- [x] Add debug command line argument
- [x] Add logging to file
- [x] Add SQLite storage
- [ ] Add dashboard for browsing saved posts
- [ ] Improve reader/feed error handling
- [ ] Add desktop or email notifications
- [ ] Refactor run.py logic into separate modules