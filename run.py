from datetime import datetime
from reader import make_reader, FeedExistsError
import logging
import argparse
import sqlite3

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


def save_posts_to_db(postlist) -> int:
    con = sqlite3.connect("output.db")

    try:
        cur = con.cursor()
        initialize_db(cur)

        saved_count = 0

        for post in postlist:
            if save_post(cur, post):
                saved_count += 1

        con.commit()
        return saved_count

    finally:
        con.close()


def mark_posts_as_read(reader, postlist) -> None:
    for post in postlist:
        reader.mark_entry_as_read(post)


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

        saved_count = save_posts_to_db(postlist)
        logger.info("%d new posts saved to database.", saved_count)

        mark_posts_as_read(reader, postlist)

if __name__ == "__main__":
    main()