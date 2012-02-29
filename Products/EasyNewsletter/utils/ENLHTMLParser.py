
import HTMLParser
import urlparse
import urllib
import htmllib
import cStringIO
import formatter

from Products.CMFCore.utils import getToolByName


class ENLHTMLParser(HTMLParser.HTMLParser):
    """A simple parser which exchange relative URLs with absolute ones"""
    TEXT_MAX_COLS = 72

    def __init__(self, context):
        self.context = context
        self._html = ""
        self._body = ""
        self._is_body = False
        self.image_urls = []
        self.image_number = 0
        plone_utils = getToolByName(self.context, 'plone_utils')
        self._encoding = plone_utils.getSiteEncoding()
        self._base_parts = urlparse.urlparse(context.absolute_url())

        HTMLParser.HTMLParser.__init__(self)

    def _write_to_html(self, data):
        self._html += data
        if self._is_body:
            self._body += data

    def get_html(self):
        return self._html

    def get_text(self):
        text = cStringIO.StringIO()
        parser = htmllib.HTMLParser(
            formatter.AbstractFormatter(
                formatter.DumbWriter(
                    text, self.TEXT_MAX_COLS)))
        parser.feed(self._body)
        parser.close()

        # append the anchorlist at the bottom of a message
        # to keep the message readable.
        anchors = "\n\n" + ("-" * self.TEXT_MAX_COLS) + "\n\n"
        for index, item in enumerate(parser.anchorlist):
            anchors += "[%d] %s\n" % (index, item)

        return text.getvalue() + anchors

    def handle_starttag(self, tag, attrs):
        """
        """
        if tag == 'body':
            self._is_body = True
        self._write_to_html("<%s" % tag)

        for key, value in attrs:
            if key == "href":
                if isinstance(value, unicode):
                    value = value.encode(self._encoding)
                if value[0] != '#':
                    # If we have something else than an anchor make it absolute
                    parts = urlparse.urlparse(value)
                    if parts[0] in ['', 'http', 'https']:
                        absolute_parts = [parts[0] or self._base_parts[0],
                                          parts[1] or self._base_parts[1]]
                        if len(parts[2]) and parts[2][0] != '/':
                            absolute_parts.append(
                                '/'.join((self._base_parts[2], parts[2])))
                        else:
                            absolute_parts.append(parts[2])
                        absolute_parts.extend(parts[3:])
                        value = urlparse.urlunparse(absolute_parts)
            self._write_to_html(' %s="%s"' % (key, value))

        self._write_to_html(">")

    def handle_endtag(self, tag):
        """
        """
        self._write_to_html("</%s>" % tag)
        if tag == 'body':
            self._is_body = False

    def handle_data(self, data):
        """
        """
        self._write_to_html(data)

    def handle_charref(self, name):
        self._write_to_html("&#%s;" % name)

    def handle_entityref(self, name):
        self._write_to_html("&%s;" % name)

    def handle_comment(self, data):
        self._write_to_html("<!--%s-->" % data)

    def handle_decl(self, decl):
        self._write_to_html("<!%s>" % decl)

    def handle_startendtag(self, tag, attrs):
        """
        """
        self._write_to_html("<%s" % tag)

        for key, value in attrs:
            if key == "src":
                if 'http' in value:
                    self._write_to_html(' src="%s"' % value)
                else:
                    self._write_to_html(' src="cid:image_%s"' % self.image_number)
                    self.image_number += 1
                    self.image_urls.append(value)
            else:
                self._write_to_html(' %s="%s"' % (key, value))

        self._write_to_html(" />")
