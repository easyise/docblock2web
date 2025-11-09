import re
import sys

from .docblock2web_exception import DocBlock2WebException

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

    def __init__(self, master_parser, begin, end, subject, contents, lines, **kwargs):

        self.master_parser = master_parser

        self.lineNoStart = begin
        self.lineNoEnd = end
        self.lines = lines

        self.obj_prefix = ''

        self.rawSubject = subject
        self.rawContents = contents

        self.sourceFile = kwargs.get('sourceFile', None)  
        self.sourceFileName = kwargs.get('sourceFileName', '')

        self.subject = ''
        self.type = None
        self.subtype = None
        self.scope = None

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

    def updateScope(self):
        if self.scope:
            return
        if 'event' in self.tokens:
            self.scope = 'event'
            return
        self.scope = 'static' if re.search('static', self.rawSubject, re.IGNORECASE) \
            else ('protected' if re.search('protected', self.rawSubject, re.IGNORECASE) \
                else ('private' if re.search('private', self.rawSubject, re.IGNORECASE) \
                    else 'public'))
        
    def _init_assets(self):
        self.assets = {}
        self.assets['properties'] = {'public': [], 'static': [], 'private': [], 'protected': []}
        self.assets['methods'] = {'public': [], 'static': [], 'private': [], 'protected': []}
        self.assets['events'] = []
        self.assets['categories'] = {}


    def collectProperties(self, selfIndex, alldockblocks):
        
        self._init_assets()

        root_types = self.master_parser.rootTypes

        for i in range(selfIndex+1, len(alldockblocks)):
            db = alldockblocks[i]
            
            if db.type in root_types:
                break

            db.updateScope()

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
        
        return (self.parent.name.lower()+'_' if self.parent else '') \
            + (self.obj_prefix + '_' if self.obj_prefix else '') \
            + self.name.lower()


    def brief_name(self, options={}):

        return self.name
        

    
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
        tag_order = self.master_parser.options['tag_order']
        for tag in sorted(ts, key=lambda x: tag_order.index(x) if x in tag_order else len(tag_order)):
            if tag not in ['param', 'return', 'example', 'description']:
                if tag in options['tags'] and tag in self.tokens:
                    tags += '__'+options['tags'][tag]+'__'+": "+lst2str(self.tokens[tag])+"  \n"
                else:
                    raise DocBlock2WebException("Tag '%s' is not supported %s" % (tag, 
                                                                                  "(file: %s:%d)" % (self.sourceFileName,
                                                                                                     self.lineNoStart[0]) if self.sourceFileName else '') )
                
        tags += '\n' if len(tags)>0 else ''

        strMD += tags

        if options['display']=='hierarchial' and self.type in self.master_parser.rootTypes and self.type!='file_header':
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

        root_types = self.master_parser.rootTypes
        colon = ':' if [y for x in self.assets.values() if len(x) > 0 for y in x.values() if len(y) > 0 ] else ''
        str_ = formatter[0].format(options['translations'][self.type]+' '+self.name + colon, '#'+self.anchor() )
        if self.type in root_types and self.type!='file_header':
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
    
    def _updateSubject(self):
        pass
    
    @staticmethod
    def _parseArray(lineNoEnd, lines):
        return ''
    
    @staticmethod
    def _parseFunctionSignature(lineNoEnd, lines):
        return '', []
    
    

class DocBlockPHP(DocBlock):

    language = 'PHP'

    def _updateSubject(self):

        mClass = re.search(r'class\s+(\w+)', self.rawSubject, re.IGNORECASE)
        if mClass:
            self.type = 'class'
            self.subject = mClass.group(1)
            self.name = mClass.group(1)
            self.obj_prefix = 'cls'
            return

        mFunction = re.search(r'function\s((\w+)\s*\()', self.rawSubject, re.IGNORECASE)
        if mFunction:
            self.type = 'function'
            self.name = mFunction.group(2)
            self.subject, params = __class__._parseFunctionSignature(self.lineNoEnd[0], self.lines)
            if ('param' not in self.tokens or not self.tokens['param']) and params:
                self.tokens['param'] = params
            self.obj_prefix = 'fn'
            return

        mVariable = re.search(r'(\$[\w]+)\s*=\s*', self.rawSubject, re.IGNORECASE)
        if mVariable:
            self.type = 'property'
            self.subject = mVariable.group(1)
            self.name = self.reDollar.sub(r'\2', mVariable.group(1))
            self.obj_prefix = 'prop'
            return
    
    def brief_name(self, options={}):

        return  (self.parent.name+'::' if self.parent and 'showParent' in options and options['showParent'] else '')+\
                ('$' if self.type=='property' else '')+\
                self.name+\
                ('()' if self.type=='function' else '')  

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
        params = re.split(r',\s*\&?\$', mSignature.group('params').strip('&$ \t'))
        params = filter(lambda x: x.strip()!='', params)
        params = list(map(lambda x: '$'+x, params))

        if len(full_signature)>maxsignaturelength:
            return mSignature.group('func_name') + '()', params
        else:
            return mSignature.group('func_name') + '(' + mSignature.group('params') + ')', params
        
class DocBlockJS(DocBlock):

    language = 'JavaScript'

    _RESERVED_METHOD_NAMES = {'if', 'for', 'while', 'switch', 'catch', 'finally', 'do', 'return'}

    def _updateSubject(self):

        signature = self._collect_signature()
        if not signature:
            return

        signature = re.sub(r'\s+', ' ', signature.strip())

        # $.fn.myPlugin = function(method) { ... }
        m_plugin_assign = re.search(r'\$\.fn\.([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\((?P<params>[^)]*)\)', signature)
        if m_plugin_assign:
            plugin_name = m_plugin_assign.group(1)
            params = self._split_params(m_plugin_assign.group('params'))
            self.type = 'function'
            self.name = plugin_name
            self.subject = self._format_signature(plugin_name, params)
            self._ensure_param_tokens(params)
            self.plugin_candidate = plugin_name
            self.obj_prefix = 'jqp'
            return

        # (function($){ ... })( jQuery ); pattern – infer plugin name from body
        if signature.startswith('(function('):
            plugin_name = self._infer_plugin_name()
            if plugin_name:
                self.type = 'jquery_plugin'
                self.name = plugin_name
                self.subject = plugin_name
                self.plugin_candidate = plugin_name
                self.obj_prefix = 'jqp'
                return

        # class declaration
        m_class = re.search(r'(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)', signature)
        if m_class:
            self.type = 'class'
            self.name = m_class.group(1)
            self.subject = self.name
            self.obj_prefix = 'jscls'
            return

        # prototype assignment Foo.prototype.bar = function(...)
        m_prototype = re.search(r'([A-Za-z_$][\w$]*)\.prototype\.([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\((?P<params>[^)]*)\)', signature)
        if m_prototype:
            owner, method = m_prototype.group(1), m_prototype.group(2)
            params = self._split_params(m_prototype.group('params'))
            self.type = 'js_prototype_method'
            self.parent_name = owner
            self.name = method
            self.subject = self._format_signature(f"{owner}.{method}", params)
            self._ensure_param_tokens(params)
            self.obj_prefix = 'jsfn'
            return

        # object literal method: name: function(...)
        m_object_method = re.search(r'([A-Za-z_$][\w$]*)\s*:\s*(?:async\s+)?function\s*\((?P<params>[^)]*)\)', signature)
        if m_object_method:
            method = m_object_method.group(1)
            params = self._split_params(m_object_method.group('params'))
            self.type = 'function'
            self.name = method
            self.subject = self._format_signature(method, params)
            self._ensure_param_tokens(params)
            self.obj_prefix = 'jsfn'
            return

        # function declaration
        m_function_decl = re.search(r'(?:export\s+)?(?:default\s+)?function\s+([A-Za-z_$][\w$]*)\s*\((?P<params>[^)]*)\)', signature)
        if m_function_decl:
            func_name = m_function_decl.group(1)
            params = self._split_params(m_function_decl.group('params'))
            self.type = 'function'
            self.name = func_name
            self.subject = self._format_signature(func_name, params)
            self._ensure_param_tokens(params)
            self.obj_prefix = 'jsfn'
            return

        # const/let/var assignment to function expression
        m_function_expr = re.search(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\((?P<params>[^)]*)\)', signature)
        if m_function_expr:
            func_name = m_function_expr.group(1)
            params = self._split_params(m_function_expr.group('params'))
            self.type = 'function'
            self.name = func_name
            self.subject = self._format_signature(func_name, params)
            self._ensure_param_tokens(params)
            self.obj_prefix = 'jsfn'
            return

        # arrow function with parentheses: const name = (params) =>
        m_arrow = re.search(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?\((?P<params>[^)]*)\)\s*=>', signature)
        if m_arrow:
            func_name = m_arrow.group(1)
            params = self._split_params(m_arrow.group('params'))
            self.type = 'function'
            self.name = func_name
            self.subject = self._format_signature(func_name, params)
            self._ensure_param_tokens(params)
            self.obj_prefix = 'jsfn'
            return

        # arrow function single param: const name = param =>
        m_arrow_single = re.search(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*=>', signature)
        if m_arrow_single:
            func_name = m_arrow_single.group(1)
            params = [m_arrow_single.group(2)]
            self.type = 'function'
            self.name = func_name
            self.subject = self._format_signature(func_name, params)
            self._ensure_param_tokens(params)
            self.obj_prefix = 'jsfn'
            return

        # class method (including constructor/static)
        m_class_method_static = re.search(r'static\s+(?:async\s+)?([A-Za-z_$][\w$]*)\s*\((?P<params>[^)]*)\)', signature)
        if m_class_method_static:
            method = m_class_method_static.group(1)
            params = self._split_params(m_class_method_static.group('params'))
            self.type = 'function'
            self.name = method
            self.subject = self._format_signature(method, params)
            self._ensure_param_tokens(params)
            self.obj_prefix = 'jsfn'
            return

        m_class_method = re.search(r'(?:async\s+)?([A-Za-z_$][\w$]*)\s*\((?P<params>[^)]*)\)\s*\{', signature)
        if m_class_method:
            method = m_class_method.group(1)
            if method not in self._RESERVED_METHOD_NAMES:
                params = self._split_params(m_class_method.group('params'))
                self.type = 'function'
                self.name = method
                self.subject = self._format_signature(method, params)
                self._ensure_param_tokens(params)
                self.obj_prefix = 'jsfn'
                return

        # property assignments
        m_this_property = re.search(r'this\.([A-Za-z_$][\w$]*)\s*=', signature)
        if m_this_property:
            prop = m_this_property.group(1)
            self.type = 'property'
            self.name = prop
            self.subject = f'this.{prop}'
            self.obj_prefix = 'jsprop'
            return

        m_var_property = re.search(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=', signature)
        if m_var_property:
            prop = m_var_property.group(1)
            self.type = 'property'
            self.name = prop
            self.subject = prop
            self.obj_prefix = 'jsprop'
            return

        # fallback – keep raw subject
        self.subject = signature

    def _collect_signature(self):
        subject = (self.rawSubject or '').strip()
        if not subject:
            return ''

        if subject.endswith('{') or subject.endswith(';'):
            return subject

        signature_parts = [subject]
        start_index = self.lineNoEnd[0]+1 if isinstance(self.lineNoEnd, (list, tuple)) else self.lineNoEnd + 1
        max_lines = 6

        while start_index < len(self.lines) and max_lines > 0:
            fragment = self.lines[start_index].strip()
            start_index += 1
            if not fragment:
                continue
            signature_parts.append(fragment)
            if fragment.endswith('{') or fragment.endswith(';'):
                break
            max_lines -= 1

        return ' '.join(signature_parts)

    def _infer_plugin_name(self):
        start_index = self.lineNoEnd[0]+1 if isinstance(self.lineNoEnd, (list, tuple)) else self.lineNoEnd + 1
        pattern = re.compile(r'^\s*\$\.fn\.([A-Za-z_$][\w$]*)')
        open_brackets = 0
        found_open = False

        while start_index < len(self.lines):
            line = self.lines[start_index]
            if not found_open:
                if '{' in line:
                    found_open = True
                    open_brackets = line.count('{') - line.count('}')
            else:
                open_brackets += line.count('{') - line.count('}')

            match = pattern.search(line)
            if match:
                return match.group(1)

            if found_open and open_brackets <= 0:
                break

            start_index += 1
        return None
    

    def brief_name(self, options={}):

        parent = ''
        if self.parent and 'showParent' in options and options['showParent']:
            parent_refix = ''
            if self.parent.type=='jquery_plugin':
                parent_refix = '$.fn.'
            else:
                parent_refix =''
            parent = parent_refix + self.parent.name

        name = self.name

        if self.type=='jquery_plugin':
            name = '$.fn.' + name

        return  (parent + '.' if parent else '') + \
                name + \
                ('()' if self.type=='function' else '')  

    @staticmethod
    def _split_params(param_str):
        if param_str is None:
            return []
        param_str = param_str.strip()
        if not param_str:
            return []

        params = []
        current = ''
        depth = 0

        for char in param_str:
            if char == ',' and depth == 0:
                if current.strip():
                    params.append(current.strip())
                current = ''
                continue
            current += char
            if char in '({[':
                depth += 1
            elif char in ')}]':
                depth = max(0, depth - 1)

        if current.strip():
            params.append(current.strip())

        return params

    @staticmethod
    def _format_signature(name, params):
        param_str = ', '.join(params) if params else ''
        return f"{name}({param_str})" if param_str else f"{name}()"

    def _ensure_param_tokens(self, params):
        if not params:
            return
        if 'param' not in self.tokens or not self.tokens['param']:
            self.tokens['param'] = params

    @staticmethod
    def _parseArray(lineNoEnd, lines):

        arrayContent = ''
        openBrackets = 0
        closeBrackets = 0

        first_line = lines[lineNoEnd+1] if lineNoEnd+1 < len(lines) else ''

        if not (re.search(r'=\s*\{', first_line) or re.search(r'=\s*\[', first_line) or re.search(r'\$\.extend\(', first_line)):
            return ''

        # skip empty literal
        if re.search(r'=\s*\{\s*\}[\s;,]*$', first_line) or re.search(r'=\s*\[\s*\][\s;,]*$', first_line):
            return ''

        for line in lines[lineNoEnd+1:]:
            arrayContent += line
            openBrackets += len(re.findall(r'[\{\[]', line))
            closeBrackets += len(re.findall(r'[\}\]]', line))
            if openBrackets>0 and openBrackets==closeBrackets:
                break

        return arrayContent.strip()

    @staticmethod
    def _parseFunctionSignature(lineNoEnd, lines):

        collected = []
        idx = lineNoEnd+1
        max_lines = 6
        open_paren = 0

        while idx < len(lines) and max_lines > 0:
            fragment = lines[idx].strip()
            idx += 1
            if not fragment:
                continue
            collected.append(fragment)
            open_paren += fragment.count('(') - fragment.count(')')
            if open_paren <= 0 and (fragment.endswith('{') or fragment.endswith(';') or '=>' in fragment):
                break
            max_lines -= 1

        signature = ' '.join(collected)
        signature = re.sub(r'\s+', ' ', signature)

        # Attempt to reuse parsing logic on the collected signature
        m_function = re.search(r'(?:function\s+)?([A-Za-z_$][\w$]*)\s*\((?P<params>[^)]*)\)', signature)
        if m_function:
            name = m_function.group(1)
            params = DocBlockJS._split_params(m_function.group('params'))
            return DocBlockJS._format_signature(name, params), params

        m_arrow = re.search(r'([A-Za-z_$][\w$]*)\s*=>', signature)
        if m_arrow:
            name = m_arrow.group(1)
            params = [name]
            return DocBlockJS._format_signature(name, params), params

        return signature.strip(), []
    