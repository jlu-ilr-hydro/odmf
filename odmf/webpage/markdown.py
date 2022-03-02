'''
Contains the odmf flavor of markdown

Created on 15.05.2013
@author: kraft-p
'''
import markdown
from markdown.inlinepatterns import Pattern
from xml.etree import ElementTree as etree
import bleach
import typing
import re



class PatternLink(Pattern):
    """
    Creates a link from a specific Regular Expression pattern
    """

    def __init__(self, md, pattern: str, href: typing.Union[str, typing.Callable], text: typing.Union[str, typing.Callable]):
        """
        Creates the rule to substitute a pattern with a link
        md: The MarkDown object
        pattern: a regular expression of the text to be used as the pattern
        href: a substitution string to yield the linked url from the pattern. Note: Groups have one index higher as one would expect. Eg. the first group in \2
        text: a substitution string to yield the link label from the pattern. Note: Groups have one index higher as one would expect. Eg. the first group in \2
        """
        from ..config import conf
        super(PatternLink, self).__init__(pattern, md)
        if href.startswith('/') and not href.startswith(conf.root_url):
            self.href = conf.root_url + href
        else:
            self.href = href
        self.text = text

    def handleMatch(self, m):
        try:
            href = self.href(m)
        except TypeError:
            href = m.expand(self.href)
        try:
            text = self.text(m)
        except TypeError:
            text = m.expand(self.text)
        el = etree.Element("a")
        el.set('href', href)
        el.text = markdown.util.AtomicString(text)
        return el


class VideoPattern(Pattern):
    def __init__(self, md, pattern):
        super(VideoPattern, self).__init__(pattern, md)

    def parseOption(self, o):
        return str(o).replace("[", "").replace("]", "")

    def handleMatch(self, m):
        """
        Simply extraxt regex groups and push information to the video element, which is nested in a div-wrapper.
        A width and height can be set, but is not supported from javascript, yet. Maybe never will be, because
        we need a correct working canvas with teh exact dimension of the video.
        :param m:
        :return:
        """
        el = markdown.util.etree.Element("video")
        el.set('src', m.group(3))
        el.set('controls', "controls")
        el.set('type', "video/mp4")

        return el


class VideoAlphaPattern(Pattern):
    """
    This Creates a HTML-5-Element with an extra wrapper div, to handle alpha-formated Video.
    Later a javscript function will convert this alpha videos in videos with transparent background
    and therefor needs a speciall html / class structure
    """
    def __init__(self, md, pattern):
        super(VideoAlphaPattern, self).__init__(pattern, md)

    def parseOption(self,o):
        return str(o).replace("[","").replace("]","")

    def handleMatch(self, m):
        """
        Simply extraxt regex groups and push information to the video element, which is nested in a div-wrapper.
        A width and height can be set, but is not supported from javascript, yet. Maybe never will be, because
        we need a correct working canvas with teh exact dimension of the video.
        :param m:
        :return:
        """
        el = markdown.util.etree.Element("video")
        el.set('src', m.group(3))
        el.set('controls',"")
        el.set('type', "video/mp4")
        el.set('class', "html5AlphaVideo_video")

        par_el = markdown.util.etree.Element("div")
        par_el.set("class", "html5AlphaVideo_wrapperDiv")
        par_el.append(el)
        return par_el


class SymbolPattern(Pattern):
    def __init__(self, md, pattern, out):
        super(SymbolPattern, self).__init__(pattern, md)
        self.out = out

    def handleMatch(self, m):
        return self.out

class FontAwesomePattern(Pattern):
    def __init__(self, md):
        super().__init__(r'!(fa\-\S+)', md)

    def handleMatch(self, m: re.Match[str]):
        icon = m.expand(r'\2')

        el = etree.Element("i")
        el.set('class', 'fas ' + icon)
        return el



# The UrlizePattern class is taken from: https://github.com/r0wb0t/markdown-urlize/blob/master/urlize.py
# Global Vars
URLIZE_RE = '(%s)' % '|'.join([
    r'<(?:f|ht)tps?://[^>]*>',
    r'\b(?:f|ht)tps?://[^)<>\s]+[^.,)<>\s]',
    r'\bwww\.[^)<>\s]+[^.,)<>\s]',
    r'[^(<\s]+\.(?:com|net|org|de)\b',
])


class UrlizePattern(Pattern):
    """ Return a link Element given an autolink (`http://example/com`). """

    def handleMatch(self, m):
        url = m.group(2)

        if url.startswith('<'):
            url = url[1:-1]

        text = url
        if text.find("video") == -1:
            if not url.split('://')[0] in ('http', 'https', 'ftp'):
                if '@' in url and '/' not in url:
                    url = 'mailto:' + url
                else:
                    url = 'https://' + url

            el = markdown.util.etree.Element("a")
            el.set('href', url)
            el.text = markdown.util.AtomicString(text)
            return el
        else:
            return None


class ODMFExtension(markdown.Extension):
    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """ Replace autolink with UrlizePattern """
        from ..config import conf
        def user2name(s):
            return ' '.join(S.title() for S in s.group(3).split('.'))
        url = conf.root_url
        if url.endswith('/'):
            url = url[:-1]
        md.inlinePatterns.register(PatternLink(md, r'(ds)([0-9]+)', url + r'/dataset/\3/', '\u25B8' + r'\2\3'), 'link datasets', 100)
        md.inlinePatterns.register(PatternLink(md, r'(file:)(\S+)', url + r'/download/\3', '\u25B8' + r'\3'), 'link files', 100)
        md.inlinePatterns.register(PatternLink(md, r'(#)([0-9]+)', url + r'/site/\3', '\u25B8' + r'\2\3'), 'link sites', 1000)
        md.inlinePatterns.register(PatternLink(md, r'(job:)([0-9]+)', url + r'/job/\3', '\u25B8' + r'\2\3'), 'link job', 100)
        md.inlinePatterns.register(PatternLink(md, r'(dir:)(\S+)', url + r'/download/\3', '\u25B8' + r'\3'), 'link dir', 100)
        md.inlinePatterns.register(PatternLink(md, r'(user:)([a-zA-Z\.]+)', url + r'/user/\3', user2name), 'link user', 100)
        md.inlinePatterns.register(PatternLink(md, r'(photo:)([0-9]+)', url + r'/picture/?id=\3', '\u25B8' + r'\2\3'), 'link photo', 100)
        md.inlinePatterns.register(PatternLink(md, r'(log:)([0-9]+)', url + r'/log/\3', '\u25B8' + r'\2\3'), 'link log', 100)
        md.inlinePatterns.register(PatternLink(md, r'(wiki:)([\w/]+)', url + r'/download/\3', '[\\3]'), 'link wiki', 100)

        md.inlinePatterns.register(SymbolPattern(md, r'(-->)', '\u2192'), 'replace rarrow', 100)
        md.inlinePatterns.register(SymbolPattern(md, r'(<--)', '\u2190'), 'replace larrow', 100)
        md.inlinePatterns.register(SymbolPattern(md, r'(==>)', '\u21D2'), 'replace rarrow big', 100)
        md.inlinePatterns.register(SymbolPattern(md, r'(<==)', '\u21D0'), 'replace larrow big', 100)
        md.inlinePatterns.register(VideoAlphaPattern(md, r'(alpha-video:)([\w\.\:\-\/]*)(\[\d+\])?(\[\d+\])?'), 'alphavideo', 100)
        md.inlinePatterns.register(VideoPattern(md, r'(video:)([\w\.\:\-\/]*)'), 'video', 100)
        md.inlinePatterns.register(FontAwesomePattern(md), 'fa-icon', 100)


class UrlizeExtension(markdown.Extension):
    """ Urlize Extension for Python-Markdown. """

    def extendMarkdown(self, md: markdown.Markdown):
        """ Replace autolink with UrlizePattern """
        md.inlinePatterns.register(UrlizePattern(URLIZE_RE, md), 'autolink', 100)


class bleach_allow:

    tags = bleach.ALLOWED_TAGS + [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'a', 'pre', 'div', 'hr', 'br',
        'sub', 'sup',
        'video', 'img', 'code',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'tfoot'
    ]
    attributes = {
        '*': ['class', 'title'],
        'video': ['controls', 'src', 'type'],
        'img': ['alt', 'src'],
        'a': ['href', 'alt']
    }

    styles = ['admonition', 'warning']


class MarkDown:
    def __init__(self):
        se = ODMFExtension()
        al = UrlizeExtension()

        self.md = markdown.Markdown(extensions=['admonition', 'extra', se, al])

    def __call__(self, s, *, with_newline_literal=False) -> str:
        if s:
            if type(s) is str:
                pass
            elif not type(s) is str:
                s = str(s, errors='replace')

            html = self.md.convert(s)

            cleaned_html = bleach.clean(
                html,
                tags=bleach_allow.tags,
                attributes=bleach_allow.attributes,
                styles=bleach_allow.styles
            )
            if with_newline_literal:
                cleaned_html = cleaned_html.replace('\n', r'\n')
            return cleaned_html
        else:
            return s
