from datetime import datetime
from reader import make_reader, FeedExistsError


def main():    
    # Generate keyword list from source (txt) file
    keywords = []

    for line in open("keywords.txt"):
        stripped = line.strip()
        if stripped:
            keywords.append(stripped)

    # Convert to set to eliminate duplicates
    keywords_set = set(keywords)

    # Get RSS feeds
    rssfeeds = []

    for line in open("rssfeeds.txt"):
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
            # go through each result, skipping any already marked as 'read'
            for result in reader.search_entries(keyword, read=False):
                if result.resource_id not in seen:
                    # mark each entry as "read"
                    reader.mark_entry_as_read(result)
                    seen.add(result.resource_id)
                    postlist.append(result)
                    
    # save relevant postings to output.html
    # TODO: have output appended to top of file (possibly using shutil and os?)
    with open("output.html", "a", encoding="utf-8") as myfile:
        for post in postlist:
            title = post.metadata.get(".title")
            feed_title = post.metadata.get(".feed.title")
            summary = post.content.get(".summary")

            myfile.write("<b>New post added: " + str(datetime.now()) + "</b><br><br>")
            myfile.write(f"{title.value if title else ''}<br>")
            myfile.write(f"{feed_title.value if feed_title else ''}<br>")
            myfile.write(f"{summary.value if summary else ''}<br>")
            myfile.write(f'<a href="{post.id}">View Posting</a><hr>')

if __name__ == "__main__":
    main()