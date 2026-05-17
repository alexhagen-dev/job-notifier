import feedparser
import string
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

        for keyword in keywords_set:
            # go through each result, skipping any already marked as 'read'
            for result in reader.search_entries(keyword, read=False):
                # mark each entry as "read"
                reader.mark_entry_as_read(result)
                # fetch full entry while reader is open
                entry = reader.get_entry(result.resource_id)
                postlist.append(entry)
                    
    # save relevant postings to output.html
    # TODO: have output appended to top of file (possibly using shutil and os?)
    with open("output.html", "a", encoding="utf-8") as myfile:
        for post in postlist:
            myfile.write(f"{post.title}<br>")
            myfile.write(f"{post.feed.title}<br>")
            myfile.write(f"{post.summary}<br>")
            myfile.write(f"{post.link}<hr>")


if __name__ == "__main__":
    main()