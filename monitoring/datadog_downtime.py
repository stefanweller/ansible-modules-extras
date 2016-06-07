#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Stefan Weller <stefan.weller@asideas.de>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.    If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: datadog_downtime
short_description: Set/update/cancel active or future downtimes (with optional recurrence) of DataDog monitors by a scope.
description:
- "Allows to set/update/cancel active or future downtimes (with optional recurrence) of DataDog monitors (www.datadoghq.com) by providing a scope."
- "Uses U(http://docs.datadoghq.com/api/#monitors) API."
- "Uses datadogpy U(https://github.com/DataDog/datadogpy) library -> pip install datadog."
- "Currently this module has no check mode."
version_added: "2.2.0"
author: 'Stefan Weller <stefan.weller@asideas.de>, Github: stefanweller'
requirements: [datadog]
options:
    I(api_key):
        description: ["DataDog API key."]
        required: true
        default: null
    I(app_key):
        description: ["DataDog application key."]
        required: true
        default: null
    I(state):
        description: ["Designated state of the downtime. Currently 'present', 'updated' and 'absent' are supported."]
        required: true
        default: null
    I(scope):
        description: ["Scope of the monitors to set/update/cancel downtimes (e.g.: 'host:myhost,myapp')."]
        required: True
        default: null
    I(start):
        description: ["POSIX timestamp of downtime start time. Current time will be used if not given. Will be ignored when updating C(active_only=True) downtimes."]
        required: False
        default: null
    I(end):
        description: ["POSIX timestamp of downtime end time. Downtimes will run forever if no end given."]
        required: False
        default: null
    I(message):
        description: ["A downtime info text."]
        required: False
        default: null
    I(active_only):
        description: ["A C(True)/C(False) flag indicating that only active downtimes are affected or, if C(False), future ones too."]
        required: False
        default: null
    I(recurrence):
        description: ["A JSON object describing the recurence of a downtime. See U(http://docs.datadoghq.com/api/) -> Downtimes for a description of the object."]
        required: False
        default: null
'''

EXAMPLES = '''
- name: set Datadog downtime with scope, immediate start and no end
  datadog_downtime:
    api_key: apikeyapikeyapikeyapikeyapikeyapikey
    app_key: appkeyappkeyappkeyappkeyappkeyappkeyappkey
    state: present
    scope: 'host:my.scope'

- name: set Datadog downtime with scope, future start and no end
  datadog_downtime:
    api_key: apikeyapikeyapikeyapikeyapikeyapikey
    app_key: appkeyappkeyappkeyappkeyappkeyappkeyappkey
    state: present
    scope: 'host:my.scope'
    start: 1670803200

- name: set Datadog downtime with scope, future start and defined end
  datadog_downtime:
    api_key: apikeyapikeyapikeyapikeyapikeyapikey
    app_key: appkeyappkeyappkeyappkeyappkeyappkeyappkey
    state: present
    scope: 'host:my.scope'
    start: 1670803200
    end: 1986422400

- name: set Datadog downtime with scope, future start, defined end and message
  datadog_downtime:
    api_key: apikeyapikeyapikeyapikeyapikeyapikey
    app_key: appkeyappkeyappkeyappkeyappkeyappkeyappkey
    state: present
    scope: 'host:my.scope'
    start: 1670803200
    end: 1986422400
    message: 'This is a test downtime'

- name: set Datadog downtime with scope, future start, defined end, message and recurrence
  datadog_downtime:
    api_key: apikeyapikeyapikeyapikeyapikeyapikey
    app_key: appkeyappkeyappkeyappkeyappkeyappkeyappkey
    state: present
    scope: 'host:my.scope'
    start: 1670803200
    end: 1986422400
    message: 'This is a recurring test downtime'
    recurrence: "{\"type\":\"days\",\"period\":\"2\"}"

- name: update Datadog downtimes that are currently active by scope ('start' will be skipped if given)
  datadog_downtime:
    api_key: apikeyapikeyapikeyapikeyapikeyapikey
    app_key: appkeyappkeyappkeyappkeyappkeyappkeyappkey
    state: updated
    scope: 'host:my.scope'
    end: 2362435200
    message: 'This is a very long downtime'
    active_only: True

- name: cancel all Datadog downtimes matching given scope
  datadog_downtime:
    api_key: apikeyapikeyapikeyapikeyapikeyapikey
    app_key: appkeyappkeyappkeyappkeyappkeyappkeyappkey
    state: absent
    scope: 'host:my.scope'
'''

RETURN = '''
'''

import sys
import json

# Import Datadog
try:
    from datadog import initialize, api
    HAS_DATADOG = True
except:
    HAS_DATADOG = False

def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(required=True),
            app_key=dict(required=True),
            state=dict(required=True, choices=['present', 'updated', 'absent']),
            scope=dict(required=True, type='list'),
            start=dict(required=False),
            end=dict(required=False),
            message=dict(required=False),
            active_only=dict(required=False, type='bool'),
            recurrence=dict(required=False),
        )
    )

    # prepare Datadog
    if not HAS_DATADOG:
        module.fail_json(msg='datadogpy required for this module')

    options = {
        'api_key': module.params['api_key'],
        'app_key': module.params['app_key']
    }

    initialize(**options)
    downtimes = find_downtimes_by_scope(module)

    if module.params['state'] == 'present':
        set_downtime(module, downtimes)

    elif module.params['state'] == 'updated':
        update_downtimes(module, downtimes)

    elif module.params['state'] == 'absent':
        cancel_downtimes(module, downtimes)

def set_downtime(module, downtimes):
    scope = module.params['scope']
    start = module.params['start']
    end = module.params['end']
    message = module.params['message']
    recurrence = module.params['recurrence']
    loaded_recurrence = None

    for downtime in downtimes:
        # all scope tags must match - also the number of tags
        if len(set(scope) - set(downtime['scope'])) == 0 and int(start) == downtime['start'] and message == downtime['message'] and recurrence == downtime['recurrence']:
            #if end is define, also check it
            if end:
                if int(end) == downtime['end']:
                    module.exit_json(changed=False, msg="Matching downtime already present (end defined)." % scope)
            #if no end is defined, all criteria already match
            else:
                module.exit_json(changed=False, msg="Matching downtime already present (no end defined)." % scope)

    # set current time for start if no start given
    if not start:
        start = start = int(time.time())

    if recurrence:
        loaded_recurrence = json.loads(recurrence)

    result = api.Downtime.create(scope=scope, start=start, end=end, message=message, recurrence=loaded_recurrence)
    if result and 'errors' in result:
        module.fail_json(msg="Error while setting downtime: %s" % result['errors'])

    module.exit_json(changed=True, msg="Downtime for scope '%s' set." % scope)

def update_downtimes(module, downtimes):
    scope = module.params['scope']
    start = module.params['start']
    end = module.params['end']
    message = module.params['message']
    recurrence = module.params['recurrence']
    loaded_recurrence = None

    current_time = int(time.time())
    updated_downtimes = 0

    if recurrence:
        loaded_recurrence = json.loads(recurrence)

    for downtime in downtimes:
        # skip running downtimes when start time is given (change not allowed)
        if start and downtime['start'] < current_time:
            continue

        result = api.Downtime.update(downtime['id'], start=start, end=end, message=message, recurrence=loaded_recurrence)
        if result and 'errors' in result:
            module.fail_json(msg="Error while updating downtime: %s" % result['errors'])

        updated_downtimes += 1

    module.exit_json(changed=True, msg="Downtime/s for scope '%s' updated (found %s, updated %s)." % (scope, len(downtimes), updated_downtimes))

def cancel_downtimes(module, downtimes):
    scope = module.params['scope']
    for downtime in downtimes:
        result = api.Downtime.delete(downtime['id'])
        if result and 'errors' in result:
            module.fail_json(msg="Error while canceling downtime: %s" % result['errors'])

    module.exit_json(changed=True, msg="Downtime/s for scope '%s' canceled (found %s)." % (scope, len(downtimes)))

def find_downtimes_by_scope(module):
    search_scope = module.params['scope']
    active_only = module.params['active_only']

    all_downtimes = api.Downtime.get_all()
    if all_downtimes and 'errors' in all_downtimes:
        module.fail_json(msg="Error while retrieving downtimes: %s" % all_downtimes['errors'])

    matching_downtimes = []

    for downtime in all_downtimes:

        # canceled downtimes are not relevant
        if downtime['canceled']:
            continue

        # # only scan active downtimes when set so
        if not downtime['active'] and active_only:
            continue

        # all scope tags must match - also the number of tags
        if len(set(search_scope) - set(downtime['scope'])) == 0:
            matching_downtimes.append(downtime)

    if not matching_downtimes:
        module.fail_json(msg="No downtime matching scope '%s' found." % search_scope)

    return matching_downtimes

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()
