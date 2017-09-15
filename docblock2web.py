import re
import os

class docblock2web:

    docBlocks = []
    fileHierarchy = []
    sourceFile = ''
    sourceFileName = ''

    rootTypes = ['file_header', 'class', 'js_function', 'jquery_plugin']

    options = {'asset_order': ['properties', 'methods', 'events'],\
        'scope_order': ['public', 'static', 'protected', 'private'], \
        'header_level': 2, \
        'display': 'hierarchial', \
        'escapeDollar': False, \
        'tags': { \
            #'api': 'API', \ #not supported yet
            'author': 'Author', \
            'category': 'Category', \
            'copyright': 'Copyright', \
            'deprecated': 'Depracated', \
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
        }}

    def __init__(self, sourceFile, sourceFileName='', options={}):
        
        self.sourceFile = sourceFile
        self.sourceFileName = sourceFileName

        lines = sourceFile.readlines()
        self.docBlocks = []
        self.options = docblock2web.options.copy()
        self.options.update(options)

        # getting docblock coordinates
        lineNo = 0
        for line in lines:
            mStart = docBlock.reStart.search(line)
            mEnd = docBlock.reEnd.search(line)
            
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
                    lineProcessed = re.sub(docBlock.reEnd, '', \
                                                    re.sub(docBlock.reStart, '',\
                                                           dbLine)
                                                    )
                    db['contents'] +=  re.sub(docBlock.reLineStart, '', lineProcessed )
                db['contents'] = db['contents'].strip()
                if db['contents'] !='' and not re.search("\@ignore", db['contents']):
                    db['subject'] = lines[lineNo+1].strip()
                    if db['subject'] != '' or len(self.docBlocks)==0:
                        self.docBlocks.append( docBlock( **db ) )
                
            lineNo += 1

        for i, db in enumerate(self.docBlocks):
            if i==0 and not db.type:
                db.type='file_header'
                continue
            if db.type=='class':
                db.collectClassAssets(i, self.docBlocks)
                continue
            



    # returns Markdown
    def md(self):

        md = ''
        for i, db in enumerate(self.docBlocks):
            
            if self.options['display']=='hierarchial' and db.type not in docblock2web.rootTypes:
                continue

            md += db.md(self.options)
                
            md += "\n\n\n"

        return md

class docBlock:

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

    def __init__(self, begin, end, subject, contents):

        self.lineNoStart = begin
        self.lienNoEnd = end

        self.rawSubject = subject
        self.rawContents = contents

        self.subject = ''
        self.type = None
        self.subtype = None
        self.scope = None

        self.parent = None

        self.tokens = {}
        self.tokenSequence = []
        self.assets = {}

        def _finishToken(activeToken, activeTokenContent):
            if activeToken not in self.tokens:
                self.tokens[activeToken] = []
            self.tokens[activeToken].append(activeTokenContent)
            self.tokenSequence.append(activeToken)

        aContents = self.rawContents.split("\n")
        reToken = "^\@([a-z]+)"
        retVal = {'subject': subject, 'contnent': contents}
        
        activeToken = 'description'
        activeTokenContent = ''
        
        for i in range(0,len(aContents)):
            curString = aContents[i]
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

        mFunction = re.search(r'function\s((\w+)\s*\([^)]+\))', self.rawSubject, re.IGNORECASE)
        if mFunction:
            self.type = 'function'
            self.subject = mFunction.group(1)
            self.name = mFunction.group(2)
            return

        mVariable = re.search(r'(\$[\w]+)\s*=\s*', self.rawSubject, re.IGNORECASE)
        if mVariable:
            self.type = 'variable'
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

    def collectClassAssets(self, selfIndex, allDocBlocks):

        self.assets['properties'] = {'public': [], 'static': [], 'private': [], 'protected': []}
        self.assets['methods'] = {'public': [], 'static': [], 'private': [], 'protected': []}
        self.assets['events'] = []

        for i in range(selfIndex+1, len(allDocBlocks)):
            db = allDocBlocks[i]
            
            if db.type in docblock2web.rootTypes:
                break;

            db.updateScope();
            if db.type=='function':
                if db.scope=='event':
                    self.assets['events'].append(db)    
                elif db.scope in self.assets['methods']:
                    self.assets['methods'][db.scope].append(db)
                else:
                    continue

            if db.type=='variable' and db.scope in self.assets['properties']:
                self.assets['properties'][db.scope].append(db)
            db.parent = self
            

    def anchor(self):
        return (self.parent.name.lower()+'-' if self.parent else '') + self.name.lower()


    def md(self, options={}):

        def lst2str(lst):
            ret = ''
            for line in lst:
                ret += line+"\n"
            return ret.strip()

        strMD = ''
        header = ''

        if(self.type!='file_header'):
            header = ('#' * (options['header_level']+(1 if self.scope else 0)) + ' ') \
                + ('<a name="%s"></a>' % self.anchor() if self.name else '') \
                + (self.scope+' ' if self.scope else '') \
                + self.type +' '+self.subject
            header += "\n\n"

        strMD = header

        strMD += lst2str(self.tokens['description'])+"\n\n"

        ts = set(self.tokenSequence)
        tags = ''
        for tag in ts:
            if tag not in ['param', 'return', 'example', 'description']:
                tags += '__'+options['tags'][tag]+'__'+": "+lst2str(self.tokens[tag])+"  \n"
        tags += '\n' if len(tags)>0 else ''

        strMD += tags

        if self.type=='function':
            if 'param' in self.tokens:
                strMD += '__'+options['tags']['param']+'__'+": \n"
                for param in self.tokens['param']:
                    strMD += '* '
                    m = self.reParam.search(param)
                    if m:
                        param = '__%s__ (%s)' % (m.group('name'), m.group('type'))+ ' - '+self.reParam.sub('', param).strip('- ')

                    strMD += re.sub(r'\n', '\n\t', param)

                    strMD += "\n"

            if 'return' in self.tokens:
                strMD += '__'+options['tags']['return']+'__'+": "+lst2str(self.tokens['return'])+"\n"



        if options['display']=='hierarchial' and self.type in docblock2web.rootTypes and self.type!='file_header':
            for asset_type in options['asset_order']:
                for scope in options['scope_order']:
                    assets = self.assets[asset_type] if (type(self.assets[asset_type]) is list) \
                        else (self.assets[asset_type][scope] if type(self.assets[asset_type][scope]) is list \
                            else [])
                    for dbAsset in assets:
                        strMD += dbAsset.md(options)+"\n\n"

        return self.reDollar.sub(r'\\\1\2', strMD) if options['escapeDollar'] else strMD










