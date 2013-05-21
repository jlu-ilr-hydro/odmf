'''
Created on 15.05.2013

@author: kraft-p
'''
import markdown
from markdown.extensions import Extension
import re
from markdown.preprocessors import Preprocessor
from genshi.core import Markup

class MarkDownLink(Preprocessor):
    def __init__(self,md,pattern,sub):
        super(MarkDownLink,self).__init__(md)
        self.pattern = re.compile(pattern)
        self.sub = sub
    def run(self,lines):
        return [self.pattern.sub(self.sub,line) for line in lines]

def user2name(s):
    name=' '.join(S.title() for S in s.group(2).split('.'))
    return '[%s](/person/%s)' % (name,s)

class PatternLink(markdown.inlinepatterns.Pattern):
    def __init__(self,md,pattern,href,text):
        super(PatternLink,self).__init__(pattern,md)
        self.href=href
        self.text = text
    def handleMatch(self,m):
        try:
            href = self.href(m)
        except TypeError:
            href =  m.expand(self.href)
        try:
            text = self.text(m)
        except TypeError:
            text =  m.expand(self.text)
        el = markdown.util.etree.Element("a")
        el.set('href', href)
        el.text = u'\u25B8' + markdown.util.AtomicString(text)
        return el

class SymbolPattern(markdown.inlinepatterns.Pattern):
    def __init__(self,md,pattern,out):
        super(SymbolPattern,self).__init__(pattern,md)
        self.out = out
    def handleMatch(self,m):
        return self.out
                 

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

class SchwingbachExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        """ Replace autolink with UrlizePattern """
        user2name = lambda s:' '.join(S.title() for S in s.group(3).split('.'))
        md.inlinePatterns['link datasets'] = PatternLink(md,'(ds)([0-9]+)',r'/dataset/\3/',r'\2\3')
        md.inlinePatterns['link files']=PatternLink(md,r'(file:)(\S+)',r'/datafiles/\3',r'\3')
        md.inlinePatterns['link sites']=PatternLink(md,'(#)([0-9]+)',r'/site/\3',r'\2\3')
        md.inlinePatterns['link job']=PatternLink(md,'(job:)([0-9]+)',r'/job/\3',r'\2\3')
        md.inlinePatterns['link dir']=PatternLink(md,'(dir:)(\S+)',r'/download?dir=\3',r'\3')
        md.inlinePatterns['link user']=PatternLink(md,r'(user:)([a-zA-Z\.]+)',r'/user/\3',user2name)
        md.inlinePatterns['link photo']=PatternLink(md,'(photo:)([0-9]+)',r'/picture/?id=\3',r'\2\3')
        md.inlinePatterns['replace rarrow']=SymbolPattern(md,r'(-->)',u'\u2192')
        md.inlinePatterns['replace larrow']=SymbolPattern(md,r'(<--)',u'\u2190')
        md.inlinePatterns['replace rarrow big']=SymbolPattern(md,r'(==>)',u'\u21D2')
        md.inlinePatterns['replace larrow big']=SymbolPattern(md,r'(<==)',u'\u21D0')
class UrlizeExtension(markdown.Extension):
    """ Urlize Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Replace autolink with UrlizePattern """
        md.inlinePatterns['autolink'] = UrlizePattern(URLIZE_RE, md)

           
class MarkDown:
    def __init__(self):
        se = SchwingbachExtension(configs={})
        al = UrlizeExtension(configs={})
        self.md = markdown.Markdown(extensions=['admonition',se,al])

    def __call__(self,s):
        if s:
            return Markup(self.md.convert(s))
        else:
            return s