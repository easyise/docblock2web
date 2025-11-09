from .docblock2web import DocBlock2Web

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


















