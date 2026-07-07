"""Namuwiki (namu.wiki) crawl + parse layer for Wuthering Waves game data.

Fetches Namuwiki article HTML and parses it into normalized dicts that the
content layer stores in PostgreSQL. Parsers are section-heading driven and
defensive: a missing section yields an omitted field, never a crash.
"""
