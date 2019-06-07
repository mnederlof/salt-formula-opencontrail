#!/usr/bin/python
# Copyright 2018 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import subprocess
import time

# Import Salt Libs
import salt.utils.http


MODULE_NAME = 'contrail_health'
LOG = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load this module if contrail-status or doctrail utility
    (in case of containerized contrail version) is available.
    '''
    if _is_cmd_available('contrail-status') or _is_cmd_available('doctrail'):
        return MODULE_NAME
    return False


def _is_cmd_available(cmd_name):
    try:
        with open(os.devnull) as devnull:
            subprocess.Popen(
                [cmd_name], stdout=devnull, stderr=devnull
            ).communicate()
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            return False
    return True


def get_services_status():
    cs_out = None

    if _is_cmd_available('contrail-status'):
        LOG.info('Trying to get status of contrail services '
                 'using contrail-status utility on host ...')
        try:
            cs_out = str(subprocess.check_output(['contrail-status']))
        except subprocess.CalledProcessError as e:
            LOG.warn('Status of contrail services cannot be checked '
                     'by contrail-status utility from host')
    if cs_out is None and _is_cmd_available('doctrail'):
        LOG.info('Trying to get status of contrail services inside containers '
                 'using doctrail utility ...')
        try:
            cs_out = str(subprocess.check_output(
                ['doctrail', 'all', 'contrail-status'])
            )
        except subprocess.CalledProcessError as e:
            LOG.warn('Status of contrail services inside containers cannot '
                     'be checked by contrail-status utility via doctrail cmd')

    status_map = {}

    if cs_out:
        for line in cs_out.split('\n'):
            line_list = line.split()
            if (not line.startswith("==") and "FOR NODE" not in line and
                    len(line_list) >= 2):
                status_map[line_list[0].split(":")[0]] = line_list[1]
    else:
        LOG.error('Status of contrail services cannot be checked '
                  'by {0} module.'.format(MODULE_NAME))

    return status_map

'''
    Check status of Contail API service on Virtual IP which is defined by pillars.

    CLI Example:

    .. code-block:: bash

        salt 'ntw01*' contrail_health.get_api_status [wait_for=300] \\
                [tries=20]

    wait_for
        Number of seconds how long to wait for API response.

    tries
        Number of tries. After each unsuccessful try will sleep for \\
        (wait_for/tries).
'''


def get_api_status(wait_for=180, tries=20):
    api_host = __pillar__['opencontrail'].get('client', {}).get('api', {}).\
        get('host', {})
    api_port = __pillar__['opencontrail']['client']['api']['port']
    use_ssl = __pillar__['opencontrail'].get('client', {}).get('api', {}).\
        get('use_ssl', {})
    api_protocol = 'https' if use_ssl is True else 'http'

    for t in range(0, tries):
        try:
            data = salt.utils.http.query(
                "{0}://{1}:{2}".format(api_protocol, api_host, api_port),
                backend='requests', status=True
            )
            if data['status'] == 200:
                return True
        except Exception as e:
            LOG.error(e.message)
        time.sleep(int(wait_for / tries))

    return False
