'''
plugins.py

Copyright 2008 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import copy
import sys
import textwrap

import core.controllers.outputManager as om

from core.ui.console.menu import menu
from core.ui.console.config import configMenu
from core.ui.console.util import suggest
from core.controllers.w3afException import w3afException


class pluginsMenu(menu):
    '''
    Menu for the list of plugins.
    @author Alexander Berezhnoy (alexander.berezhnoy |at| gmail.com)

    '''

    def __init__(self, name, console, w3af, parent):
        menu.__init__(self, name, console, w3af, parent)
        types = w3af.plugins.get_plugin_types()        
        self._children = {}

        self._loadHelp('plugins')

        for t in types:
            self.addChild(t, pluginsTypeMenu)
#            self._help.addHelpEntry(t, "List %s plugins" % t, 'plugins')
        self.__loadPluginTypesHelp(types)

#        self._help.addHelpEntry('list', "List plugins by their type", 'commands')
#        self._help.addHelpEntry('config', "Config plugins (same as <type> config>)", 'commands')
          
    def __loadPluginTypesHelp(self, types): 
        vars = {}
        for t in types:
            pList = self._w3af.plugins.get_plugin_list(t)
            (p1, p2) = len(pList)>1 and (pList[0], pList[1]) \
                or ('plugin1', 'plugin2')
            vars['PLUGIN1'], vars['PLUGIN2'] = p1, p2
            vars['TYPE'] = t
            
            self._loadHelp('plugin_type', vars=vars)
    
    def getChildren(self):
        return self._children

    def execute(self, tokens):
        '''
        This is a trick to make this console back-compatible.
        For example, command 'audit' means 'show all audit plugins', 
        while command 'audit xss' means 'enable xss plugin'.
        At the same time, to show only enabled audit plugin, the command
        'list audit enabled' has to be used. 
        That's an inconsistency, which needs a resolution.
        '''
        if len(tokens) == 1 and tokens[0] in self._children:
            return self._cmd_list(tokens)
        return menu.execute(self, tokens)


#    def _cmd_config(self, params):
#        try:
#            type = params[0]
#            subMenu = self._children[type]
#        except:
#            self._cmd_help(['config'])
#        else:
#            subMenu._list(params[1:])


    def _cmd_list(self, params):
        try:
            type = params[0]
            subMenu = self._children[type]
        except:
            self._cmd_help(['list'])
        else:
            subMenu._list(params[1:])

        return None

    def _para_list(self, params, part):
        l = len(params)
        if l==0:
            return suggest(self._children.keys(), part)
        if l==1:
            return suggest(['all', 'enabled', 'disabled'], part)
        return []

        
class pluginsTypeMenu(menu):
    '''
        Common menu for all types of plugins. 
        The type of plugins is defined by the menu's own name.
    '''
    def __init__(self, name, console, w3af, parent):
        menu.__init__(self, name, console, w3af, parent)
        plugins = w3af.plugins.get_plugin_list(name)
        self._plugins = {} # name to number of options
        for p in plugins:
            try:
                options = self._w3af.plugins.get_plugin_inst(self._name, p).get_options()
            except Exception, e:
                om.out.error('Error while reading plugin options: "%s"' % e)                
                sys.exit(-8)
            else:
                self._plugins[p] = len(options)
        self._configs = {}
      

    def suggestCommands(self, part, *skip):
        return suggest(self._plugins.keys() + ['all'], part.lstrip('!')) + \
            suggest(self.getCommands(), part)

    def suggestParams(self, command, params, part):
        if command in self.getCommands():
            return menu.suggestParams(self, command, params, part)
        
        alreadySel =[s.lstrip('!') for s in [command] + params]
        
        plugins = self._plugins.keys()
        return suggest(plugins, part.lstrip('!'), alreadySel)


    def getCommands(self):
        return ['config', 'desc']

    def execute(self, tokens):
        if len(tokens)>0:
            command, params = tokens[0], tokens[1:]
            #print "command: " + command + "; " + str(self.getCommands())
            if command in self.getCommands():
                return menu.execute(self, tokens)
            else:
                self._enablePlugins(','.join(tokens).split(','))
        else:
            return self

    def _enablePlugins(self, list):
        enabled = copy.copy(self._w3af.plugins.get_enabled_plugins(self._name))
        
        for plugin in list:
            if plugin=='':
                continue 
            if plugin.startswith('!'):
                disabling = True
                plugin = plugin.lstrip('!')
            else:
                disabling = False

            if plugin!='all' and plugin not in self._plugins:
                raise w3afException("Unknown plugin: '%s'" % plugin)

            if disabling:
                if plugin == 'all':
                    enabled = []
                elif plugin in enabled:
                    enabled.remove(plugin)
            elif plugin == 'all':
                enabled = self._plugins.keys()
            elif plugin not in enabled:
                enabled.append(plugin)
        
        # Note: Disabling this check after talking with olle. Only advanced users are going to
        # remove the console output plugin, and if someone else does, he will realize that he
        # fucked up ;)
        #
        #if self._name == 'output' and 'console' not in enabled:
        #    om.out.console("Warning: You can't disable the console output plugin in the console UI")
        #    enabled.append('console')
        #
        # What I'm going to do, is to let the user know that he's going into blind mode:
        #
        if self._name == 'output' and 'console' not in enabled and len(enabled) == 0:
            msg = "Warning: You disabled the console output plugin. If you start a new scan, the"
            msg += ' discovered vulnerabilities won\'t be printed to the console, we advise you'
            msg += ' to enable at least one output plugin in order to be able to actually see'
            msg += ' the scan output.'
            om.out.console( msg )
            
        self._w3af.plugins.set_plugins(enabled, self._name)

    def _cmd_desc(self, params):
        
        if len(params) == 0:
            raise w3afException("Plugin name is required")

        plugin_name = params[0]
        if plugin_name not in self._plugins:
            raise w3afException("Unknown plugin: '%s'" % plugin_name)

        plugin = self._w3af.plugins.get_plugin_inst(self._name, plugin_name)
        long_desc = plugin.get_long_desc()
        long_desc = textwrap.dedent(long_desc)
        om.out.console( long_desc )


    def _para_desc(self, params, part):
        if len(params)>0:
            return []

        return suggest(self._plugins.keys(), part)

        
    def _list(self, params):
        #print 'list : ' + str(params)
        filter = len(params)>0 and params[0] or 'all'

        all = self._plugins.keys()
        enabled = self._w3af.plugins.get_enabled_plugins(self._name)

        if filter == 'all':
            list = all
        elif filter == 'enabled':
            list = enabled
        elif filter == 'disabled':
            list = [p for p in all if p not in enabled]
        else:
            list = []
                       

        if len(list) == 0:
            om.out.console('No plugins have status ' + filter)
            return


        list.sort()
        table = [['Plugin name', 'Status', 'Conf', 'Description']]

        for plugin_name in list:
            row = []
            plugin = self._w3af.plugins.get_plugin_inst(self._name, plugin_name)
    
            optCount = self._plugins[plugin_name]
            row.append(plugin_name)
            status = plugin_name in enabled and 'Enabled' or ''
            row.append(status)
            optInfo = optCount>0 and 'Yes' or ''
            row.append(optInfo)
            row.append(str(plugin.getDesc()))

            table.append(row)
        self._console.drawTable(table, True)

       
    def _cmd_config(self, params):
        
        if len(params) ==0:
            raise w3afException("Plugin name is required")

        name = params[0]

        if name not in self._plugins:
            raise w3afException("Unknown plugin: '%s'" %name)

        if self._configs.has_key(name):
            config = self._configs[name]
        else:
            config = configMenu(name, self._console, self._w3af, self, 
                                self._w3af.plugins.get_plugin_inst(self._name, params[0]))
            self._configs[name] = config

        return config

    def _para_config(self, params, part):
        if len(params) > 0:
            return []

        return suggest([p for p in self._plugins.keys() \
            if self._plugins[p] > 0], part)
                
    def _para_list(self, params, part=''):
        if len(params)==0:
            return suggest(['enabled', 'all', 'disabled'], part)
        return []

