from .docblock2web import DocBlock2Web

def jekyllfile(files, **kwargs):

    defaults = {
        "title": "Documentation",
        "layout": "docs",
        "title_sidebar_left": "Documentation",
        "css_prefix_sidebar_left": "",
        "title_sidebar_right": "Documentation",
        "css_prefix_sidebar_right": "",
    }

    values = { **defaults, **kwargs }   
    
    doc =   "---\n"+\
            "layout: {layout}\n"+\
            "title: \"{title}\"\n"+\
            "sidebar_left:\n"+\
            "  title: \"{title_sidebar_left}\"\n"+\
            "  class: \"{css_prefix_sidebar_left}navbar-left\"\n"+\
            "  id: \"{css_prefix_sidebar_left}navbar_left\"\n"+\
            "  folders:\n"

    doc = doc.format(**values)

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

    sidebar_right =  "sidebar_right:\n"+\
            "  title: \"{title_sidebar_right}\"\n"+\
            "  class: \"{css_prefix_sidebar_right}navbar-right\"\n"+\
            "  id: \"{css_prefix_sidebar_right}navbar_right\"\n"+\
            "  folders:\n"

    sidebar_right = sidebar_right.format(**values)

    doc += sidebar_right
            
    doc += dbws[0].cats(categories = merged_categories)
        
    doc += '---\n\n'    
    
    doc += md
    
    return doc


















