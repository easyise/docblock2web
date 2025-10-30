import re
import os, io
from pathlib import Path

class DocBlock2Web:

    dockblocks = []
    fileHierarchy = []
    categories = {}
    sourceFile = ''
    sourceFileName = ''

    rootTypes = ['file_header', 'class', 'js_function', 'jquery_plugin']

    options = {'asset_order': ['properties', 'methods', 'events'],\
        'scope_order': ['public', 'static', 'protected', 'private'], \
        'tag_order': ['description', 'param', 'uses', 'return', 'example', 'see', 'category'], 
        'header_level': 2, \
        'display': 'hierarchial', \
        'escapeDollar': False, \
        'tags': { \
            #'api': 'API', \ #not supported yet
            'author': 'Author', \
            'category': 'Category', \
            'copyright': 'Copyright', \
            'deprecated': 'Deprecated', \
            'example': 'Example', \
            #'filesource': '', \ 
            #'internal': '', \
            'license': 'License', \
            'link': 'Link', \
            'method': 'Method', \
            'package': 'Package', \
            'param': 'Parameters', \
            'property': 'Property', \
            'property-read': 'Property (read)', \
            'property-write': 'Property (write)', \
            'return': 'Returns', \
            'see': 'See also', \
            'since': 'Since', \
            'source': 'Source', \
            'subpackage': 'Subpackage', \
            'throws': 'Throws', \
            'todo': 'To Do', \
            'uses': 'Uses', \
            'used-by': 'Used By', \
            'var': 'Variable', \
            'version': 'Version' \
        }, \
        'translations': { \
            'class': 'class', \
            'js_function': 'JavaScript object',\
            'jquery_plugin': 'jQuery plugin',\
            'categories': 'By category',\
        }}

    def __init__(self, sourceFile, sourceFileName='', options={}):
        
        self.sourceFile = sourceFile
        self.sourceFileName = sourceFileName if sourceFileName else \
            sourceFile.name if isinstance(sourceFile, io.TextIOWrapper) else None

        lines = sourceFile.readlines()
        self.dockblocks = []
        self.categories = {}
        self.options = DocBlock2Web.options.copy()
        self.options.update(options)

        # getting docblock coordinates
        lineNo = 0
        for line in lines:
            mStart = DocBlock.reStart.search(line)
            mEnd = DocBlock.reEnd.search(line)
            
            if mStart:
                #print("DocBlock starts at line {}:{}".format(lineNo+1, mStart.end()))
                db = {'begin': [lineNo,mStart.end()]}
            if mEnd:
                #print("db ends at line {}:{}".format(lineNo+1, mEnd.start()))
                db['end']  = [lineNo, mEnd.start()]
                db['subject'] = ''
                db['contents'] = ''
                for i in range(db['begin'][0], db['end'][0]):
                    dbLine = lines[i]
                    lineProcessed = re.sub(DocBlock.reEnd, '', \
                                                    re.sub(DocBlock.reStart, '',\
                                                           dbLine)
                                                    )
                    db['contents'] +=  re.sub(DocBlock.reLineStart, '', lineProcessed )
                db['contents'] = db['contents'].strip()
                if db['contents'] !='' and not re.search("\@ignore", db['contents']):
                    db['subject'] = lines[lineNo+1].strip()
                    if db['subject'] != '' or len(self.dockblocks)==0:
                        o_db = DocBlock( **db, 
                                        lines=lines,
                                        sourceFile=sourceFile, 
                                        sourceFileName=self.sourceFileName )
                        self.dockblocks.append( o_db )
                
            lineNo += 1

        for i, db in enumerate(self.dockblocks):
            if i==0 and not db.type:
                db.type='file_header'
                continue
            if db.type=='class':
                db.collectClassAssets(i, self.dockblocks)
                continue
        
        for i, db in enumerate(self.dockblocks):
            if 'category' in db.tokens and hasattr(db, 'name'):
                for cat in db.tokens['category']:
                    cat = cat.strip()
                    if cat not in self.categories:
                        self.categories[cat] = []
                    self.categories[cat].append(db)

        for cat, dbs in self.categories.items():
            dbs = dbs.sort(key=lambda db: ((db.parent.name if hasattr(db, 'parent') and hasattr(db.parent, 'name') else '')+db.name).lower())

    def merge_categories(categories, categories1):
        """ Recursively merge categories dictionary and sort list by class name + function name. The ``merge_dct`` is merged into ``dct``.
            :param categories: dict onto which the merge is executed
            :param categories1: dct merged into dct
            :return: categories
            """

        if not categories1:
            return categories

        for cat, dbs in categories1.items():
            if not cat in categories:
                categories[cat] = dbs
            else:
                categories[cat] += dbs

        for cat, dbs in categories.items():
            dbs = dbs.sort(key=lambda db: ((db.parent.name if hasattr(db, 'parent') else '')+db.name).lower())

        return categories


    # returns Markdown
    def md(self):

        md = ''
        for i, db in enumerate(self.dockblocks):
            
            if self.options['display']=='hierarchial' and db.type not in DocBlock2Web.rootTypes:
                continue

            md += db.md(self.options)
                
            md += "\n\n\n"

        return md
    
    #returns TOC markdown, hiearchially
    def toc(self, output='yaml'):

        md = ''

        options = self.options.copy()
        options['output'] = output
            
        for i, db in enumerate(self.dockblocks):
            
            if db.type not in DocBlock2Web.rootTypes or db.type=='file_header':
                continue

            md += db.toc(options)
                
            md += "\n\n"

        return md

    # returns categories markdown
    def cats(self, categories = None, output = None):

        categories = self.categories if categories is None else categories
        output = 'yaml' if output is None else output

        str_ = ''

        formatters = {'yaml':[ (' '*4)+'- title: \"{}\"\n'+(' '*6)+'folders:\n\n',\
                (' '*6)+'- title: \"{}\"\n'+(' '*8)+'url: \"{}\"\n'+(' '*8)+'folders:\n\n'\
            ],\
            'md': ['{}\n',\
                '* [{}]({})\n'\
            ]\
        }

        formatter = formatters[output]

        if len(categories.keys())==0:
            
            for i, db in enumerate(self.dockblocks):
                
                if db.type not in DocBlock2Web.rootTypes or db.type=='file_header':
                    continue

                categories = DocBlock2Web.merge_categories( categories, db.assets['categories'] )

        cats = list(categories.keys())

        cats.sort(key=lambda cat: cat.lower())

        flagMultipleClasses = False
        parentName = ''
        for i, cat in enumerate(cats):
            for j, db in enumerate(categories[cat]):
                if parentName!='' and parentName!=db.parent.name:
                    flagMultipleClasses = True
                    break
                parentName = db.parent.name
            if flagMultipleClasses:
                break

        for i, cat in enumerate(cats):
            str_ += formatter[0].format(cat)
            for j, db in enumerate(categories[cat]):
                str_ += formatter[1].format( db.brief_name({'showParent': flagMultipleClasses}), '#'+db.anchor() )

        return str_






class DocBlock:

    lineNoStart = None
    lineNoEnd = None

    rawSubject = ''
    rawContents = ''

    assets = {}

    reStart = re.compile(r'^\s*/\*\*')
    reEnd = re.compile(r'\*/')
    reLineStart = re.compile(r'^\s*\* {0,1}')

    reParam = re.compile(r'^\s*(?P<type>[\w]+)\s+(?P<name>[\$\w]+)')

    reDollar = re.compile(r'(\$)([\w]+)')

    def __init__(self, begin, end, subject, contents, lines, **kwargs):

        self.lineNoStart = begin
        self.lineNoEnd = end
        self.lines = lines

        self.rawSubject = subject
        self.rawContents = contents

        self.sourceFile = kwargs.get('sourceFile', None)  
        self.sourceFileName = kwargs.get('sourceFileName', '')

        self.subject = ''
        self.type = None
        self.subtype = None
        self.scope = None

        self.language = 'PHP'

        self.parent = None

        self.tokens = {}
        self.tokenSequence = []
        self.assets = {}

        def _finishToken(activeToken, activeTokenContent):
            if activeToken not in self.tokens or not self.tokens[activeToken]:
                self.tokens[activeToken] = []
            self.tokens[activeToken].append(activeTokenContent)
            self.tokenSequence.append(activeToken)

        aContents = self.rawContents.split("\n")
        reToken = "^\@([a-z]+)"
        retVal = {'subject': subject, 'contnent': contents}
        
        activeToken = 'description'
        activeTokenContent = ''
        
        for i, curString in enumerate(aContents):
            if re.search(reToken, curString, re.IGNORECASE):
                # finish previous active token and start next
                if activeToken:
                    _finishToken(activeToken, activeTokenContent)
                activeToken = re.match(reToken, curString).group(1)
                activeTokenContent = ''
                curString = curString.strip().replace('@'+activeToken, '').strip()
            activeTokenContent += ["\n", ''][activeTokenContent=='']+curString
        _finishToken(activeToken, activeTokenContent)

        self._updateSubject();

    def _updateSubject(self):

        mClass = re.search(r'class\s+(\w+)', self.rawSubject, re.IGNORECASE)
        if mClass:
            self.type = 'class'
            self.subject = mClass.group(1)
            self.name = mClass.group(1)
            return

        mFunction = re.search(r'function\s((\w+)\s*\()', self.rawSubject, re.IGNORECASE)
        if mFunction:
            self.type = 'function'
            self.name = mFunction.group(2)
            self.subject, params = __class__._parseFunctionSignature(self.lineNoEnd[0], self.lines)
            if ('param' not in self.tokens or not self.tokens['param']) and params:
                self.tokens['param'] = params
            return

        mVariable = re.search(r'(\$[\w]+)\s*=\s*', self.rawSubject, re.IGNORECASE)
        if mVariable:
            self.type = 'property'
            self.subject = mVariable.group(1)
            self.name = self.reDollar.sub(r'\2', mVariable.group(1))
            return

    def updateScope(self):
        if 'event' in self.tokens:
            self.scope = 'event'
            return
        self.scope = 'static' if re.search('static', self.rawSubject, re.IGNORECASE) \
            else ('protected' if re.search('protected', self.rawSubject, re.IGNORECASE) \
                else ('private' if re.search('private', self.rawSubject, re.IGNORECASE) \
                    else 'public'))

    def collectClassAssets(self, selfIndex, alldockblocks):

        self.assets['properties'] = {'public': [], 'static': [], 'private': [], 'protected': []}
        self.assets['methods'] = {'public': [], 'static': [], 'private': [], 'protected': []}
        self.assets['events'] = []
        self.assets['categories'] = {}

        for i in range(selfIndex+1, len(alldockblocks)):
            db = alldockblocks[i]
            
            if db.type in DocBlock2Web.rootTypes:
                break;

            db.updateScope();

            if 'category' in db.tokenSequence and hasattr( db, 'name' ):
                for cat in db.tokens['category']:
                    cat = cat.strip()
                    if cat not in self.assets['categories']:
                        self.assets['categories'][cat] = []
                    self.assets['categories'][cat].append(db)

            if db.type=='function':
                if db.scope=='event':
                    self.assets['events'].append(db)    
                elif db.scope in self.assets['methods']:
                    self.assets['methods'][db.scope].append(db)
                else:
                    continue

            if db.type=='property' and db.scope in self.assets['properties']:
                self.assets['properties'][db.scope].append(db)

            db.parent = self


        for cat, dbs in self.assets['categories'].items():
            #for db in dbs: print(db.subject+':'+(db.name if hasattr(db, 'name') else '-subj-'+db.rawSubject))
            dbs.sort(key=lambda db: db.name)


    def anchor(self):
        
        return (self.parent.name.lower()+'-' if self.parent else '') + self.name.lower()


    def brief_name(self, options={}):
        
        return  (self.parent.name+('::' if self.language=='PHP' else '.') if self.parent and 'showParent' in options and options['showParent'] else '')+\
                ('$' if self.language=='PHP' and self.type=='property' else '')+\
                self.name+\
                ('()' if self.type=='function' else '')

    
    def href(self, options={}):

        return "["+self.brief_name(options)+"](#%s)\n" % self.anchor()

    
    def md(self, options={}):

        def lst2str(lst):
            return '\n'.join( [ str(item).strip() for item in lst ] )

        strMD = ''
        header = ''

        if(self.type!='file_header'):
            header = ('#' * (options['header_level']+(1 if self.scope else 0)) + ' ') \
                + ('<a name="%s"></a>' % self.anchor() if self.name else '') \
                + (self.scope+' ' if self.scope else '') \
                + self.type +' __'+self.subject+'__'
            header += "\n\n"

        strMD = header

        strMD += lst2str(self.tokens['description'])+"\n\n"

        if self.type=='property':
            contents = __class__._parseArray(self.lineNoEnd[0], self.lines)
            strMD += '```'+self.language.lower()+'\n'+contents+'\n```\n\n' if contents else ''

        if self.type=='function':
            if 'param' in self.tokens and self.tokens['param']:
                strMD += '__'+options['tags']['param']+'__'+": \n\n"
                for param in self.tokens['param']:
                    strMD += '* '
                    strMD += "\t"
                    m = self.reParam.search(param)
                    if m:
                        param = '__%s__ (%s)' % (m.group('name'), m.group('type'))+ ' - '+self.reParam.sub('', param).strip('- ')

                    strMD += param.rstrip() + "\n"

                strMD += "\n"

            if 'return' in self.tokens:
                strMD += '__'+options['tags']['return']+'__'+": "+lst2str(self.tokens['return'])+"\n\n"

        ts = set(self.tokenSequence)
        tags = ''
        for tag in sorted(ts, key=lambda x: DocBlock2Web.options['tag_order'].index(x) if x in DocBlock2Web.options['tag_order'] else len(DocBlock2Web.options['tag_order'])):
            if tag not in ['param', 'return', 'example', 'description']:
                if tag in options['tags'] and tag in self.tokens:
                    tags += '__'+options['tags'][tag]+'__'+": "+lst2str(self.tokens[tag])+"  \n"
                else:
                    raise DocBlock2WebException("Tag '%s' is not supported %s" % (tag, 
                                                                                  "(file: %s:%d)" % (self.sourceFileName,
                                                                                                     self.lineNoStart[0]) if self.sourceFileName else '') )
                
        tags += '\n' if len(tags)>0 else ''

        strMD += tags

        if options['display']=='hierarchial' and self.type in DocBlock2Web.rootTypes and self.type!='file_header':
            for asset_type in options['asset_order']:
                for scope in options['scope_order']:
                    assets = self.assets[asset_type] if (type(self.assets[asset_type]) is list) \
                        else (self.assets[asset_type][scope] if type(self.assets[asset_type][scope]) is list \
                            else [])
                    for dbAsset in assets:
                        strMD += dbAsset.md(options)+"\n\n"

        return self.reDollar.sub(r'\\\1\2', strMD) if options['escapeDollar'] else strMD

    
    def toc(self, options={}):

        indent = ' '

        formatters = {'yaml':[ (' '*4)+'- title: \"{}\"\n'+(' '*6)+'url: \"{}\"\n'+(' '*6)+'folders:\n\n',\
                (' '*6)+'- title: \"{}\"\n'+(' '*8)+'folders:\n\n',\
                (' '*8)+'- title: \"{}\"\n'+(' '*10)+'url: \"{}\"\n\n',\
            ],\
            'md': ['[{}]({})\n',\
                '* {}\n',\
                '\t- [{}]({})\n'
            ]\
        }

        formatter = formatters[options['output']]

        str_ = formatter[0].format(options['translations'][self.type]+' '+self.name+":", '#'+self.anchor() )
        if self.type in DocBlock2Web.rootTypes and self.type!='file_header':
            for asset_type in options['asset_order']:
                for scope in options['scope_order']:
                    assets = self.assets[asset_type] if (type(self.assets[asset_type]) is list) \
                        else (self.assets[asset_type][scope] if type(self.assets[asset_type][scope]) is list \
                            else [])
                    if len(assets)>0:
                        str_ += formatter[1].format( (scope+' ' if scope else '')+asset_type+":" )
                        for dbAsset in assets:
                            str_ += formatter[2].format( dbAsset.brief_name(options), '#'+dbAsset.anchor() )
                            """
                            if options['output']=='md':
                                str_ += "\t- "+dbAsset.href()
                            else: 
                                str_ += "    -title: %s\n" % dbAsset.brief_name(options)
                                str_ += "     href: #%s\n" % dbAsset.anchor()
                                """
            str_ += "\n"

        return str_
    
    @staticmethod
    def _parseArray(lineNoEnd, lines):

        arrayContent = ''
        openBrackets = 0
        closeBrackets = 0

        first_line = lines[lineNoEnd+1] if lineNoEnd+1 < len(lines) else ''

        if not (re.search(r'=\s*array\s*\(.*$', first_line) or re.search(r'=\s*\[.*$', first_line)):
            return ''

        # skip empty array
        if re.search(r'=\s*array\s*\(\s*\)[\s;,]*$', first_line) or re.search(r'=\s*\[\s*\][\s;,]*$', first_line):
            return ''

        for line in lines[lineNoEnd+1:]:
            arrayContent += line
            openBrackets += len(re.findall(r'\[|\(', line))
            closeBrackets += len(re.findall(r'\]|\)', line))
            if openBrackets>0 and openBrackets==closeBrackets:
                break

        return arrayContent.strip()
    
    @staticmethod
    def _parseFunctionSignature(lineNoEnd, lines):

        maxsignaturelength = 55

        full_signature = ''
        openBrackets = 0
        closeBrackets = 0

        first_line = lines[lineNoEnd+1] if lineNoEnd+1 < len(lines) else ''

        for line in lines[lineNoEnd+1:]:
            full_signature += line
            openBrackets += len(re.findall(r'\(', line))
            closeBrackets += len(re.findall(r'\)', line))
            if openBrackets>0 and openBrackets==closeBrackets:
                break
        
        full_signature = re.sub(r'\s+', ' ', full_signature)
        full_signature = full_signature.strip('{ ')
        
        mSignature = re.search(r'function\s+(?P<func_name>\w+)\s*(\((?P<params>.*)\))', full_signature)
        params = re.split(r',\s*\$', mSignature.group('params').strip('$ \t'))
        params = filter(lambda x: x.strip()!='', params)
        params = list(map(lambda x: '$'+x, params))

        if len(full_signature)>maxsignaturelength:
            return mSignature.group('func_name') + '()', params
        else:
            return mSignature.group('func_name') + '(' + mSignature.group('params') + ')', params


    
class DocBlock2WebException(Exception):
    pass


def jekyllfile(files):
    
    doc =   "---\n"+\
            "layout: docs\n"+\
            "title: \"Item and Action Tracing\"\n"+\
            "sidebar_left:\n"+\
            "  title: Class reference\n"+\
            "  class: rsd-navbar-left\n"+\
            "  id: \"rsd_navbar_left\"\n"+\
            "  folders:\n"
    
    dbws = []
    merged_categories = {}
    md = ''
    
    for i, path in enumerate(files):
        file = open(path)
        dbw = DocBlock2Web(file)
        doc += dbw.toc()
        md += dbw.md()
        dbws.append(dbw)
        merged_categories = DocBlock2Web.merge_categories( merged_categories, dbw.categories )
        
        
    doc += "sidebar_right:\n"+\
            "  title: By category\n"+\
            "  class: rsd-navbar-right\n"+\
            "  id: \"rsd_navbar_right\"\n"+\
            "  folders:\n"
            
    doc += dbws[0].cats(categories = merged_categories)
        
    doc += '---\n\n'    
    
    doc += md
    
    return doc


















