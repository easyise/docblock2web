docblock2web
===

Generate Markdown from your phpDoc/JSDoc inline documentation in simpliest possible way.

Make your code documentation more friendly by publishing it on the web (e.g. on [http://github.io]()).

This tool extracts inline documentation blocks made according to [phpDocumentor](https://www.phpdoc.org) or [JSDoc](http://usejsdoc.org) specifications from your source code file and creates [Markdown](https://daringfireball.net/projects/markdown/syntax) that could be used with [Jekyll](https://jekyllrb.com), WordPress, WiKi, etc.

Usage example:
```
from docblock2web import docblock2web

filePath = 'sample.php' 

dbw = docblock2web( open(filePath) )

print( dbw.md() )
```

Requires Python version 3.

