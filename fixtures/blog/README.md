# `fixtures/blog/` — recorded payloads for the blog fetch path

**Engineer 1.** Synthetic, hand-written, and deliberately not recorded from a
real site.

Three reasons they are not real captures:

1. **The suite must not depend on somebody else's site being up.** A test that
   fetches a live feed fails on their maintenance window and passes on ours.
2. **Feeds are not picked yet.** The criteria are drafted and the NFR-5 source
   ruling is outstanding; committing a real feed's payload would pick one by
   accident and make it look reviewed.
3. **Republication.** Published content is quote + attribution + link. A real
   article's full text checked into the repository is the thing that rule
   forbids, in the one place nobody would think to look for it.

Every host is `.invalid` — reserved by RFC 2606, so a bug that tries to fetch
one fails at DNS instead of reaching a stranger's server.

| File | What it exercises |
|---|---|
| `feed_rss.xml` | RSS 2.0, guid + link, one entry with `content:encoded` |
| `feed_atom.xml` | Atom, `id`/`updated`/`published` split, relative entry link |
| `feed_malformed.xml` | unescaped `&` — `bozo` set, entries still parse |
| `feed_no_ids.xml` | entries with neither guid nor link — unidentifiable, dropped and counted |
| `article.html` | an article with a code block and a number-with-units |
| `article_with_comments.html` | an article whose comment section must **not** reach the extracted body |
| `robots_allow.txt` | `User-agent: *` with an unrelated `Disallow` |
| `robots_disallow.txt` | our path disallowed |
| `robots_crawl_delay.txt` | `Crawl-delay: 5`, to check the floor widens |
