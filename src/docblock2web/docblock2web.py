import re
import os, io
from pathlib import Path

from .docblock import DocBlockJS, DocBlockPHP, DocBlock
from .docblock2web_exception import DocBlock2WebException

class DocBlock2Web:

    dockblocks = []
    fileHierarchy = []
    categories = {}
    sourceFile = ''
    sourceFileName = ''

    rootTypes = ['file_header', 'class', 'jquery_plugin', 'js_class', 'js_function']

    file_extensions = {'.php': 'PHP', '.js': 'JavaScript'}

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
            'returns': 'Returns', \
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
            'js_class': 'JS class',\
            'js_function': 'JS function',\
            'jquery_plugin': 'jQuery plugin',\
            'categories': 'By category',\
        }}

    def __init__(self, sourceFile, **options):
        
        self.sourceFile = sourceFile

        self.sourceFileName = self._get_source_file_name(sourceFile, **options)
        self.docblock_class = self._get_docblock_class(sourceFile, **options)

        lines = []
        if isinstance(sourceFile, (io.TextIOWrapper, io.StringIO)):
            lines = sourceFile.readlines()
        elif isinstance(sourceFile, Path) or isinstance(sourceFile, str):
            with open(sourceFile, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            raise DocBlock2WebException("sourceFile must be a file-like object, pathlib.Path or str %s" % \
                                        ("(file: %s)" % (self.sourceFileName) if self.sourceFileName else '') )

        self.dockblocks = []
        self.categories = {}
        self.options = DocBlock2Web.options.copy()
        self.options.update(options)

        # getting docblock coordinates
        lineNo = 0
        db = {}
        for lineNo, line in enumerate(lines):
            mStart = DocBlock.reStart.search(line)
            mEnd = DocBlock.reEnd.search(line)
            
            if mStart:
                # print("DocBlock starts at line {}:{}".format(lineNo+1, mStart.end()))
                db = {'begin': [lineNo,mStart.end()]}
                

            if mEnd:
                # print("db ends at line {}:{}".format(lineNo+1, mEnd.start()), db)
                if not db:
                    continue    
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
                        o_db = self.docblock_class( **db, 
                                        master_parser=self,
                                        lines=lines,
                                        sourceFile=sourceFile, 
                                        sourceFileName=self.sourceFileName )
                        self.dockblocks.append( o_db )
                db = {}
                continue

            if db and not mStart and not DocBlock.reLineStart.search(line):
               raise DocBlock2WebException("DocBlock content line does not start with '*': %s" % \
                                            ("(file: %s:%d)" % (self.sourceFileName, lineNo+1) if self.sourceFileName else '') ) 
                

        # Collect class assets
        for i, db in enumerate(self.dockblocks):
            if i==0 and not db.type:
                db.type='file_header'
                continue
            if db.type in ['class', 'js_class', 'jquery_plugin']:
                db.collectProperties(i, self.dockblocks)
                continue
        
        for i, db in enumerate(self.dockblocks):
            if db.type=='js_prototype_method' and hasattr(db, 'parent_name'):
                for j, db_parent in enumerate(self.dockblocks):
                    if db.parent_name==db_parent.name and db_parent.type=='function':
                        print(db.parent_name, db_parent.name, db_parent.assets)
                        db.parent = db_parent                        
                        if 'methods' not in db_parent.assets:
                            db_parent._init_assets()
                        db_parent.assets['methods']['public'].append(db)
                        db_parent.type = 'js_class'
                        if db_parent.parent:
                            if db_parent.name in [d.name for d in db_parent.parent.assets['methods']['public']]:
                                ix = [d.name for d in db_parent.parent.assets['methods']['public']].index(db_parent.name)
                                del db_parent.parent.assets['methods']['public'][ix]
                                db_parent.parent.assets['properties']['private'].append(db_parent)
                        break
        
        for i, db in enumerate(self.dockblocks):
            if 'category' in db.tokens and hasattr(db, 'name'):
                for cat in db.tokens['category']:
                    cat = cat.strip()
                    if cat not in self.categories:
                        self.categories[cat] = []
                    self.categories[cat].append(db)

        for cat, dbs in self.categories.items():
            dbs = dbs.sort(key=lambda db: ((db.parent.name if hasattr(db, 'parent') and hasattr(db.parent, 'name') else '')+db.name).lower())

    @staticmethod
    def _is_js_root_function(docblock):
        subject = getattr(docblock, 'rawSubject', '')
        if not subject:
            return False
        subject = subject.strip()

        # Skip class-style method declarations (constructor, static methods, etc.)
        if re.match(r'(?:static\s+)?(?:async\s+)?[A-Za-z_$][\w$]*\s*\(', subject) and not subject.startswith('function'):
            return False

        if subject.startswith('constructor('):
            return False

        top_level_patterns = [
            r'(?:export\s+)?(?:default\s+)?function\s+',
            r'(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*='
        ]

        return any(re.match(pattern, subject) for pattern in top_level_patterns)

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
            dbs = dbs.sort(key=lambda db: ((db.parent.name if hasattr(db, 'parent') and db.parent else '')+db.name).lower())

        return categories
    
    def _get_source_file_name_ext(self, sourceFile, **kwargs):

        if language := kwargs.get('language', None):
            if language=='PHP':
                return 'unknown', '.php'
            elif language=='JavaScript':
                return 'unknown', '.js'

        ext = ''
        name = ''
        if isinstance(sourceFile, (io.TextIOWrapper, io.StringIO)):
            if hasattr(sourceFile, 'name'):
                ext = Path(sourceFile.name).suffixes[-1]
                name = Path(sourceFile.name).name
            else:
                sourceFile.seek(0)
                if re.search(r'<\?php', sourceFile.read(1024)):
                    ext = '.php'
                    name = 'unknown'
                    sourceFile.seek(0)
                else:
                    raise DocBlock2WebException("Unable to determine language from sourceFile")         
        elif isinstance(sourceFile, Path):
            ext = ''.join(sourceFile.suffixes)
            name = sourceFile.name
        elif isinstance(sourceFile, str):
            ext = ''.join(Path(sourceFile).suffixes)
            name = Path(sourceFile).name

        return name, ext

    def _get_source_file_name(self, sourceFile, **kwargs):
        name, ext = self._get_source_file_name_ext(sourceFile, **kwargs)
        return name+ext

    def _get_docblock_class(self, sourceFile, **kwargs):

        name, ext = self._get_source_file_name_ext(sourceFile, **kwargs)

        if ext in DocBlock2Web.file_extensions:
            language = DocBlock2Web.file_extensions[ext]
            if language=='PHP':
                return DocBlockPHP
            elif language=='JavaScript':
                return DocBlockJS
            else:
                raise DocBlock2WebException("DocBlock class for language '%s' is not implemented %s" % (language, 
                                                                                                          "(file: %s)" % (self.sourceFileName) if self.sourceFileName else '') )
        else:
            raise DocBlock2WebException("File extension '%s' is not supported %s" % (ext, 
                                                                                      "(file: %s)" % (self.sourceFileName) if self.sourceFileName else '') )


    # returns Markdown
    def md(self):

        md = ''
        for i, db in enumerate(self.dockblocks):
            
            if self.options['display']=='hierarchial' and db.type not in DocBlock2Web.rootTypes:
                continue

            md += db.md(self.options)
                
            md += "\n\n\n"

        return md
    
    #returns TOC yaml, hiearchially
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

    # returns categories yaml
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
                parentName_db = db.parent.name if hasattr(db, 'parent') and hasattr(db.parent, 'name') else ''
                if parentName!='' and parentName!=parentName_db:
                    flagMultipleClasses = True
                    break
                parentName = parentName_db
            if flagMultipleClasses:
                break

        for i, cat in enumerate(cats):
            str_ += formatter[0].format(cat)
            for j, db in enumerate(categories[cat]):
                str_ += formatter[1].format( db.brief_name({'showParent': flagMultipleClasses}), '#'+db.anchor() )

        return str_
