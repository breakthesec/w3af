'''
halberd.py

Copyright 2006 Andres Riancho

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

import core.controllers.outputManager as om

from core.controllers.basePlugin.baseInfrastructurePlugin import baseInfrastructurePlugin
from core.controllers.w3afException import w3afRunOnce
from core.controllers.misc.decorators import runonce

import core.data.kb.knowledgeBase as kb
import core.data.kb.info as infokb


# halberd imports!
# done this way so the user can run this plugin without having to install halberd !
# Also, the halberd version i'm using, has some minimal changes.
import sys, os.path
halberd_dir = 'plugins' + os.path.sep + 'infrastructure' + os.path.sep + 'oHalberd'

# This insert in the first position of the path is to "step over" an installation of halberd.
sys.path.insert( 0, halberd_dir )

# I do it this way and not with a "from plugins.infrastructure.oHalberd.Halberd import logger" because
# inside the original hablerd they are crossed imports and stuff that I don't want to modify.
import Halberd.shell as halberd_shell
import Halberd.logger as halberd_logger
import Halberd.ScanTask as halberd_scan_task
import Halberd.version as halberd_shell_version
import Halberd.clues.analysis as halberd_analysis

class halberd(baseInfrastructurePlugin):
    '''
    Identify if the remote server has HTTP load balancers.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    '''
    This plugin is a wrapper for  Juan M. Bello Rivas <jmbr |at| superadditive.com> halberd.
    '''

    def __init__(self):
        baseInfrastructurePlugin.__init__(self)

    @runonce(exc_class=w3afRunOnce)
    def discover(self, fuzzableRequest ):
        '''
        It calls the "main" from halberd and writes the results to the kb.
        
        @parameter fuzzableRequest: A fuzzableRequest instance that contains
                                    (among other things) the URL to test.
        '''
        msg = 'halberd plugin is starting. Original halberd author: Juan M. Bello Rivas ;'
        msg += ' http://halberd.superadditive.com/'
        om.out.information( msg )
        
        self._main( fuzzableRequest.getURL().baseUrl().url_string )

    def _main( self, url ):
        '''
        This was taken from the original halberd, 'script/halberd' .
        '''
        scantask = halberd_scan_task.ScanTask()

        scantask.scantime = halberd_scan_task.default_scantime
        scantask.parallelism = halberd_scan_task.default_parallelism
        scantask.verbose = False
        scantask.debug = False
        scantask.conf_file = halberd_scan_task.default_conf_file
        scantask.cluefile = ''
        scantask.save = ''
        scantask.output = ''
        
        halberd_logger.setError()
        scantask.readConf()
        
        # UniScan
        scantask.url = url
        scantask.addr = ''
        scanner = halberd_shell.UniScanStrategy
        
        try:
            s = scanner(scantask)
        except halberd_shell.ScanError, msg:
            om.out.error('*** %s ***' % msg )
        else:
            #
            #       The scantask initialization worked, we can start the actual scan!
            #
            try:
                result = s.execute()
                # result should be: <Halberd.ScanTask.ScanTask instance at 0x85df8ec>                
            except halberd_shell.ScanError, msg:
                om.out.debug('*** %s ***' % msg )
            except KeyboardInterrupt:
                raise
            else:
                self._report( result )

    def _report( self, scantask):
        """
        Displays detailed report information to the user and save the data to the kb.
        """
        if len(scantask.analyzed) == 1:
            om.out.information('The site: ' + scantask.url + " doesn't seem to have a HTTP load balancer configuration.")
        else:
            clues = scantask.analyzed
            hits = halberd_analysis.hits(clues)
        
            # xxx This could be passed by the caller in order to avoid recomputation in
            # case the clues needed a re-analysis.
            diff_fields = halberd_analysis.diff_fields(clues)
        
            om.out.information('=' * 70 )
            om.out.information('%s' % scantask.url, newLine=False)
            if scantask.addr:
                om.out.information(' (%s)' % scantask.addr, newLine=False)
            om.out.information(': %d real server(s)'  % len(clues) )
            om.out.information('=' * 70 )
        
            for num, clue in enumerate(clues):
                assert hits > 0
                info = clue.info
        
                om.out.information('')
                om.out.information('server %d: %s' % (num + 1, info['server'].lstrip()))
                om.out.information('-' * 70 + '\n')
                
                # This is added so other w3af plugins can read the halberd results.
                # If needed by other plugins, I could fill up the info object with more
                # data about the different headers, time, etc...
                i = infokb.info()
                i['server'] = info['server'].lstrip()
                i['serverNumber'] = num +1
                kb.kb.append( self, 'halberd', i )
                
                om.out.information('difference: %d seconds' % clue.diff)
        
                om.out.information('successful requests: %d hits (%.2f%%)' \
                          % (clue.getCount(), clue.getCount() * 100 / float(hits)))
        
                if info['contloc']:
                    om.out.information('content-location: %s' % info['contloc'].lstrip())
        
                if len(info['cookies']) > 0:
                    om.out.information('cookie(s):')
                for cookie in info['cookies']:
                    om.out.information('  %s' % cookie.lstrip())
        
                om.out.information('header fingerprint: %s' % info['digest'])
        
                different = [(field, value) for field, value in clue.headers \
                                            if field in diff_fields]
                if different:
                    om.out.information('different headers:')
                    idx = 1
                    for field, value in different:
                        om.out.information('  %d. %s:%s' % (idx, field, value))
                        idx += 1
        
                if scantask.debug:
                    import pprint
                    import StringIO
                    tmp = StringIO.StringIO()
                    om.out.information('headers:')
                    pprint.pprint(clue.headers, stream=tmp, indent=2)
                    om.out.information( tmp )
                    
            om.out.information('\n')
    
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin tries to find if an HTTP Load balancer is present.
        '''