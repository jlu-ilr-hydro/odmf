Markdown - a simple way to format web content
=============================================


In some places, eg. comments [Markdown][1] syntax can be used to 
enhance the appearance of the text. **But you don't need to care!**

The official [Markdown description][2] contains a lot of possibilities, 
here only the most important and the ODMF-extensions to markdown are explained

This help page is written using Markdown

Making captions
----------------

Lines can be turned into captions of different levels (translated to `<hX>` tags), by starting with `#`:

# `# bla` --> `<h1>bla</h1>`
## `## bla2` --> `<h2>bla2</h2>`
### `### bla2` --> `<h3>bla3</h3>`



Creating links
--------------------

The special links to ODMF-objects, like files, datasets, users etc. work of course only in ODMF not in other tools
using Markdown.

 * `file:/template/` links to a file or folder on the server. Use this to link to manuals, thesis etc. ==> file:template 
 * `ds:370` links to a dataset ==> ds:370 
 * `site:18` links to a site ==> site:18
 * `job:1` links to a job ==> job:1
 * `help:import` links to a file /help/import (this one): help:import
 * `photo:1` links to a photo ==> photo:1
 * `![title](/picture/thumbnail/1)`inserts a small version of a photo ==> ![title](/picture/thumbnail/1)
 * `user:philipp` links to a user page ==> user:philipp
 * `[link name](http://uni-giessen.de)` links to another web site. ==> [link name](http://uni-giessen.de)
 * `[title](/map)` links to a location on this site ==> [title](/map)
 * Just write the link address - it will be converted automatically to a link, eg. https://uni-giessen.de


Formatting
---------------

 * Starting a line with \* can be used for a list. Like this one.
 * You can *emphasize* or **strong emphazise** text in this way: `*emphasize*` or `**strong emphazise**`
 * You can insert a line break by doing two line breaks in your text
 * You can insert a horizontal line by `------` on a single line 
 * You can use arrows like this `--> ==> <-- <==` to get this --> ==> <-- <== (ODMF only)
 * You can do some more stuff with Markdown, have a look [here][1] and [here][2] or at the 


 [1]: http://de.wikipedia.org/wiki/Markdown
 [2]: http://daringfireball.net/projects/markdown/syntax
