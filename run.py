from datetime import datetime
from reader import make_reader, FeedExistsError
import logging
import argparse
import sqlite3
import sys
from dataclasses import dataclass, field

@dataclass
class MatchedPost:
    post: object
    matched_keywords: set[str] = field(default_factory=set)

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS post_keywords (
            link TEXT NOT NULL,
            keyword TEXT NOT NULL,
            PRIMARY KEY (link, keyword),
            FOREIGN KEY (link) REFERENCES posts(link)
        )
    """)


def save_post(cur, matched_post: MatchedPost) -> bool:
    post = matched_post.post

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
        post.id,
    ))

    post_was_inserted = cur.rowcount > 0

    if post_was_inserted:
        cur.executemany("""
            INSERT OR IGNORE INTO post_keywords (
                link,
                keyword
            )
            VALUES (?, ?)
        """, [
            (post.id, keyword)
            for keyword in matched_post.matched_keywords
        ])

    return post_was_inserted


def load_lines(filename: str) -> list[str]:
    items = []

    with open(filename, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                items.append(stripped)

    return items


def collect_posts(reader, keywords: set[str]) -> list[MatchedPost]:
    matches: dict[str, MatchedPost] = {}

    for keyword in keywords:
        logger.debug("Searching keyword: %s", keyword)

        for result in reader.search_entries(keyword, read=False):
            link = result.id

            if link not in matches:
                matches[link] = MatchedPost(post=result)

            matches[link].matched_keywords.add(keyword)

    return list(matches.values())


def add_feeds(reader, rssfeeds: list[str]) -> None:
    for feed in rssfeeds:
        try:
            reader.add_feed(feed)
        except FeedExistsError:
            pass


def save_posts_to_db(matched_posts: list[MatchedPost]) -> list[MatchedPost]:
    con = sqlite3.connect("output.db")

    try:
        cur = con.cursor()
        initialize_db(cur)

        saved_matches = []

        for matched_post in matched_posts:
            if save_post(cur, matched_post):
                saved_matches.append(matched_post)

        con.commit()
        return saved_matches

    finally:
        con.close()


def mark_posts_as_read(reader, postlist: list[object]) -> None:
    for post in postlist:
        reader.mark_entry_as_read(post)


def send_notification(tag: str, message: str) -> None:
    if sys.platform != 'win32':
        return
    from windows_toasts import Toast, WindowsToaster

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
        matched_posts = collect_posts(reader, keywords)

    if not matched_posts:
        logger.info("No new posts found.")
        return
    
    logger.info("%d new posts found.", len(matched_posts))

    saved_posts = save_posts_to_db(matched_posts)
    if saved_posts:
        num_saved_posts = len(saved_posts)
        logger.info("%d new posts saved to database.", num_saved_posts)    
        with make_reader("db.sqlite") as reader:
            mark_posts_as_read(reader, [matched.post for matched in saved_posts])
        send_notification('results', f'Found {num_saved_posts} new jobs.')
    else:
        logger.info("No new posts saved to database.")


if __name__ == "__main__":
    main()