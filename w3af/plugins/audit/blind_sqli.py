"""
blind_sqli.py

Copyright 2006 Andres Riancho

This file is part of w3af, http://w3af.org/ .

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

"""
import w3af.core.data.kb.knowledge_base as kb

from w3af.core.controllers.plugins.audit_plugin import AuditPlugin
from w3af.core.controllers.sql_tools.blind_sqli_response_diff import \
                                BlindSqliResponseDiff
from w3af.core.controllers.sql_tools.blind_sqli_time_delay import \
                                blind_sqli_time_delay

from w3af.core.data.options.opt_factory import opt_factory
from w3af.core.data.options.option_list import OptionList
from w3af.core.data.fuzzer.fuzzer import create_mutants


class blind_sqli(AuditPlugin):
    """
    Identify blind SQL injection vulnerabilities.

    :author: Andres Riancho (andres.riancho@gmail.com)
    """

    def __init__(self):
        AuditPlugin.__init__(self)

        # User configured variables
        self._eq_limit = 0.9

    def audit(self, freq, orig_response):
        """
        Tests an URL for blind SQL injection vulnerabilities.

        :param freq: A FuzzableRequest
        """
        #
        #    Setup blind SQL injection detector objects
        #
        bsqli_resp_diff = BlindSqliResponseDiff(self._uri_opener)
        bsqli_resp_diff.set_eq_limit(self._eq_limit)

        bsqli_time_delay = blind_sqli_time_delay(self._uri_opener)

        method_list = [bsqli_resp_diff, bsqli_time_delay]

        #
        #    Use the objects to identify the vulnerabilities
        #
        fake_mutants = create_mutants(freq, ['', ])

        for mutant in fake_mutants:

            if self._has_sql_injection(mutant):
                #
                # If sqli.py was enabled and already detected a vulnerability
                # in this parameter, then it makes no sense to test it again
                # and report a duplicate to the user
                #
                continue

            for method in method_list:
                found_vuln = method.is_injectable(mutant)

                if found_vuln is not None:
                    self.kb_append_uniq(self, 'blind_sqli', found_vuln)
                    break

    def _has_sql_injection(self, mutant):
        """
        :return: True if there IS a reported SQL injection for this
                 URL/parameter combination.
        """
        sql_injection_list = kb.kb.get('sqli', 'sqli')

        for sql_injection in sql_injection_list:
            if sql_injection.get_url() == mutant.get_url() and \
            sql_injection.get_token_name() == mutant.get_token_name():
                return True

        return False

    def get_options(self):
        """
        :return: A list of option objects for this plugin.
        """
        opt_list = OptionList()

        desc = 'String equal ratio (0.0 to 1.0)'
        h = 'Two pages are considered equal if they match in more'\
            ' than eq_limit.'
        opt = opt_factory('eq_limit', self._eq_limit, desc, 'float', help=h)

        opt_list.add(opt)

        return opt_list

    def set_options(self, options_list):
        """
        This method sets all the options that are configured using the user
        interface generated by the framework using the result of get_options().

        :param options_list: A dictionary with the options for the plugin.
        :return: No value is returned.
        """
        self._eq_limit = options_list['eq_limit'].get_value()

    def get_long_desc(self):
        """
        :return: A DETAILED description of the plugin functions and features.
        """
        return """
        This plugin finds blind SQL injections using two techniques: time delays
        and true/false response comparison.

        Only one configurable parameters exists:
            - eq_limit
        """
