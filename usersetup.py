import pymel.core as pm

def build_pymel_menu():
    master_menu = pm.menu('pymel_menu',
                          parent=pm.getMelGlobal('string','gMainWindow'),
                          tearOff=True,
                          label='+ pymel',)
    
    
    import maintenance.publish
    pm.menuItem(label='Publish Pymel',
                parent=master_menu,
                command=maintenance.publish.publish,
                annotation='Publish pymel from working git to sww.')
    
    import maintenance.docs

    def build_docs(*args):
        run=True
        clean=True
        count = 0
        
        while run:
            run=False
            try:
                maintenance.docs.generate(clean=clean)
            except AttributeError:
                run=True
                clean=False
            count += 1
            if count > 10:
                print 'Depth limit hit'
                break
        
        maintenance.docs.build()
        
    pm.menuItem(label='Build Docs',
                parent=master_menu,
                command=build_docs,
                annotation='Build New Docs')

pm.evalDeferred(build_pymel_menu)
