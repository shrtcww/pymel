"The primary module for maya commands and node classes"

#import pymel.mayahook as mayahook

import sys, logging
import pymel.version as _version
import pymel.mayahook as mayahook

# will check for the presence of an initilized Maya / launch it
mayahook.mayaInit() 


import factories

from general import *
from context import *
from system import *
from windows import *
from animation import *
from effects import *
from modeling import *
from rendering import *
from language import *
from other import *

# to allow lazy loading, we avoid import *
import nodetypes
import nodetypes as nt
import datatypes
import datatypes as dt
import uitypes
import uitypes as ui

import runtime
import maya.cmds as cmds

# initialize MEL 
mayahook.finalize()

import maya.cmds as cmds

_logger = logging.getLogger('pymel.core')

#: dictionary of plugins and the nodes and commands they register   
_pluginData = {}

_module = sys.modules[__name__]
    
def _pluginLoaded( *args ):

    if len(args) > 1:
        # 2009 API callback, the args are ( [ pathToPlugin, pluginName ], clientData )
        pluginName = args[0][1]
    else:
        pluginName = args[0]
        
    if not pluginName:
        return
    
    #print type(array)
    #pluginPath, pluginName = array
    import pmcmds
    _logger.info("Plugin loaded: %s", pluginName)
    
    _pluginData[pluginName] = {}
    
    try:
        commands = pmcmds.pluginInfo(pluginName, query=1, command=1)
    except:
        _logger.error("Failed to get command list from %s", pluginName)
        commands = None

    
    # Commands
    if commands:
        _pluginData[pluginName]['commands'] = commands
        _logger.debug( "adding new commands: %s" % ', '.join(commands) )
        for funcName in commands:
            #__logger.debug("adding new command:", funcName)
            factories.cmdlist[funcName] = factories.getCmdInfoBasic( funcName )
            pmcmds.addWrappedCmd(funcName)
            func = factories.functionFactory( funcName )
            try:
                if func:
                    setattr( _module, funcName, func )
                    if 'pymel.all' in sys.modules:
                        setattr( sys.modules['pymel.all'], funcName, func )
                else:
                    _logger.warning( "failed to create function" )
            except Exception, msg:
                _logger.warning("exception: %s" % str(msg) )
    
    # Nodes          
    mayaTypes = cmds.pluginInfo(pluginName, query=1, dependNode=1)
    #apiEnums = cmds.pluginInfo(pluginName, query=1, dependNodeId=1) 
    if mayaTypes :
        
        def addPluginPyNodes(*args):
            try:
                id = _pluginData[pluginName]['callbackId']
                if id is not None:
                    api.MEventMessage.removeCallback( id )
                    id.disown()
            except KeyError:
                _logger.warning("could not find callback id!")
            
            _pluginData[pluginName]['dependNodes'] = mayaTypes
            _logger.debug("adding new nodes: %s", ', '.join( mayaTypes ))
            
            for mayaType in mayaTypes:
                
                inheritance = factories.getInheritance( mayaType )
                
                if not util.isIterable(inheritance):
                    _logger.warn( "could not get inheritance for mayaType %s" % mayaType)
                else:
                    #__logger.debug(mayaType, inheritance)
                    #__logger.debug("adding new node:", mayaType, apiEnum, inheritence)
                    # some nodes in the hierarchy for this node might not exist, so we cycle through all 
                    parent = 'dependNode'
                    
                    for node in inheritance:
                        nodeName = factories.addPyNode( nodetypes, node, parent )
                        parent = node
                        if 'pymel.all' in sys.modules:
                            # getattr forces loading of Lazy object
                            setattr( sys.modules['pymel.all'], nodeName, getattr(nodetypes,nodeName) )
        
        # evidently isOpeningFile is not avaiable in maya 8.5 sp1.  this could definitely cause problems
        if api.MFileIO.isReadingFile() or ( _version.CURRENT >= _version.v2008 and api.MFileIO.isOpeningFile() ):
            #__logger.debug("pymel: Installing temporary plugin-loaded callback")
            id = api.MEventMessage.addEventCallback( 'SceneOpened', addPluginPyNodes )
            _pluginData[pluginName]['callbackId'] = id
            # scriptJob not respected in batch mode, had to use api
            #cmds.scriptJob( event=('SceneOpened',doSomethingElse), runOnce=1 ) 
        else:
            # add the callback id as None so that if we fail to get an id in addPluginPyNodes we know something is wrong
            _pluginData[pluginName]['callbackId'] = None
            addPluginPyNodes()

            


             
def _pluginUnloaded(*args):

    if len(args) > 1:
        # 2009 API callback, the args are
        # ( [ pluginName, pathToPlugin ], clientData )  OR
        # ( [ pathToPlugin ], clientData )
        pluginName = args[0][0]
    else:
        pluginName = args[0]
    
    _logger.info("Plugin unloaded: %s" % pluginName)
    import pmcmds
    try:
        data = _pluginData.pop(pluginName)
    except KeyError: 
        pass
    else:
        # Commands
        commands = data.pop('commands', [])
        if commands:
            _logger.info("Removing commands: %s", ', '.join( commands ))
            for command in commands:
                try:
                    pmcmds.removeWrappedCmd(command)
                    _module.__dict__.pop(command)
                except KeyError:
                    _logger.warn( "Failed to remove %s from module %s" % (command, _module.__name__) )
                        
        # Nodes
        nodes = data.pop('dependNodes', [])
        if nodes:
            _logger.debug("Removing nodes: %s" % ', '.join( nodes ))
            for node in nodes:
                factories.removePyNode( nodetypes, node )


global _pluginLoadedCB
global _pluginUnloadedCB
_pluginLoadedCB = None
_pluginUnloadedCB = None

def _installCallbacks():
    """install the callbacks that trigger new nodes and commands to be added to pymel when a 
    plugin loads.  This is called from pymel.__init__
    """

    global _pluginLoadedCB
    if _pluginLoadedCB is None:
        _pluginLoadedCB = True
        _logger.debug("Adding pluginLoaded callback")
        #_pluginLoadedCB = pluginLoadedCallback(module)

        
        if _version.CURRENT >= _version.v2009:
            id = api.MSceneMessage.addStringArrayCallback( api.MSceneMessage.kAfterPluginLoad, _pluginLoaded  )
            id.disown()
        else:
            # BUG: this line has to be a string, because using a function causes a 'pure virtual' error every time maya shuts down 
            cmds.loadPlugin( addCallback='import pymel.core; pymel.core._pluginLoaded("%s")' )
    else:
        _logger.debug("PluginLoaded callback already exists")
    
    global _pluginUnloadedCB
    if _pluginUnloadedCB is None:
        _pluginUnloadedCB = True
        
        # BUG: autodesk still has not add python callback support, and calling this as MEL is not getting the plugin name passed to it
        #mel.unloadPlugin( addCallback='''python("import pymel; pymel._pluginUnloaded('#1')")''' )
        
        if _version.CURRENT >= _version.v2009:
            _logger.debug("Adding pluginUnloaded callback")
            id = api.MSceneMessage.addStringArrayCallback( api.MSceneMessage.kAfterPluginUnload, _pluginUnloaded )
            id.disown()
        

    else:
        _logger.debug("PluginUnloaded callback already exists")

    # add commands and nodes for plugins loaded prior to importing pymel
    preLoadedPlugins = cmds.pluginInfo( q=1, listPlugins=1 ) 
    if preLoadedPlugins:
        _logger.info("Updating pymel with pre-loaded plugins: %s" % ', '.join( preLoadedPlugins ))
        level = _logger.getEffectiveLevel()
        _logger.setLevel(logging.WARNING)
        for plugin in preLoadedPlugins:
            _pluginLoaded( plugin )
        _logger.setLevel(level)
            
_installCallbacks()





