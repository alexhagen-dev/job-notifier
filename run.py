from datetime import datetime
from reader import make_reader, FeedExistsError
import logging
import argparse
import sqlite3
from windows_toasts import Toast, WindowsToaster

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", help="Show debug messages when running")
args = parser.parse_args()

# Set global logging level
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s:[%(levelname)s]:%(name)s: %(message)s",
    filename="app.log"
)

logger = logging.getLogger(__name__)

# Set logging level for this program (leaving the levels of the imports alone)
if args.debug:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


def initialize_db(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            datetime TEXT,
            title TEXT,
            feedtitle TEXT,
            summary TEXT,
            link TEXT PRIMARY KEY
        )
    """)


def save_post(cur, post) -> bool:
    title = post.metadata.get(".title")
    feed_title = post.metadata.get(".feed.title")
    summary = post.content.get(".summary")

    cur.execute("""
        INSERT OR IGNORE INTO posts
        VALUES (?, ?, ?, ?, ?)
    """, (
        str(datetime.now()),
        title.value if title else "",
        feed_title.value if feed_title else "",
        summary.value if summary else "",
        post.id
    ))

    return cur.rowcount > 0


def load_lines(filename: str) -> list[str]:
    items = []

    with open(filename, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                items.append(stripped)

    return items


def collect_posts(reader, keywords: set[str]) -> list:
    postlist = []
    seen = set()

    for keyword in keywords:
        logger.debug("Searching keyword: %s", keyword)
        for result in reader.search_entries(keyword, read=False):
            if result.resource_id not in seen:
                seen.add(result.resource_id)
                postlist.append(result)

    return postlist


def add_feeds(reader, rssfeeds: list[str]) -> None:
    for feed in rssfeeds:
        try:
            reader.add_feed(feed)
        except FeedExistsError:
            pass


def save_posts_to_db(postlist) -> list:
    con = sqlite3.connect("output.db")

    try:
        cur = con.cursor()
        initialize_db(cur)

        saved_posts = []

        for post in postlist:
            if save_post(cur, post):
                saved_posts.append(post)

        con.commit()
        return saved_posts

    finally:
        con.close()


def mark_posts_as_read(reader, postlist) -> None:
    for post in postlist:
        reader.mark_entry_as_read(post)


def send_notification(tag: str, message: str) -> None:
    toaster = WindowsToaster('Job Notifier')
    toast = Toast()
    toast.tag = 'job-notifier-' + tag
    toast.text_fields = [message]
    toaster.show_toast(toast)


def main():    
    logger.info("Running job notifier script...")
    
    keywords = set(load_lines("keywords.txt"))
    rssfeeds = load_lines("rssfeeds.txt")

    with make_reader("db.sqlite") as reader:
        add_feeds(reader, rssfeeds)
        reader.update_feeds()
        reader.update_search()
        postlist = collect_posts(reader, keywords)

    if not postlist:
        logger.info("No new posts found.")
        return
    
    logger.info("%d new posts found.", len(postlist))

    saved_posts = save_posts_to_db(postlist)
    if saved_posts:
        num_saved_posts = len(saved_posts)
        logger.info("%d new posts saved to database.", num_saved_posts)    
        with make_reader("db.sqlite") as reader:
            mark_posts_as_read(reader, saved_posts)
        send_notification('results', f'Found {num_saved_posts} new jobs.')
    else:
        logger.info("No new posts saved to database.")


if __name__ == "__main__":
    main()