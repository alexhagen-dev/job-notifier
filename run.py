from datetime import datetime
from reader import make_reader, FeedExistsError
import shutil
import os
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


# TODO: refactor into separate functions 
def main():    
    logger.info("Running job notifier script...")
    
    # Generate keyword list from source (txt) file
    keywords = []

    with open("keywords.txt", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if stripped:
                keywords.append(stripped)

    # Convert to set to eliminate duplicates
    keywords_set = set(keywords)

    # Get RSS feeds
    rssfeeds = []

    with open("rssfeeds.txt", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if stripped:
                rssfeeds.append(stripped)

    postlist = []

    # initialize/use the reader
    with make_reader('db.sqlite') as reader:
        # cycle through feeds and add them to the reader
        for feed in rssfeeds:
            try:
                reader.add_feed(feed)
            except FeedExistsError:
                pass
        
        # update the feeds
        reader.update_feeds()
        
        # update search index
        reader.update_search()

        seen = set()

        for keyword in keywords_set:
            logger.debug("Searching keyword: %s", keyword)
            # go through each result, skipping any already marked as 'read'
            for result in reader.search_entries(keyword, read=False):
                logger.debug("Keyword match found: %s", keyword)
                if result.resource_id not in seen:
                    # mark each entry as "read"
                    reader.mark_entry_as_read(result)
                    seen.add(result.resource_id)
                    postlist.append(result)
                    
    con = sqlite3.connect("output.db")

    try:
        cur = con.cursor()
        initialize_db(cur)

        saved_count = 0

        for post in postlist:
            if save_post(cur, post):
                saved_count += 1

        con.commit()
    finally:
        con.close()
    
    logger.info("%d new posts saved to database.", saved_count)

    # save relevant postings to output.html, "prepending" new posts to the 
    # top of the file
    original_file = 'output.html'
    temp_file = 'data.txt.tmp'

    if not postlist:
        logger.info("No new posts found.")
        return

    logger.info("%d new posts found.", len(postlist))

    with open(temp_file, 'w', encoding='utf-8') as f_temp:
        for post in postlist:
            title = post.metadata.get(".title")
            feed_title = post.metadata.get(".feed.title")
            summary = post.content.get(".summary")

            f_temp.write("<b>New post added: " + str(datetime.now()) + "</b><br><br>")
            f_temp.write(f"{title.value if title else ''}<br>")
            f_temp.write(f"{feed_title.value if feed_title else ''}<br>")
            f_temp.write(f"{summary.value if summary else ''}<br>")
            f_temp.write(f'<br><a href="{post.id}">View Posting</a><hr>')
        
        if os.path.exists(original_file):
            with open(original_file, 'r', encoding='utf-8') as f_orig:
                shutil.copyfileobj(f_orig, f_temp)

    os.replace(temp_file, original_file)


if __name__ == "__main__":
    main()