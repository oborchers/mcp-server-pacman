"""HTML parsers for package repositories."""

from html.parser import HTMLParser


class PyPISimpleParser(HTMLParser):
    """Parser for PyPI's simple HTML index."""

    def __init__(self):
        super().__init__()
        self.packages = []
        self._current_tag = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._current_tag = tag
            for attr in attrs:
                if attr[0] == "href" and attr[1].startswith("/simple/"):
                    # Extract package name from URLs like /simple/package-name/
                    package_name = attr[1].split("/")[2]
                    self.packages.append(package_name)

    def handle_endtag(self, tag):
        if tag == "a":
            self._current_tag = None
