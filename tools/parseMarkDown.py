'''
Created on 15.05.2013

@author: kraft-p
'''
import markdown
from markdown.extensions import Extension
import re
from markdown.preprocessors import Preprocessor
from genshi.core import Markup
class LinkDs(Preprocessor):
    def run(self,lines):                                                                                                   
        pattern = re.compile('(ds)([0-9]+)')                                                                               
        return [pattern.sub(r'&#x25B9;[\1\2](/dataset/\2/)',line) for line in lines]
class LinkFile(Preprocessor):
    def run(self,lines):
        pattern = re.compile(r'(file:)(\S+)')
        return [pattern.sub(r'&#x25B9;[\2](/datafiles/\2)',line) for line in lines]


# The UrlizePattern class is taken from: https://github.com/r0wb0t/markdown-urlize/blob/master/urlize.py
# Global Vars
URLIZE_RE = '(%s)' % '|'.join([
    r'<(?:f|ht)tps?://[^>]*>',
    r'\b(?:f|ht)tps?://[^)<>\s]+[^.,)<>\s]',
    r'\bwww\.[^)<>\s]+[^.,)<>\s]',
    r'[^(<\s]+\.(?:com|net|org|de)\b',
])

class UrlizePattern(markdown.inlinepatterns.Pattern):
    """ Return a link Element given an autolink (`http://example/com`). """
    def handleMatch(self, m):
        url = m.group(2)
        
        if url.startswith('<'):
            url = url[1:-1]
            
        text = url
        
        if not url.split('://')[0] in ('http','https','ftp'):
            if '@' in url and not '/' in url:
                url = 'mailto:' + url
            else:
                url = 'http://' + url
    
        el = markdown.util.etree.Element("a")
        el.set('href', url)
        el.text = '&#x25B8;' + markdown.util.AtomicString(text)
        return el

           
class MarkDown:
    def __init__(self):
        self.md = markdown.Markdown()
        self.md.preprocessors['link datasets']=LinkDs(self.md)
        self.md.preprocessors['link files']=LinkFile(self.md)
        self.md.inlinePatterns['autolink'] = UrlizePattern(URLIZE_RE, self.md)
    def __call__(self,s):
        if s:
            return Markup(self.md.convert(s))
        else:
            return s