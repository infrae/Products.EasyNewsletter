
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

        for attr in attrs:
            if attr[0] == "href":
                try:
                    # split anchor from url
                    baseurl, anchor = urlparse.urldefrag(attr[1])
                    o = self.context.restrictedTraverse(urllib.unquote(baseurl))
                    if getattr(o, 'absolute_url', None):
                        url = o.absolute_url()
                    else:
                        # maybe we got a view instead of an traversal object:
                        if getattr(o, 'context', None):
                            url = o.context.absolute_url()
                        else:
                            url = attr[1]
                    if anchor:
                        url = '#' + anchor
                except:
                    url = attr[1]
                if isinstance(url, unicode):
                    plone_utils = getToolByName(self.context, 'plone_utils')
                    encoding = plone_utils.getSiteEncoding()
                    url = url.encode(encoding)
                self._write_to_html(' href="%s"' % url)
            else:
                self._write_to_html(' %s="%s"' % (attr))

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
        for attr in attrs:
            if attr[0] == "src":
                image_url = urlparse.urlparse(attr[1])
                if 'http' in attr[1]:
                    url = attr[1]
                    self._write_to_html(' src="%s"' % url)
                else:
                    self._write_to_html(' src="cid:image_%s"' % self.image_number)
                    self.image_number += 1
                    self.image_urls.append(attr[1])
            else:
                self._write_to_html(' %s="%s"' % (attr))

        self._write_to_html(" />")
