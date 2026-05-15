import feedparser
import string


def get_words(text):
    return set(
        text.lower()
        .translate(str.maketrans('', '', string.punctuation))
        .split()
    )


def validate_post(words, keywords_set):
        # TODO: add check to see if post is already in output file
        return bool(words & keywords_set)


def main():    
    # Generate keyword list from source (txt) file
    keywords = open("keywords.txt").readlines()

    # Convert to set to eliminate duplicates
    keywords_set = set(keywords)

    # Get RSS feeds
    rssfeeds = open("rssfeeds.txt").readlines()

    postlist = []

    for feed in rssfeeds:
        posts = feedparser.parse(feed)
        for post in posts.entries:
            # Convert post to string
            poststring = str(post)
           
            # Make list of words in post, normalizing each word by making lowercase and stripping punctuation          
            words = get_words(poststring)
            
            if validate_post(words, keywords_set):
                postlist.append(post)
                    
    with open("output.html", "a", encoding="utf-8") as myfile:        
        for post in postlist:
            myfile.write(str(post['title']) + "<br>")
            myfile.write(str(post['type']) + "<br>")
            myfile.write(str(post['summary']) + "<br>")
            myfile.write(str(post['link']) + "<hr>")


if __name__ == "__main__":
    main()