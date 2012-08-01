'''
strange_headers.py

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
import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info

from core.controllers.basePlugin.baseGrepPlugin import baseGrepPlugin
from core.controllers.misc.groupbyMinKey import groupbyMinKey


class strange_headers(baseGrepPlugin):
    '''
    Grep headers for uncommon headers sent in HTTP responses.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    # Remember that this headers are only the ones SENT BY THE SERVER TO THE
    # CLIENT. Headers must be uppercase in order to compare them
    COMMON_HEADERS = set([
                "ACCEPT-RANGES",
                "AGE",
                "ALLOW",
                "CONNECTION",
                "CONTENT-ENCODING",        
                "CONTENT-LENGTH",
                "CONTENT-TYPE",
                "CONTENT-LANGUAGE",
                "CONTENT-LOCATION",
                "CACHE-CONTROL",
                "DATE",
                "EXPIRES",
                "ETAG",
                "KEEP-ALIVE",
                "LAST-MODIFIED",
                "LOCATION",
                "PUBLIC",
                "PRAGMA",
                "PROXY-CONNECTION",
                "SET-COOKIE",    
                "SERVER",
                "STRICT-TRANSPORT-SECURITY",        
                "TRANSFER-ENCODING",
                "VIA",        
                "VARY",
                "WWW-AUTHENTICATE",
                "X-FRAME-OPTIONS", 
                "X-CONTENT-TYPE-OPTIONS",         
                "X-POWERED-BY",
                "X-ASPNET-VERSION",
                "X-CACHE",
                "X-UA-COMPATIBLE",
                "X-PAD",
                "X-XSS-Protection"]
                      )
                      
    def __init__(self):
        baseGrepPlugin.__init__(self)

    def grep(self, request, response):
        '''
        Plugin entry point.
        
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None, all results are saved in the kb.
        '''

        # Check if the header names are common or not
        for header_name in response.getHeaders().keys():
            if header_name.upper() not in self.COMMON_HEADERS:
                
                # Check if the kb already has a info object with this code:
                strange_header_infos = kb.kb.getData('strange_headers', 'strange_headers')
                
                for info_obj in strange_header_infos:
                    if info_obj['header_name'] == header_name:
                        # Work with the "old" info object:
                        id_list = info_obj.getId()
                        id_list.append( response.id )
                        info_obj.setId( id_list )
                        break
                else:
                    # Create a new info object from scratch and save it to the kb:
                    i = info.info()
                    i.setPluginName(self.getName())
                    i.setName('Strange header')
                    i.setURL( response.getURL() )
                    i.setId( response.id )
                    msg = 'The remote web server sent the HTTP header: "' + header_name
                    msg += '" with value: "' + response.getHeaders()[header_name] + '".'
                    i.setDesc( msg )
                    i['header_name'] = header_name
                    hvalue = response.getHeaders()[header_name]
                    i['header_value'] = hvalue
                    i.addToHighlight( hvalue, header_name )
                    kb.kb.append( self , 'strange_headers' , i )


        # Now check for protocol anomalies
        self._content_location_not_300(request, response)

    def _content_location_not_300( self, request, response):
        '''
        Check if the response has a content-location header and the response code
        is not in the 300 range.
        
        @return: None, all results are saved in the kb.
        '''
        if 'content-location' in response.getLowerCaseHeaders() \
        and response.getCode() not in xrange(300,310):
            i = info.info()
            i.setPluginName(self.getName())
            i.setName('Content-Location HTTP header anomaly')
            i.setURL( response.getURL() )
            i.setId( response.id )
            msg = 'The URL: "' +  i.getURL() + '" sent the HTTP header: "content-location"' 
            msg += ' with value: "' + response.getLowerCaseHeaders()['content-location']
            msg += '" in an HTTP response with code ' + str(response.getCode()) + ' which is'
            msg += ' a violation to the RFC.'
            i.setDesc( msg )
            i.addToHighlight( 'content-location' )
            kb.kb.append( self , 'anomaly' , i )

    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        headers = kb.kb.getData( 'strange_headers', 'strange_headers' )
        # This is how I saved the data:
        #    i['header_name'] = header_name
        #    i['header_value'] = response.getHeaders()[header_name]
        
        # Group correctly
        tmp = []
        for i in headers:
            tmp.append( (i['header_name'], i.getURL() ) )
        
        # And don't print duplicates
        tmp = list(set(tmp))
        
        resDict, itemIndex = groupbyMinKey( tmp )
        if itemIndex == 0:
            # Grouped by header_name
            msg = 'The header: "%s" was sent by these URLs:'
        else:
            # Grouped by URL
            msg = 'The URL: "%s" sent these strange headers:'
            
        for k in resDict:
            om.out.information(msg % k)
            for i in resDict[k]:
                om.out.information('- ' + i )
            
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin greps all headers for non-common headers. This could be useful
        to identify special modules and features added to the server.
        '''