#!/usr/bin/python
# Copyright 2017 Mirantis, Inc.
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

from vnc_api.vnc_api import *
from vnc_api.gen.resource_xsd import *
from cfgm_common.exceptions import *
from cfgm_common.rbaclib import *
import cfgm_common

from netaddr import IPNetwork
from vnc_api.vnc_api import PhysicalRouter, PhysicalInterface, LogicalInterface
from vnc_api.vnc_api import EncapsulationPrioritiesType
from vnc_api.vnc_api import VirtualMachineInterface, MacAddressesType
from vnc_api.vnc_api import ServiceApplianceSet, KeyValuePairs, KeyValuePair

try:
    from vnc_api import vnc_api
    from vnc_api.vnc_api import LinklocalServiceEntryType, \
        LinklocalServicesTypes, GlobalVrouterConfig, GlobalSystemConfig
    from vnc_api.gen.resource_client import VirtualRouter, AnalyticsNode, \
        ConfigNode, DatabaseNode, BgpRouter, VirtualNetwork, FloatingIpPool
    from vnc_api.gen.resource_xsd import AddressFamilies, BgpSessionAttributes, \
        BgpSession, BgpPeeringAttributes, BgpRouterParams, AuthenticationData, \
        AuthenticationKeyItem, VirtualNetworkType, IpamSubnetType, SubnetType, \
        VnSubnetsType, RouteTargetList, ShareType

    HAS_CONTRAIL = True
except ImportError:
    HAS_CONTRAIL = False


try:
    from vnc_api.gen.resource_xsd import GracefulRestartParametersType
    HAS_OLD = False
except ImportError:
    HAS_OLD = True

__opts__ = {}


def __virtual__():
    '''
    Only load this module if vnc_api library is installed.
    '''
    if HAS_CONTRAIL:
        return 'contrail'

    return False


def _auth(**kwargs):
    '''
    Set up Contrail API credentials.
    '''
    user = kwargs.get('user')
    password = kwargs.get('password')
    tenant_name = kwargs.get('project')
    api_host = kwargs.get('api_server_ip')
    api_port = kwargs.get('api_server_port')
    api_base_url = kwargs.get('api_base_url')
    use_ssl = kwargs.get('api_server_use_ssl')
    auth_host = kwargs.get('auth_host_ip')
    vnc_lib = vnc_api.VncApi(user, password, tenant_name,
                             api_host, api_port, api_base_url, wait_for_connect=False,
                             api_server_use_ssl=use_ssl, auth_host=auth_host)

    return vnc_lib


def _get_config(vnc_client, global_system_config='default-global-system-config'):
    try:
        gsc_obj = vnc_client.global_system_config_read(id=global_system_config)
    except vnc_api.NoIdError:
        gsc_obj = vnc_client.global_system_config_read(fq_name_str=global_system_config)
    except:
        gsc_obj = None

    return gsc_obj


def _get_rt_inst_obj(vnc_client):
    # TODO pick fqname hardcode from common
    rt_inst_obj = vnc_client.routing_instance_read(
        fq_name=['default-domain', 'default-project',
                 'ip-fabric', '__default__'])

    return rt_inst_obj


def _get_fq_name(vnc_client, resource_name, project_name, domain='default-domain'):
    res = [domain]
    if project_name:
        res.append(project_name)
    if resource_name:
        res.append(resource_name)
    return res


def _get_project_obj(vnc_client, name, domain='default-domain'):
    return vnc_client.project_read(fq_name=[domain, name])


def _get_ip(ip_w_pfx):
    return str(IPNetwork(ip_w_pfx).ip)


def virtual_router_list(**kwargs):
    '''
    Return a list of all Contrail virtual routers

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_router_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    vrouter_objs = vnc_client._objects_list('virtual-router', detail=True)
    for vrouter_obj in vrouter_objs:
        ret[vrouter_obj.name] = {
            'ip_address': vrouter_obj.virtual_router_ip_address,
            'dpdk_enabled': vrouter_obj.virtual_router_dpdk_enabled,
            'uuid': vrouter_obj.uuid

        }
    return ret


def virtual_router_get(name, **kwargs):
    '''
    Return a specific Contrail virtual router

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_router_get cmp01
    '''
    ret = {}
    vrouter_objs = virtual_router_list(**kwargs)
    if name in vrouter_objs:
        ret[name] = vrouter_objs.get(name)
    if len(ret) == 0:
        return {'Error': 'Error in retrieving virtual router.'}
    return ret


def virtual_router_create(name, ip_address, router_type=None, dpdk_enabled=False, **kwargs):
    '''
    Create specific Contrail virtual router

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_router_create cmp02 10.10.10.102
        router_types:
        - tor-agent
        - tor-service-node
        - embedded
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    vrouter_objs = virtual_router_list(**kwargs)
    router_types = ['tor-agent', 'tor-service-node', 'embedded']
    if router_type not in router_types:
        router_type = None
    if name in vrouter_objs:
        vrouter = virtual_router_get(name, **kwargs)
        vrouter_obj = vnc_client._object_read('virtual-router', id=vrouter[name]['uuid'])
        changes = {}
        if vrouter_obj.get_virtual_router_ip_address() != ip_address:
            changes['ip_address'] = {'from': vrouter_obj.get_virtual_router_ip_address(), "to": ip_address}
            vrouter_obj.set_virtual_router_ip_address(ip_address)
        if vrouter_obj.get_virtual_router_type() != router_type:
            changes['router_type'] = {"from": vrouter_obj.get_virtual_router_type(), "to": router_type}
            vrouter_obj.set_virtual_router_type(router_type)
        if vrouter_obj.get_virtual_router_dpdk_enabled() != dpdk_enabled:
            changes['dpdk_enabled'] = {"from": vrouter_obj.get_virtual_router_dpdk_enabled(), "to": dpdk_enabled}
            vrouter_obj.set_virtual_router_dpdk_enabled(dpdk_enabled)
        if len(changes) != 0:
            if __opts__['test']:
                ret['result'] = None
                ret['comment'] = "Virtual router " + name + " will be updated"
            else:
                ret['comment'] = "VirtualRouter " + name + " has been updated"
                ret['changes'] = changes
                vnc_client.virtual_router_update(vrouter_obj)
            return ret
        ret['comment'] = 'Virtual router ' + name + ' already exists and is updated'
        return ret
    else:
        vrouter_obj = VirtualRouter(
            name, gsc_obj,
            virtual_router_ip_address=ip_address,
            virtual_router_type=router_type)
        vrouter_obj.set_virtual_router_dpdk_enabled(dpdk_enabled)
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "VirtualRouter " + name + " will be created"
        else:
            vnc_client.virtual_router_create(vrouter_obj)
            ret['comment'] = "VirtualRouter " + name + " has been created"
            ret['changes'] = {'VirtualRouter': {'old': '', 'new': name}}
    return ret


def virtual_router_delete(name, **kwargs):
    '''
    Delete specific Contrail virtual router

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_router_delete cmp01
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    vrouter_obj = VirtualRouter(name, gsc_obj)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "VirtualRouter " + name + " will be deleted"
    else:
        vnc_client.virtual_router_delete(fq_name=vrouter_obj.get_fq_name())
        ret['comment'] = "VirtualRouter " + name + " has been deleted"
        ret['changes'] = {'VirtualRouter': {'old': name, 'new': ''}}
    return ret


def physical_router_list(**kwargs):
    '''
    Return a list of all Contrail physical routers

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.physical_router_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    prouter_objs = vnc_client._objects_list('physical-router', detail=True)
    for prouter_obj in prouter_objs:
        ret[prouter_obj.name] = {
            'uuid': prouter_obj._uuid,
            'management_ip': prouter_obj._physical_router_management_ip,
            'product_name': prouter_obj._physical_router_product_name,
        }

    return ret


def physical_router_get(name, **kwargs):
    '''
    Return a specific Contrail physical router

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.physical_router_get router_name
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    prouter_objs = vnc_client._objects_list('physical-router', detail=True)
    for prouter_obj in prouter_objs:
        if name == prouter_obj.name:
            ret[name] = prouter_obj.__dict__
    if len(ret) == 0:
        return {'Error': 'Error in retrieving physical router.'}
    return ret


def physical_router_create(name, parent_type=None,
                           management_ip=None,
                           dataplane_ip=None,  # VTEP address in web GUI
                           vendor_name=None,
                           product_name=None,
                           vnc_managed=None,
                           junos_service_ports=None,
                           agents=None, **kwargs):
    '''
    Create specific Contrail physical router

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.physical_router_create OVSDB_router management_ip=10.167.4.202 dataplane_ip=172.16.20.15 vendor_name=MyVendor product_name=MyProduct agents="['tor01','tns01']"
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    # gsc_obj = _get_config(vnc_client)
    prouter_objs = physical_router_list(**kwargs)
    if name in prouter_objs:
        prouter = physical_router_get(name)
        changes = {}
        prouter_obj = vnc_client._object_read('physical-router', id=prouter[name]['_uuid'])
        if prouter_obj.physical_router_management_ip != management_ip:
            changes['management_ip'] = {'from': prouter_obj.physical_router_management_ip, "to": management_ip}
            prouter_obj.set_physical_router_management_ip(management_ip)
        if prouter_obj.physical_router_dataplane_ip != dataplane_ip:
            changes['dataplane_ip'] = {'from': prouter_obj.physical_router_dataplane_ip, "to": dataplane_ip}
            prouter_obj.set_physical_router_dataplane_ip(dataplane_ip)
        if prouter_obj.get_physical_router_vendor_name() != vendor_name:
            changes['vendor_name'] = {'from': prouter_obj.get_physical_router_vendor_name(), "to": vendor_name}
            prouter_obj.set_physical_router_vendor_name(vendor_name)
        if prouter_obj.get_physical_router_product_name() != product_name:
            changes['product_name'] = {'from': prouter_obj.get_physical_router_product_name(), "to": product_name}
            prouter_obj.set_physical_router_product_name(product_name)
        if prouter_obj.get_physical_router_vnc_managed() != vnc_managed:
            changes['vnc_managed'] = {'from': prouter_obj.get_physical_router_vnc_managed(), "to": vnc_managed}
            prouter_obj.set_physical_router_vnc_managed(vnc_managed)
        if prouter_obj.get_physical_router_junos_service_ports() != junos_service_ports:
            changes['junos_service_ports'] = {'from': prouter_obj.get_physical_router_junos_service_ports(),
                                              'to': junos_service_ports}
            prouter_obj.set_physical_router_junos_service_ports(junos_service_ports)

        if len(changes) != 0:
            if __opts__['test']:
                ret['result'] = None
                ret['comment'] = "Physical router " + name + " will be updated"
        else:
            ret['comment'] = 'Physical router ' + name + ' already exists and is updated'
        return ret

        vrouter_objs = vnc_client._objects_list('virtual-router', detail=True)  # all vrouter objects
        c_agents = []  # referenced vrouters
        for c_agent in prouter_obj.get_virtual_router_refs():
            c_agents.append(c_agent['uuid'])
        # agent_objs = []  # required state of references
        for vrouter_obj in vrouter_objs:
            if vrouter_obj._display_name in agents and vrouter_obj._uuid not in c_agents:
                prouter_obj.add_virtual_router(vrouter_obj)
                changes['vrouter ' + vrouter_obj._display_name] = "Reference added"
            if vrouter_obj._display_name not in agents and vrouter_obj._uuid in c_agents:
                prouter_obj.del_virtual_router(vrouter_obj)
                changes['vrouter ' + vrouter_obj._display_name] = "Reference removed"
        vnc_client.physical_router_update(prouter_obj)

        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "VirtualRouter " + name + " will be created"
        else:
            vnc_client.virtual_router_create(vrouter_obj)
            ret['comment'] = "VirtualRouter " + name + " has been created"
            ret['changes'] = {'VirtualRouter': {'old': '', 'new': name}}

        if len(changes) == 0:
            ret['comment'] = "Physical router exists and is updated"
        return ret
    else:
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "Physical router " + name + " will be created"
            return ret
        prouter_obj = PhysicalRouter(
            name=name,
            parent_obj=None,
            physical_router_management_ip=management_ip,
            physical_router_dataplane_ip=dataplane_ip,
            physical_router_vendor_name=vendor_name,
            physical_router_product_name=product_name,
            physical_router_vnc_managed=vnc_managed,
            physical_router_junos_service_ports=junos_service_ports,
        )
        for agent in agents:
            vrouter = virtual_router_get(agent)
            vrouter_obj = vnc_client._object_read('virtual-router', id=vrouter[agent]['uuid'])
            prouter_obj.add_virtual_router(vrouter_obj)
        vnc_client.physical_router_create(prouter_obj)
        ret['comment'] = "Physical router " + name + " has been created"
        ret['changes'] = {'PhysicalRouter': {'old': '', 'new': name}}
    return ret


def physical_router_delete(name, **kwargs):
    '''
    Delete specific Contrail physical router

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.physical_router_delete router_name
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    prouter_obj = PhysicalRouter(name, gsc_obj)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Physical router " + name + " will be deleted"
    else:
        vnc_client.physical_router_delete(fq_name=prouter_obj.get_fq_name())
        ret['comment'] = "Physical router " + name + " has been deleted"
        ret['changes'] = {'Physical router': {'old': name, 'new': ''}}
    return ret


def physical_interface_list(**kwargs):
    '''
    Return a list of all Contrail physical interface

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.physical_interface_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    pinterface_objs = vnc_client._objects_list('physical-interface', detail=True)
    for pinterface_obj in pinterface_objs:
        ret[pinterface_obj.name] = {
            'uuid': pinterface_obj._uuid,
            'fq_name': pinterface_obj.fq_name,
            'parent_type': pinterface_obj.parent_type,
        }

    return ret


def physical_interface_get(name, physical_router, **kwargs):
    '''
    Return a specific Contrail physical interface

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.physical_interface_get interface_name physical_router_name
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    pinterf_objs = vnc_client._objects_list('physical-interface', detail=True)
    for pinterf_obj in pinterf_objs:
        if name == pinterf_obj.name and physical_router in pinterf_obj.fq_name:
            ret[name] = pinterf_obj.__dict__
    if len(ret) == 0:
        return {'Error': 'Error in retrieving physical interface.'}
    return ret


def physical_interface_create(name, physical_router, **kwargs):
    '''
    Create specific Contrail physical interface

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.physical_interface_create ge-0/0/10 physical_router_name
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    # gsc_obj = _get_config(vnc_client)
    pinterf_obj = physical_interface_get(name, physical_router, **kwargs)
    if 'Error' not in pinterf_obj:
        ret['comment'] = 'Physical interface ' + name + ' on ' + physical_router + ' already exists'
        return ret

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Physical interface " + name + " will be created"
        return ret

    prouter = physical_router_get(physical_router)
    prouter_obj = vnc_client._object_read('physical-router', id=prouter[physical_router]['_uuid'])
    pinterf_obj = PhysicalInterface(name, prouter_obj)
    vnc_client.physical_interface_create(pinterf_obj)
    ret['comment'] = "Physical interface " + name + " has been created"
    ret['changes'] = {'Physical interface': {'old': '', 'new': name}}
    return ret


def physical_interface_delete(name, physical_router, **kwargs):
    '''
    Delete specific Contrail physical interface

    CLI Example:
    .. code-block:: bash

        salt '*' contrail.physical_interface_delete ge-0/0/0 phr01
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    # gsc_obj = _get_config(vnc_client)
    piface = physical_interface_get(name, physical_router)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Physical interface " + name + " will be deleted"
    else:
        vnc_client.physical_interface_delete(id=piface[name]['_uuid'])
        ret['comment'] = "Physical router " + name + " has been deleted"
        ret['changes'] = {'Physical router': {'old': name, 'new': ''}}
    return ret


def logical_interface_list(**kwargs):
    '''
    Return a list of all Contrail logical interfaces

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.logical_interface_list
    '''
    ret = []
    vnc_client = _auth(**kwargs)
    liface_objs = vnc_client._objects_list('logical-interface', detail=True)
    for liface_obj in liface_objs:
        ret.append({
            'name': liface_obj.name,
            'uuid': liface_obj._uuid,
            'fq_name': liface_obj.fq_name,
            'parent_type': liface_obj.parent_type,
        })
    return ret


def logical_interface_get(name, parent_names, parent_type=None, **kwargs):
    '''
    Return a specific Contrail logical interface

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.logical_interface_get ge-0/0/0.10 ['phr01']
        or
        salt '*' contrail.logical_interface_get ge-0/0/0.10 ['ge-0/0/0','phr01']
        or
        salt '*' contrail.logical_interface_get ge-0/0/0.10 ['phr01'] parent_type=physcal-interface
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    liface_objs = vnc_client._objects_list('logical-interface', detail=True)
    count = 0
    for liface_obj in liface_objs:
        if name == liface_obj.name and set(parent_names).issubset(liface_obj.fq_name):
            if parent_type and parent_type == liface_obj.parent_type:
                count += 1
                ret[liface_obj.name] = liface_obj.__dict__
            if not parent_type:
                count += 1
                ret[liface_obj.name] = liface_obj.__dict__
    if len(ret) == 0:
        return {'Error': 'Error in retrieving logical interface.'}
    if count > 1:
        return {
            'Error': 'Error Was found more then one logical interface. Please put more parent_name or put parent_type to chose one of them.'}
    return ret


def logical_interface_create(name, parent_names, parent_type='physical-interface', vlan_tag=None, interface_type="l2",
                             vmis=None, **kwargs):
    '''
    Create specific Contrail logical interface

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.logical_interface_create ge-0/0/10.11 parent_names="['ge-0/0/0','phr1']" parent_type=physical-interface vlan_tag=1025 interface_type=L2
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    # gsc_obj = _get_config(vnc_client)

    liface_obj = logical_interface_get(name, parent_names, parent_type, **kwargs)
    if 'Error' not in liface_obj:
        ret['comment'] = 'Logical interface ' + name + ' already exists'
    else:
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "Logical interface " + name + " will be created"
            return ret
        parent_obj = None
        for router in parent_names:
            parent_router = physical_router_get(router)
            if 'Error' not in parent_router:
                parent_obj = vnc_client._object_read('physical-router', id=parent_router[router]['_uuid'])
                break
        if not parent_obj:
            ret['result'] = False
            ret['comment'] = 'Physical router have to be defined'
            return ret
        if parent_type == 'physical-interface':
            for interface in parent_names:
                parent_interface = physical_interface_get(interface, parent_obj.name)
                if 'Error' not in parent_interface:
                    parent_obj = vnc_client._object_read('physical-interface', id=parent_interface[interface]['_uuid'])
                    break
        if interface_type.lower() == "l3":
            ret['result'] = False
            ret['comment'] = "Virtual Network have to be defined for L3 interface type"
            return ret

        liface_obj = LogicalInterface(name, parent_obj, vlan_tag, interface_type.lower())

        if vmis:
            for vmi_name, vmi in vmis.iteritems():
                vmi = vnc_client.virtual_machine_interface_read(
                    fq_name=_get_fq_name(vnc_client, resource_name=vmi_name,
                                         project_name=kwargs.get('tenant', 'admin')))
                liface_obj.add_virtual_machine_interface(vmi)
        vnc_client.logical_interface_create(liface_obj)

    ret['comment'] = "Logical interface " + name + " has been created"
    ret['changes'] = {'Logical interface': {'old': '', 'new': name}}
    return ret


def logical_interface_delete(name, parent_names, parent_type=None, **kwargs):
    '''
    Delete specific Contrail logical interface

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.logical_interface_delete ge-0/0/0.12 ['ge-0/0/0','phr01']
        or
        salt '*' contrail.logical_interface_delete ge-0/0/0.12 ['phr01'] parent_type=physical-router

    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    # gsc_obj = _get_config(vnc_client)
    liface = logical_interface_get(name, parent_names, parent_type)

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Logical interface " + name + " will be deleted"
        return ret
    vnc_client.logical_interface_delete(id=liface[name]['_uuid'])
    ret['comment'] = "Logical interface  " + name + " has been deleted"
    ret['changes'] = {'LogicalInterface ': {'old': name, 'new': ''}}
    return ret


def global_vrouter_config_list(**kwargs):
    '''
    Return a list of all Contrail global vrouter configs

    CLI Example:

    .. code-block:: bash"

        salt '*' global_vrouter_config_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    vrouter_conf_objs = vnc_client._objects_list('global-vrouter-config', detail=True)
    for vrouter_conf_obj in vrouter_conf_objs:
        ret[vrouter_conf_obj.name] = vrouter_conf_obj.__dict__
    return ret


def global_vrouter_config_get(name, **kwargs):
    '''
    Return a specific Contrail global vrouter config

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.global_vrouter_get global-vrouter-config
    '''
    ret = {}
    vrouter_conf_objs = global_vrouter_config_list(**kwargs)
    if name in vrouter_conf_objs:
        ret[name] = vrouter_conf_objs.get(name)
    if len(ret) == 0:
        return {'Error': 'Error in retrieving  global vrouter config.'}
    return ret


def global_vrouter_config_create(name, parent_type, encap_priority, vxlan_vn_id_mode, flow_export_rate, *fq_names, **kwargs):
    '''
    Create specific Contrail global vrouter config

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.global_vrouter_config_create \
        name=global-vrouter-config parent_type=global-system-config \
        encap_priority="MPLSoUDP,MPLSoGRE" vxlan_vn_id_mode="automatic" \
        flow_export_rate=None \
        fq_names="['default-global-system-config', 'default-global-vrouter-config']"
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    # gsc_obj = _get_config(vnc_client)
    vrouter_conf_objs = global_vrouter_config_list(**kwargs)
    if name in vrouter_conf_objs:
        ret['comment'] = 'Global vrouter config ' + name + ' already exists'
        return ret
    else:
        vrouter_conf_obj = GlobalVrouterConfig(
            name=name,
            parent_obj=None,
            encapsulation_priorities=EncapsulationPrioritiesType(encapsulation=encap_priority.split(",")),
            fq_name=fq_names,
            vxlan_network_identifier_mode=vxlan_vn_id_mode,
            parent_type=parent_type,
            flow_export_rate=flow_export_rate,
        )
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "Global vRouter config " + name + " will be created"
            return ret
        vnc_client.global_vrouter_config_create(vrouter_conf_obj)
    ret['comment'] = "Global vRouter config " + name + " has been created"
    ret['changes'] = {'Global vRouter config': {'old': '', 'new': name}}
    return ret


def global_vrouter_config_delete(name, **kwargs):
    '''
    Delete specific Contrail global vrouter config

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.global_vrouter_config_delete global-vrouter-config
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    vrouter_conf_obj = GlobalVrouterConfig(name, gsc_obj)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Global vRouter config " + name + " will be deleted"
        return ret
    vnc_client.global_vrouter_config_delete(
        fq_name=vrouter_conf_obj.get_fq_name())
    ret['comment'] = "Global vRouter config " + name + " has been deleted"
    ret['changes'] = {'Global vRouter config': {'old': name, 'new': ''}}
    return ret


def analytics_node_list(**kwargs):
    '''
    Return a list of all Contrail analytics nodes

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.analytics_node_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    node_objs = vnc_client._objects_list('analytics-node', detail=True)
    for node_obj in node_objs:
        ret[node_obj.name] = node_obj.__dict__
    return ret


def analytics_node_get(name, **kwargs):
    '''
    Return a specific Contrail analytics node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.analytics_node_get nal01
    '''
    ret = {}
    vrouter_objs = analytics_node_list(**kwargs)
    if name in vrouter_objs:
        ret[name] = vrouter_objs.get(name)
    if len(ret) == 0:
        return {'Error': 'Error in retrieving analytics node.'}
    return ret


def analytics_node_create(name, ip_address, **kwargs):
    '''
    Create specific Contrail analytics node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.analytics_node_create ntw03 10.10.10.103
    '''

    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    analytics_node_objs = analytics_node_list(**kwargs)
    if name in analytics_node_objs:
        ret['comment'] = 'Analytics node %s already exists'
        return ret
    else:
        analytics_node_obj = AnalyticsNode(
            name, gsc_obj,
            analytics_node_ip_address=ip_address)
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "AnalyticsNode " + name + " will be created"
            return ret
        vnc_client.analytics_node_create(analytics_node_obj)
        ret['comment'] = "AnalyticsNode " + name + " has been created"
        ret['changes'] = {'Analytics Node': {'old': '', 'new': name}}
    return ret


def analytics_node_delete(name, **kwargs):
    '''
    Delete specific Contrail analytics node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.analytics_node_delete cmp01
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    analytics_node_obj = AnalyticsNode(name, gsc_obj)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "AnalyticsNode " + name + " will be deleted"
        return ret
    vnc_client.analytics_node_delete(
        fq_name=analytics_node_obj.get_fq_name())
    ret['comment'] = "AnalyticsNode " + name + " has been deleted"
    ret['changes'] = {'Analytics Node': {'old': name, 'new': ''}}
    return ret


def config_node_list(**kwargs):
    '''
    Return a list of all Contrail config nodes

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.config_node_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    node_objs = vnc_client._objects_list('config-node', detail=True)
    for node_obj in node_objs:
        ret[node_obj.name] = node_obj.__dict__
    return ret


def config_node_get(name, **kwargs):
    '''
    Return a specific Contrail config node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.config_node_get nal01
    '''
    ret = {}
    vrouter_objs = config_node_list(**kwargs)
    if name in vrouter_objs:
        ret[name] = vrouter_objs.get(name)
    if len(ret) == 0:
        return {'Error': 'Error in retrieving config node.'}
    return ret


def config_node_create(name, ip_address, **kwargs):
    '''
    Create specific Contrail config node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.config_node_create ntw03 10.10.10.103
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    config_node_objs = config_node_list(**kwargs)
    if name in config_node_objs:
        ret['comment'] = 'Config node ' + name + ' already exists'
        return ret
    else:
        config_node_obj = ConfigNode(
            name, gsc_obj,
            config_node_ip_address=ip_address)
        if __opts__['test']:
            ret['comment'] = "ConfigNode " + name + " will be created"
            ret['result'] = None
            return ret
        vnc_client.config_node_create(config_node_obj)
        ret['comment'] = "ConfigNode " + name + " has been created"
        ret['changes'] = {'ConfigNode': {'old': '', 'new': name}}
    return ret


def config_node_delete(name, **kwargs):
    '''
    Delete specific Contrail config node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.config_node_delete cmp01
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    config_node_obj = ConfigNode(name, gsc_obj)
    if __opts__['test']:
        ret['comment'] = "ConfigNode " + name + " will be deleted"
        ret['result'] = None
        return ret
    vnc_client.config_node_delete(
        fq_name=config_node_obj.get_fq_name())
    ret['comment'] = "ConfigNode " + name + " has been deleted"
    ret['changes'] = {'ConfigNode': {'old': name, 'new': ''}}
    return ret


def bgp_router_list(**kwargs):
    '''
    Return a list of all Contrail BGP routers

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.bgp_router_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    bgp_router_objs = vnc_client._objects_list('bgp-router', detail=True)
    for bgp_router_obj in bgp_router_objs:
        ret[bgp_router_obj.name] = bgp_router_obj.__dict__
    return ret


def bgp_router_get(name, **kwargs):
    '''
    Return a specific Contrail BGP router

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.bgp_router_get nal01
    '''
    ret = {}
    bgp_router_objs = bgp_router_list(**kwargs)
    if name in bgp_router_objs:
        ret[name] = bgp_router_objs.get(name)
    if len(ret) == 0:
        return {'Error': 'Error in retrieving BGP router.'}
    return ret


def bgp_router_create(name, type, ip_address, asn=64512, key_type=None, key=None, **kwargs):
    '''
    Create specific Contrail control node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.bgp_router_create ntw03 control-node 10.10.10.103
        salt '*' contrail.bgp_router_create mx01 router 10.10.10.105
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)

    address_families = ['route-target', 'inet-vpn', 'e-vpn', 'erm-vpn',
                        'inet6-vpn']
    if type != 'control-node':
        address_families.remove('erm-vpn')

    key_type = None if key_type == 'None' else key_type
    key = None if key == 'None' else key

    bgp_addr_fams = AddressFamilies(address_families)
    bgp_sess_attrs = [
       BgpSessionAttributes(address_families=bgp_addr_fams)]
    bgp_sessions = [BgpSession(attributes=bgp_sess_attrs)]
    bgp_peering_attrs = BgpPeeringAttributes(session=bgp_sessions)
    rt_inst_obj = _get_rt_inst_obj(vnc_client)

    bgp_auth_data = None

    if type == 'control-node':
        vendor = 'contrail'
    elif type == 'router':
        vendor = 'mx'
    else:
        vendor = 'unknown'

    if key_type == 'md5':
        key_id = 0
        key_items = AuthenticationKeyItem(key_id, key)
        bgp_auth_data = AuthenticationData(key_type, [key_items])

    router_params = BgpRouterParams(router_type=type,
                                    vendor=vendor, autonomous_system=int(asn),
                                    identifier=_get_ip(ip_address),
                                    address=_get_ip(ip_address),
                                    port=179, address_families=bgp_addr_fams,
                                    auth_data=bgp_auth_data)

    bgp_router_objs = bgp_router_list(**kwargs)
    if name in bgp_router_objs:
        bgp_router_obj = vnc_client._object_read('bgp-router', id=bgp_router_objs[name]['_uuid'])

        if bgp_router_obj.bgp_router_parameters.autonomous_system != asn:
            ret['changes'].update({"autonomous_system": {'old': bgp_router_obj.bgp_router_parameters.autonomous_system, 'new': asn}})
        if bgp_router_obj.bgp_router_parameters.vendor != vendor:
            ret['changes'].update({"vendor": {'old': bgp_router_obj.bgp_router_parameters.vendor, 'new': vendor}})
        if bgp_router_obj.bgp_router_parameters.address != ip_address:
            ret['changes'].update({"ip_address": {'old': bgp_router_obj.bgp_router_parameters.address, 'new': ip_address}})
        try:
            if bgp_router_obj.bgp_router_parameters.auth_data.key_type != key_type:
                ret['changes'].update({"key_type": {'old': bgp_router_obj.bgp_router_parameters.auth_data.key_type, 'new': key_type}})
        except:
            if key_type != None:
                ret['changes'].update({"key_type": {'old': None, 'new': key_type}})
        if key_type == 'md5':
            try:
                if bgp_router_obj.bgp_router_parameters.auth_data.key_items[0].key != key:
                    ret['changes'].update({"key": {'old': bgp_router_obj.bgp_router_parameters.auth_data.key_items[0].key, 'new': key}})
            except:
                ret['changes'].update({"key": {'old': None, 'new': key}})

        if len(ret['changes']) == 0:
            return ret

        bgp_router_obj.set_bgp_router_parameters(router_params)
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "BGP router " + name + " will be updated"
            return ret
        vnc_client.bgp_router_update(bgp_router_obj)
        ret['comment'] = "BGP router " + name + " has been updated"
        return ret
    else:
        bgp_router_obj = BgpRouter(name, rt_inst_obj, bgp_router_parameters=router_params)
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "BGP router " + name + " will be created"
            return ret
        vnc_client.bgp_router_create(bgp_router_obj)
        ret['comment'] = "BGP router " + name + " has been created"
        ret['changes'] = {'BGP router': {'old': name, 'new': ''}}
    return ret


def bgp_router_delete(name, **kwargs):
    '''
    Delete specific Contrail control node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.bgp_router_delete mx01
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "BGP router " + name + " will be deleted"
        return ret

    bgp_router = bgp_router_get(name)
    if name in bgp_router:
        vnc_client.bgp_router_delete(fq_name=bgp_router[name]['fq_name'])
        ret['comment'] = "BGP router " + name + " has been deleted"
        ret['changes'] = {'BGP router': {'old': '', 'new': name}}
    return ret


def database_node_list(**kwargs):
    '''
    Return a list of all Contrail database nodes

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.database_node_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    node_objs = vnc_client._objects_list('database-node', detail=True)
    for node_obj in node_objs:
        ret[node_obj.name] = node_obj.__dict__
    return ret


def database_node_get(name, **kwargs):
    '''
    Return a specific Contrail database node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.database_node_get nal01
    '''
    ret = {}
    vrouter_objs = database_node_list(**kwargs)
    if name in vrouter_objs:
        ret[name] = vrouter_objs.get(name)
    if len(ret) == 0:
        return {'Error': 'Error in retrieving database node.'}
    return ret


def database_node_create(name, ip_address, **kwargs):
    '''
    Create specific Contrail database node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.database_node_create ntw03 10.10.10.103
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    database_node_objs = database_node_list(**kwargs)
    if name in database_node_objs:
        ret['comment'] = 'Database node ' + name + ' already exists'
        return ret
    else:
        database_node_obj = DatabaseNode(
            name, gsc_obj,
            database_node_ip_address=ip_address)
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "DatabaseNode " + name + " will be created"
            return ret
        vnc_client.database_node_create(database_node_obj)
        ret['comment'] = "DatabaseNode " + name + " has been created"
        ret['changes'] = {'DatabaseNode': {'old': '', 'new': name}}
    return ret


def database_node_delete(name, **kwargs):
    '''
    Delete specific Contrail database node

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.database_node_delete cmp01
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    database_node_obj = DatabaseNode(name, gsc_obj)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "DatabaseNode " + name + " will be deleted"
        return ret
    vnc_client.database_node_delete(
        fq_name=database_node_obj.get_fq_name())
    ret['comment'] = "DatabaseNode " + name + " has been deleted"
    ret['changes'] = {'DatabaseNode': {'old': '', 'new': name}}
    return ret


def _get_vrouter_config(vnc_client, gvc_name=None):
    try:
        vrouter_conf_objs = vnc_client._objects_list('global-vrouter-config', detail=True)
        if len(vrouter_conf_objs) == 0:
            return None
        if not gvc_name:
            return vrouter_conf_objs[0]
        for gvc in vrouter_conf_objs:
            if gvc.name == gvc_name:
                return gvc
    except Exception as e:
       print("Error: {}".format(e))
       pass

    return None


def linklocal_service_list(global_vrouter_config_name=None, **kwargs):
    '''
    Return a list of all Contrail link local services

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.linklocal_service_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)

    current_config = _get_vrouter_config(vnc_client, global_vrouter_config_name)
    if current_config is None:
        return ret

    service_list_res = current_config.get_linklocal_services()
    if service_list_res is None:
        service_list_obj = {'linklocal_service_entry': []}
    else:
        service_list_obj = service_list_res.__dict__
    for _, value in service_list_obj.iteritems():
        for entry in value:
            service = entry.__dict__
            if 'linklocal_service_name' in service:
                ret[service['linklocal_service_name']] = service
    return ret


def linklocal_service_get(name, **kwargs):
    '''
    Return a specific Contrail link local service

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.linklocal_service_get llservice
    '''
    ret = {}
    services = linklocal_service_list(**kwargs)
    if name in services:
        ret[name] = services.get(name)
    if len(ret) == 0:
        return {'Error': 'Error in retrieving link local service "{0}"'.format(name)}
    return ret


def linklocal_service_create(name, lls_ip, lls_port, ipf_dns_or_ip, ipf_port, global_vrouter_config_name=None, **kwargs):
    '''
    Create specific Contrail link local service

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.linklocal_service_create \
            llservice 10.10.10.103 22 '["20.20.20.20", "30.30.30.30"]' 22
        salt '*' contrail.linklocal_service_create \
            llservice 10.10.10.103 22 link-local.service.dns-name 22
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    current_config = _get_vrouter_config(vnc_client, global_vrouter_config_name)
    if current_config is None:
        ret['result'] = False
        ret['comment'] = "Global Vrouter Config doesn't exist and is required for LinkLocalSevices"
        return ret

    service_entry = LinklocalServiceEntryType(
        linklocal_service_name=name,
        linklocal_service_ip=lls_ip,
        linklocal_service_port=lls_port,
        ip_fabric_service_port=ipf_port)
    if isinstance(ipf_dns_or_ip, basestring):
        service_entry.ip_fabric_DNS_service_name = ipf_dns_or_ip
    elif isinstance(ipf_dns_or_ip, list):
        service_entry.ip_fabric_service_ip = ipf_dns_or_ip
        service_entry.ip_fabric_DNS_service_name = ''

    _current_service_list = current_config.get_linklocal_services()
    if _current_service_list is None:
        service_list = {'linklocal_service_entry': []}
    else:
        service_list = _current_service_list.__dict__
    new_services = [service_entry]
    value = service_list.get('linklocal_service_entry')
    for _entry in value:
        entry = _entry.__dict__
        if 'linklocal_service_name' in entry:
            if entry['linklocal_service_name'] == name:
                ret['comment'] = 'Link local service ' + name + ' already exists'
                return ret
            new_services.append(_entry)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "LinkLocalSevices " + name + " will be created"
    service_list['linklocal_service_entry'] = new_services
    new_config = GlobalVrouterConfig(linklocal_services=service_list)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "LinkLocalSevices " + name + " will be updated"
    else:
        vnc_client.global_vrouter_config_update(new_config)
        ret['comment'] = "LinkLocalSevices " + name + " has been created"
        ret['changes'] = {'LinkLocalSevices': {'old': '', 'new': name}}
    return ret


def linklocal_service_delete(name, **kwargs):
    '''
    Delete specific link local service entry

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.linklocal_service_delete llservice
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    lls = linklocal_service_get(name)
    if name in lls:
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "Link local service " + name + " will be deleted"
            return ret
    else:
        return ret

    vnc_client = _auth(**kwargs)
    current_config = _get_vrouter_config(vnc_client)
    if current_config is not None:
        _current_service_list = current_config.get_linklocal_services()
        if _current_service_list is None:
            service_list = {'linklocal_service_entry': []}
        else:
            service_list = _current_service_list.__dict__
        new_services = []
        for key, value in service_list.iteritems():
            if key != 'linklocal_service_entry':
                continue
            for _entry in value:
                entry = _entry.__dict__
                if 'linklocal_service_name' in entry:
                    if entry['linklocal_service_name'] != name:
                        new_services.append(_entry)
            service_list[key] = new_services
        new_config = GlobalVrouterConfig(linklocal_services=service_list)
        vnc_client.global_vrouter_config_update(new_config)
        ret['comment'] = "Link local service " + name + " will be deleted"
        ret['changes'] = {'LinkLocalService': {'old': name, 'new': ''}}
    else:
        ret['result'] = False
        ret['comment'] = "Global Vrouter Config doesn't exist and is required for LinkLocalSevices"
    return ret


def virtual_machine_interface_list(**kwargs):
    '''
    Return a list of all Contrail virtual machine interfaces

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_machine_interfaces
    '''
    ret = []
    vnc_client = _auth(**kwargs)
    project = _get_project_obj(vnc_client, name=kwargs.get('tenant', 'admin'))
    project_uuid = project.get_uuid()

    vm_ifaces = vnc_client.virtual_machine_interfaces_list(
        detail=True, parent_id=project_uuid)

    for vm_iface in vm_ifaces:
        ret.append(vm_iface.__dict__)

    return ret


def virtual_machine_interface_create(name,
                                     virtual_network,
                                     mac_address=None,
                                     ip_address=None,
                                     security_group=None,
                                     **kwargs):
    '''
    Create specific Contrail  virtual machine interface (Port)

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_machine_interface_create port01 net01 mac_address='01:02:03:04:05:06'
        router_types:
        - tor-agent
        - tor-service-node
        - embedded
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    project = _get_project_obj(vnc_client, name=kwargs.get('tenant', 'admin'))

    vm_int = VirtualMachineInterface(name, parent_obj=project)

    if mac_address:
        mac_address_obj = MacAddressesType([mac_address])
        vm_int.set_virtual_machine_interface_mac_addresses(mac_address_obj)

    if security_group:
        sgo = vnc_client.security_group_read(fq_name=_get_fq_name(
          vnc_client, security_group, kwargs.get('tenant', 'admin')))
        vm_int.set_security_group(sgo)

    vnet_uuid = virtual_network_get(virtual_network, **kwargs)[virtual_network]['_uuid']
    vnet_obj = vnc_client.virtual_network_read(id=vnet_uuid)
    vm_int.set_virtual_network(vnet_obj)

    vmi_uuid = vnc_client.virtual_machine_interface_create(vm_int)
    vmi = vnc_client.virtual_machine_interface_read(id=vmi_uuid)

    vm_int.set_port_security_enabled(False)
    vnc_client.virtual_machine_interface_update(vm_int)

    # Allocate IP to VMI
    ip = vnc_api.InstanceIp(name + '.ip')
    ip.set_virtual_machine_interface(vmi)
    ip.set_virtual_network(vnet_obj)

    ip_uuid = vnc_client.instance_ip_create(ip)

    if ip_address:
        ip.set_instance_ip_address(ip_address)
        vnc_client.instance_ip_update(ip)

    return vmi.__dict__


def virtual_network_list(**kwargs):
    '''
    Return a list of all Contrail virtual network

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_network
    '''

    ret = {}
    vnc_client = _auth(**kwargs)
    virtual_networks = vnc_client._objects_list('virtual-network', detail=True)
    for virtual_network in virtual_networks:
        ret[virtual_network.name] = virtual_network.__dict__
    return ret


def virtual_network_get(name, **kwargs):
    '''
    Return a specific Contrail virtual network

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.virtual_network_get net01
    '''
    ret = {}
    vnet_objs = virtual_network_list(**kwargs)
    if name in vnet_objs:
        ret[name] = vnet_objs.get(name)
    if len(ret) != 1:
        return {'result': False,
                'Error': 'Error in retrieving virtual networks.'}
    return ret


def virtual_network_create(name, domain='default-domain', project='admin',
                           ipam_domain='default-domain',
                           ipam_project='default-project',
                           ipam_name='default-network-ipam',
                           router_external=None, route_target_list=None,
                           subnet_conf=None, vntype_conf=None, **kwargs):
    '''
    Create Contrail virtual network
    CLI Example:
    .. code-block:: bash

    salt -C 'I@opencontrail:control:role:primary'
        contrail.virtual_network_create public router_external=True
        route_target_list=["target:64512:10000"]
        subnet_conf=["ip_prefix":"172.16.111.0","ip_prefix_len":24]

    Parameters:
    name (str): name of the network (required)
    domain (str): name of domain (optional)
    project (str): name of project (optional)
    ipam_domain (str): domain for ipam (optional)
    ipam_project (str): project for ipam (optional)
    ipam_name (str): name of IP Address Management (optional)
    router_external (bool): When true, this virtual network is openstack router
        external network. (optional)
    route_target_list (list): route target list - format is
        ['target:<asn>:<target>']
    subnet_conf (dict):
        ip_prefix (string) optional - format is xxx.xxx.xxx.xxx
        ip_prefix_len (int) optional - format is xx
    vntype_conf (dict):
        allow_transit (boolean) optional - enable allow transit
        vxlan_network_identifier (int) - VxLAN VNI value for network
        forwarding_mode (any of ['l2_l3','l2','l3']) optional
            - packet forwarding mode for this virtual network
        rpf (any of ['enabled','disabled']) optional
            - Enable or disable Reverse Path Forwarding check
        for this network
        mirror_destination (boolean) optional
            - Mark the vn as mirror destination network
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}

    vnc_client = _auth(**kwargs)
    fq_name = [domain, project, name]
    prj_obj = vnc_client.project_read(fq_name=[domain,
                                               project])
    ipam_obj = vnc_client.network_ipam_read(fq_name=[ipam_domain,
                                                     ipam_project,
                                                     ipam_name])
    if route_target_list:
        route_target_list = RouteTargetList(route_target_list)
    if subnet_conf:
        if 'ip_prefix' in subnet_conf and 'ip_prefix_len' in subnet_conf:
            ipam_sn = IpamSubnetType(subnet=SubnetType(
                ip_prefix=subnet_conf['ip_prefix'],
                ip_prefix_len=subnet_conf['ip_prefix_len']))

    # Check if the network exists
    vn_obj_list = vnc_client.virtual_networks_list(parent_id=prj_obj.uuid)
    if name in list(map(lambda x: x['fq_name'][2],
                        vn_obj_list['virtual-networks'])):
        changes = {}
        vn_obj = vnc_client.virtual_network_read(fq_name=fq_name)

        # Update IPAM properties
        ipam_refs = vn_obj.get_network_ipam_refs()
        subnet_detected = False
        if subnet_conf and ipam_refs:
            for ipam in ipam_refs:
                if ipam_obj.get_uuid() == ipam['uuid']:
                    ipam_subnet_list = ipam['attr'].get_ipam_subnets()
                    for ipam_subnet_type in ipam_subnet_list:
                        subnet_obj = ipam_subnet_type.get_subnet()
                        ip_prefix = subnet_obj.get_ip_prefix()
                        ip_prefix_len = subnet_obj.get_ip_prefix_len()
                        if subnet_conf['ip_prefix'] == ip_prefix and \
                                subnet_conf['ip_prefix_len'] == ip_prefix_len:
                            subnet_detected = True
        if subnet_conf and not subnet_detected:
            changes['ipam_subnet'] = \
                {'added': '{0}/{1}'.format(subnet_conf['ip_prefix'],
                                           subnet_conf['ip_prefix_len'])}
            vn_obj.add_network_ipam(ipam_obj,
                                    VnSubnetsType(ipam_subnets=[ipam_sn]))

        # Update VirtualNetwork properties
        external = vn_obj.get_router_external()
        if router_external is not None and router_external != external:
            changes['router_external'] = {'from': external,
                                          'to': router_external}
            vn_obj.set_router_external(router_external)
        if route_target_list:
            changes['router_list'] = \
                {'from': str(vn_obj.get_route_target_list()),
                 'to': str(route_target_list)}
            vn_obj.set_route_target_list(route_target_list)

        # Update VirtualNetworkType properties
        if vntype_conf:
            vn_type_obj = vn_obj.get_virtual_network_properties()
            if vn_type_obj is None:
                vn_type_obj = VirtualNetworkType()

            if 'allow_transit' in vntype_conf:
                allow_transit_attr = vn_type_obj.get_allow_transit()
                if vntype_conf['allow_transit'] != allow_transit_attr:
                    changes['allow_transit'] = \
                        {'from': allow_transit_attr,
                         'to': vntype_conf['allow_transit']}
                    vn_type_obj.set_allow_transit(vntype_conf['allow_transit'])
            if 'vxlan_network_identifier' in vntype_conf:
                vxlan_net_id = vn_type_obj.get_vxlan_network_identifier()
                if vntype_conf['vxlan_network_identifier'] != vxlan_net_id:
                    vn_type_obj.set_vxlan_network_identifier(
                        vntype_conf['vxlan_network_identifier'])
                    changes['vxlan_network_identifier'] = \
                        {'from': vxlan_net_id,
                         'to': vntype_conf['vxlan_network_identifier']}
            if 'forwarding_mode' in vntype_conf:
                forwarding_mode_attr = vn_type_obj.get_forwarding_mode()
                if vntype_conf['forwarding_mode'] in ['l2_l3', 'l2', 'l3'] and \
                        vntype_conf['forwarding_mode'] != forwarding_mode_attr:
                    changes['forwarding_mode'] = \
                        {'from': forwarding_mode_attr,
                         'to': vntype_conf['forwarding_mode']}
                    vn_type_obj.set_forwarding_mode(
                        vntype_conf['forwarding_mode'])
            if 'mirror_destination' in vntype_conf:
                mirror_dst_attr = vn_type_obj.get_mirror_destination()
                if vntype_conf['mirror_destination'] != mirror_dst_attr:
                    changes['mirror_destination'] = \
                        {'from': mirror_dst_attr,
                         'to': vntype_conf['mirror_destination']}
                    vn_type_obj.set_mirror_destination(
                        vntype_conf['mirror_destination'])
            if 'rpf' in vntype_conf:
                rpf_attr = vn_type_obj.get_rpf()
                if vntype_conf['rpf'] != rpf_attr:
                    changes['rpf'] = \
                        {'from': rpf_attr,
                         'to': vntype_conf['rpf']}
                    vn_type_obj.set_rpf(vntype_conf['rpf'])
            vn_obj.set_virtual_network_properties(vn_type_obj)

        if changes:
            ret['changes'] = changes
            if __opts__['test']:
                ret['result'] = None
                ret['comment'] = "Virtual network " + name + " will be updated"
            else:
                ret['comment'] = "VirtualNetwork " + name + " has been updated"
                vnc_client.virtual_network_update(vn_obj)
        else:
            ret['comment'] = 'Virtual network ' + name + \
                             ' already exists and is updated'
    else:
        vn_obj = VirtualNetwork(name, prj_obj)

        # Configure IPAM properties
        if subnet_conf:
            if 'ip_prefix' in subnet_conf and 'ip_prefix_len' in subnet_conf:
                vn_obj.add_network_ipam(ipam_obj,
                                        VnSubnetsType(ipam_subnets=[ipam_sn]))

        # Configure VirtualNetwork properties
        if router_external is not None:
            vn_obj.set_router_external(router_external)
        if route_target_list is not None:
            vn_obj.set_route_target_list(route_target_list)

        # Configure VirtualNetworkType properties
        if vntype_conf:
            vn_type_obj = VirtualNetworkType()
            if 'allow_transit' in vntype_conf:
                vn_type_obj.set_allow_transit(vntype_conf['allow_transit'])
            if 'vxlan_network_identifier' in vntype_conf:
                vn_type_obj.set_vxlan_network_identifier(
                    vntype_conf['vxlan_network_identifier'])
            if 'forwarding_mode' in vntype_conf:
                if vntype_conf['forwarding_mode'] in ['l2_l3', 'l2', 'l3']:
                    vn_type_obj.set_forwarding_mode(
                        vntype_conf['forwarding_mode'])
            if 'mirror_destination' in vntype_conf:
                vn_type_obj.set_mirror_destination(vntype_conf['mirror_destination'])
            if 'rpf' in vntype_conf:
                vn_type_obj.set_rpf(vntype_conf['rpf'])
            vn_obj.set_virtual_network_properties(vn_type_obj)

        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "VirtualNetwork " + name + " will be created"
        else:
            vnc_client.virtual_network_create(vn_obj)
            ret['comment'] = "VirtualNetwork " + name + " has been created"
            ret['changes'] = {'VirtualNetwork': {'created': name}}
    return ret


def service_appliance_set_list(**kwargs):
    '''
    Return a list of Contrail service appliance set

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.service_appliance_set_list
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    service_appliance_sets = vnc_client._objects_list('service-appliance-set', detail=True)
    for service_appliance_set in service_appliance_sets:
        ret[service_appliance_set.name] = service_appliance_set.__dict__
    return ret


def service_appliance_set_get(name, **kwargs):
    '''
    Return a specific Contrail service appliance set

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.service_appliance_set_get name
    '''
    ret = {}
    sas_objs = service_appliance_set_list(**kwargs)
    if name in sas_objs:
        ret[name] = sas_objs.get(name)
    if len(ret) != 1:
        return {'result': False,
                'Error': "Error in the retrieving service apliance set."}
    return ret


def service_appliance_set_create(name, properties=None, driver=None, ha_mode=None, **kwargs):
    '''
    Create Contrail service appliance set

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.service_appliance_set_create name
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    sas_objs = service_appliance_set_list(**kwargs)
    if name in sas_objs:
        ret['commnet'] = 'Service appliance set  ' + name + ' already exists'
    else:
        service_appliance_set_obj = ServiceApplianceSet(
            name, gsc_obj)
        if properties:
            pairs = KeyValuePairs()
            for k, v in properties.items():
                pairs.add_key_value_pair(KeyValuePair(k, v))
            service_appliance_set_obj.set_service_appliance_set_properties(pairs)
        if driver:
            service_appliance_set_obj.set_service_appliance_driver(driver)
        if ha_mode:
            service_appliance_set_obj.set_service_appliance_ha_mode(ha_mode)
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = "ServiceApplianceSet " + name + " will be created"
        else:
            vnc_client.service_appliance_set_create(service_appliance_set_obj)
            ret['comment'] = "ServiceApplianceSet " + name + " has been created"
            ret['changes'] = {'ServiceApplianceSet': {'old': '', 'new': name}}
    return ret


def service_appliance_set_delete(name, **kwargs):
    '''
    Delete specific Contrail service appliance set

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.service_appliance_set_delete name
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)
    gsc_obj = _get_config(vnc_client)
    sas_obj = ServiceApplianceSet(name, gsc_obj)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Service appliance set " + name + " will be deleted"
    else:
        vnc_client.service_appliance_set_delete(fq_name=sas_obj.get_fq_name())
        ret['comment'] = "ServiceApplianceSet " + name + " has been deleted"
        ret['changes'] = {'ServiceApplianceSet': {'old': name, 'new': ''}}
    return ret

def global_system_config_list(**kwargs):
    '''
    Return a list of all global system configs

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.global_system_config_list
    '''

    ret = {}
    vnc_client = _auth(**kwargs)
    gsysconfs = vnc_client._objects_list('global-system-config', detail=True)
    for gsysconf in gsysconfs:
        ret[gsysconf.name] = gsysconf.__dict__
    return ret


def global_system_config_get(name, **kwargs):
    '''
    Return a specific Contrail global system config

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.global_system_config_get name
    '''
    ret = {}
    vnc_client = _auth(**kwargs)
    gsc_objs = vnc_client._objects_list('global-system-config', detail=True)
    for gsc_obj in gsc_objs:
        if name == gsc_obj.name:
                ret[name] = gsc_obj.__dict__
    if len(ret) == 0:
        return {'Error': 'Error in retrieving global system config.'}
    return ret


def global_system_config_create(name, ans=64512, grp=None,  **kwargs):
    '''
    Create Contrail global system config

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.global_system_config_create name=default-global-system-config ans=64512
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)

    gsc_objs = global_system_config_list(**kwargs)
    if name in gsc_objs:
        config_obj = vnc_client.global_system_config_read(fq_name=[name])
        if config_obj.graceful_restart_parameters and not HAS_OLD:
            curr_grp = str(config_obj.graceful_restart_parameters).replace(" ", "").split(",")
            curr_grpd = dict(item.split('=') for item in curr_grp)
        else:
            curr_grpd = None

        if grp and 'enable' in grp and not HAS_OLD:
            grp_obj = GracefulRestartParametersType()
            if 'enable' in grp:
                grp_obj.enable = grp['enable']
                if curr_grpd and str(grp['enable']) != str(curr_grpd['enable']):
                    ret['changes']['enable'] = {"from": str(curr_grpd['enable']), "to": str(grp['enable'])}
                elif not curr_grpd:
                    ret['changes']['enable'] = {"from": None, "to": grp['enable']}
            if 'restart_time' in grp:
                grp_obj.restart_time = grp['restart_time']
                if curr_grpd and grp['restart_time'] != int(curr_grpd['restart_time']):
                    ret['changes']['restart_time'] = {"from": int(curr_grpd['restart_time']), "to": grp['restart_time']}
                elif not curr_grpd:
                    ret['changes']['restart_time'] = {"from": None, "to": grp['restart_time']}
            if 'end_of_rib_timeout' in grp:
                grp_obj.end_of_rib_timeout = grp['end_of_rib_timeout']
                if curr_grpd and grp['end_of_rib_timeout'] != int(curr_grpd['end_of_rib_timeout']):
                    ret['changes']['end_of_rib_timeout'] = {"from": int(curr_grpd['end_of_rib_timeout']), "to": grp['end_of_rib_timeout']}
                elif not curr_grpd:
                    ret['changes']['end_of_rib_timeout'] = {"from": None, "to": grp['end_of_rib_timeout']}
            if 'bgp_helper_enable' in grp:
                grp_obj.bgp_helper_enable = grp['bgp_helper_enable']
                if curr_grpd and str(grp['bgp_helper_enable']) != str(curr_grpd['bgp_helper_enable']):
                    ret['changes']['bgp_helper_enable'] = {"from": str(curr_grpd['bgp_helper_enable']), "to": grp['bgp_helper_enable']}
                elif not curr_grpd:
                    ret['changes']['bgp_helper_enable'] = {"from": None, "to": grp['bgp_helper_enable']}
            if 'xmpp_helper_enable' in grp:
                grp_obj.xmpp_helper_enable = grp['xmpp_helper_enable']
                if curr_grpd and str(grp['xmpp_helper_enable']) != str(curr_grpd['xmpp_helper_enable']):
                    ret['changes']['xmpp_helper_enable'] = {"from": str(curr_grpd['xmpp_helper_enable']), "to": grp['xmpp_helper_enable']}
                elif not curr_grpd:
                    ret['changes']['xmpp_helper_enable'] = {"from": None, "to": grp['xmpp_helper_enable']}
            if 'long_lived_restart_time' in grp:
                grp_obj.long_lived_restart_time = grp['long_lived_restart_time']
                if curr_grpd and grp['long_lived_restart_time'] != int(curr_grpd['long_lived_restart_time']):
                    ret['changes']['long_lived_restart_time'] = {"from": int(curr_grpd['long_lived_restart_time']), "to": grp['long_lived_restart_time']}
                elif not curr_grpd:
                    ret['changes']['long_lived_restart_time'] = {"from": None, "to": grp['long_lived_restart_time']}
        else:
            grp_obj = None

        config_obj.graceful_restart_parameters = grp_obj

        if ans:
            if config_obj.autonomous_system != ans:
                ret['changes']['autonomous_system'] = {"from": config_obj.autonomous_system, "to": ans}
                config_obj.autonomous_system = ans

        vnc_client.global_system_config_update(config_obj)
        ret['comment'] = 'Global system config  ' + name + ' has been updated'
    else:
        config_obj = GlobalSystemConfig(name=name)
        if grp and not HAS_OLD:
            grp_obj = GracefulRestartParametersType()
            if 'enable' in grp:
                grp_obj.enable = grp['enable']
            if 'restart_time' in grp:
                grp_obj.restart_time = grp['restart_time']
            if 'end_of_rib_timeout' in grp:
                grp_obj.end_of_rib_timeout = grp['end_of_rib_timeout']
            if 'bgp_helper_enable' in grp:
                grp_obj.bgp_helper_enable = grp['bgp_helper_enable']
            if 'xmpp_helper_enable' in grp:
                grp_obj.xmpp_helper_enable = grp['xmpp_helper_enable']
            if 'long_lived_restart_time' in grp:
                grp_obj.long_lived_restart_time = grp['long_lived_restart_time']
            config_obj.graceful_restart_parameters = grp_obj
        if ans:
            config_obj.autonomous_system = ans

        vnc_client.global_system_config_create(config_obj)
        ret['changes'] = {"created": "new"}
        ret['comment'] = 'Global system config  ' + name + ' has been created '

    return ret


def global_system_config_delete(name, **kwargs):
    '''
    Delete specific Contrail global system config

    CLI Example:

    .. code-block:: bash

        salt '*' contrail.global_system_config_delete name
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    vnc_client = _auth(**kwargs)

    gsc_obj = GlobalSystemConfig(name)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Global system config " + name + " will be deleted"
    else:
        vnc_client.global_system_config_delete(fq_name=gsc_obj.get_fq_name())
        ret['comment'] = "GlobalSystemConfig " + name + " has been deleted"
        ret['changes'] = {'GlobalSystemConfig': {'old': name, 'new': ''}}
    return ret


def list_floating_ip_pools(**kwargs):
    '''
    List all floating ip pools

    CLI Example:
    .. code-block:: bash
        salt '*' contrail.list_floating_ip_pools
    '''
    vnc_client = _auth(**kwargs)
    pools = vnc_client.floating_ip_pools_list()
    # list of floating ip pools objects
    fp_list = []

    for pool in vnc_client.floating_ip_pools_list()['floating-ip-pools']:
        fip_obj = vnc_client.floating_ip_pool_read(pool['fq_name'])
        fp_list.append(fip_obj)
        # print given pool
        fip_obj.dump()

def update_floating_ip_pool(vn_name, vn_project, vn_domain=None,
                            owner_access=None, global_access=None,
                            projects=None, **kwargs):
    '''
    Update specific floating ip pool


    CLI Example
    .. code-block:: bash
        salt-call contrail.update_floating_ip_pool \
                                  'FLOATING-TEST' \
                                  'admin' \
                                  'default-domain' \
                                  7 7 \
                                  [['pepa',4],['karel',7]]


    params:
    vn_name - name of the virtual network, which to use
    vn-project - project which includes virtual network
    vn-domain - domain wchich includes vn_project and vn_name
    owner_access (int) - Permission rights for owner
    global_access (int) - Permission rights for others
    projects (list) - list of ShareType(tenant_name,tennat_permissions)
    '''
    ret = {'name': vn_name + "-default pool",
           'changes': {},
           'result': True,
           'comment': ''}

    if vn_domain is None:
        vn_domain = 'default-domain'
    fip_obj = None

    vnc_client = _auth(**kwargs)
    p_fq_name = [vn_domain, vn_project, vn_name, 'default']
    fip_obj = vnc_client.floating_ip_pool_read(fq_name=p_fq_name)

    changes = {}
    # get perms from fip_obj (Floatin ip pool)
    perms2 = fip_obj.get_perms2()
    if owner_access is not None:
        if perms2.get_owner_access() != owner_access:
            changes['owner_access'] = {'old': str(perms2.get_owner_access()),
                                       'new': str(owner_access)}
            perms2.set_owner_access(owner_access)

    if global_access is not None:
        if perms2.get_global_access() != global_access:
            changes['global_access'] = {'old': str(perms2.get_global_access()),
                                        'new': str(global_access)}
            perms2.set_global_access(global_access)

    # list which represents the new state of perms
    final_list = []
    if projects:
        for item in perms2.get_share():
            for share in projects:
                if item.get_tenant() == share[0]:
                    # project is in the new and old list
                    # check is the permission number is same
                    if item.get_tenant_access() == share[1]:
                        # this project and permission is without change, keep it
                        final_list.append(item)
                        break
                    else:
                        # project exists but change the permission
                        final_list.append(ShareType(tenant=share[0],
                                                    tenant_access=share[1]))
                        # show changes
                        n = str('share-'+share[0])
                        old_str = "permission for project {0} was {1}"
                        new_str = "permission for project {0} will be {1}"
                        old = old_str.format(share[0],
                                             str(item.get_tenant_access()))

                        new = new_str.format(share[0], str(share[1]))
                        changes[n] = {'old': old, 'new': new}
                        break
            else:
                rm_name = "share-" + item.get_tenant()
                changes[rm_name] = item.get_tenant() + " will be removed"

        # check for the completly new projects
        for item in projects:
            for share in final_list:
                if item[0] == share.get_tenant():
                    break
            else:
                final_list.append(ShareType(tenant=item[0],
                                            tenant_access=item[1]))
                name = 'share-' + str(item[0])
                c_str = '{0} will be added with permissions {1}'
                changes[name] = c_str.format(name, item[1])
    else:
        for item in perms2.get_share():
            rm_name = "share-" + item.get_tenant()
            changes[rm_name] = item.get_tenant() + " will be removed"

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = changes

        return ret
    else:
        ret['comment'] = changes
        perms2.set_share(final_list)
        fip_obj.set_perms2(perms2)
        vnc_client.floating_ip_pool_update(fip_obj)

        return ret


def show_rbac_rules(api_access_list_entries):
    if api_access_list_entries is None:
        return 'Empty RBAC group!'

    rule_list = api_access_list_entries.get_rbac_rule()
    response = 'Rules (%d):' % len(rule_list) + '----------\n'
    for idx, rule in enumerate(rule_list):
        o = rule.rule_object
        f = rule.rule_field
        ps = ', '.join([p.role_name+':'+p.role_crud for p in rule.rule_perms])
        o_f = "%s.%s" % (o, f) if f else o
        response += '%2d %-32s   %s\n' % (idx, o_f, ps)
    return response


def vnc_read_obj(vnc, obj_type, fq_name):
    method_name = obj_type.replace('-', '_')
    method = getattr(vnc, "%s_read" % (method_name))
    try:
        return method(fq_name=fq_name)
    except NoIdError:
        print '%s %s not found!' % (obj_type, fq_name)
        return None


def rbac_show_group(name, uuid, **kwargs):
    '''
    Show specific RBAC group


    CLI Example
    .. code-block:: bash
        salt-call contrail.rbac_show_group name \
            'default-domain:default-project:default'

    params:
    name - one of pair {name, uuid} addresing to access-list
    uuid(str) - UUID in case of "uuid" specified OR full RBAC group name \
        including domain and project

    '''
    vnc = _auth(**kwargs)
    fq_name = vnc.id_to_fq_name(uuid) if name == 'uuid' else uuid.split(':')
    ret = {'name': fq_name,
           'changes': {},
           'result': True,
           'comment': ''}
    rg = vnc_read_obj(vnc, 'api-access-list', fq_name)
    if not rg:
        ret['comment'] = 'No rules found'
        return ret

    ret['comment'] = show_rbac_rules(rg.get_api_access_list_entries())
    return ret


def rbac_create_group(uuid, **kwargs):
    '''
    Create RBAC group

    CLI Example
    .. code-block:: bash
        salt-call contrail.rbac_create_group name \
            'default-domain:default-project:default'

    params:
    name - one of pair {name, uuid} addresing to access-list
    uuid(str) - UUID in case of "uuid" specified OR full RBAC group name \
        including domain and project

    '''
    vnc = _auth(**kwargs)
    fq_name = uuid.split(':')
    ret = {'name': fq_name,
           'changes': {},
           'result': True,
           'comment': ''}
    if len(fq_name) != 2 and len(fq_name) != 3:
        ret['comment'] = 'Fully qualified name of rbac group expected'
        return ret

    name = fq_name[-1]

    if len(fq_name) == 2:
        if fq_name[0] == 'default-global-system-config':
            pobj = vnc.global_system_config_read(fq_name=fq_name[0:1])
        else:
            pobj = vnc.domain_read(fq_name=fq_name[0:1])
    else:
        pobj = vnc.project_read(fq_name=fq_name[0:2])

    rentry = RbacRuleEntriesType([])
    rg = ApiAccessList(name, parent_obj=pobj, api_access_list_entries=rentry)

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "RBAC group " + uuid + " will be created"

        return ret
    else:
        vnc.api_access_list_create(rg)
        rg2 = vnc.api_access_list_read(fq_name=fq_name)
        rge = rg.get_api_access_list_entries()
        show_rbac_rules(rge)
        ret['comment'] = "RBAC group " + uuid + " has been created"

        return ret


def rbac_delete_group(name, uuid, **kwargs):
    '''
    Delete RBAC group

    CLI Example
    .. code-block:: bash
        salt-call contrail.rbac_delete_group name \
            'default-domain:default-project:default'

    params:
    name - one of pair {name, uuid} addresing to access-list
    uuid(str) - UUID in case of "uuid" specified OR full RBAC group name \
        including domain and project

    '''
    vnc = _auth(**kwargs)
    fq_name = vnc.id_to_fq_name(uuid) if name == 'uuid' else uuid.split(':')
    ret = {'name': fq_name,
           'changes': {},
           'result': True,
           'comment': ''}
    if len(fq_name) != 2 and len(fq_name) != 3:
        ret['comment'] = 'Fully qualified name of rbac group expected'
        return ret
    name = fq_name[-1]

    rg = vnc_read_obj(vnc, 'api-access-list', fq_name)
    if not rg:
        ret['comment'] = 'No rules found'
        return ret
    rge = rg.get_api_access_list_entries()
    show_rbac_rules(rge)

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "RBAC group " + uuid + " will be deleted"

        return ret
    else:
        vnc.api_access_list_delete(fq_name=fq_name)
        ret['comment'] = "RBAC group " + uuid + " has been deleted"

        return ret


def rbac_add_rule(name, uuid, add_rule, **kwargs):
    '''
    Add rule to specific RBAC group

    CLI Example
    .. code-block:: bash
        salt-call contrail.rbac_add_rule name \
            'default-domain:default-project:default' \
            '* admin:CRUD'

    params:
    name - one of pair {name, uuid} addresing to access-list
    uuid(str) - UUID in case of "uuid" specified OR full RBAC group name \
        including domain and project
    rule(str) - Appropriate RBAC-based rule in format '<object, field> \
        list of <role:CRUD>' to be added

    '''
    vnc = _auth(**kwargs)
    fq_name = vnc.id_to_fq_name(uuid) if name == 'uuid' else uuid.split(':')
    rule = build_rule(add_rule)
    ret = {'name': fq_name,
           'changes': {},
           'result': True,
           'comment': ''}
    if rule is None:
        ret['comment'] = 'A rule string must be specified for this operation'
        return ret

    # rbac rule entry consists of one or more rules
    rg = vnc_read_obj(vnc, 'api-access-list', fq_name)
    if not rg:
        ret['comment'] = 'No rules found'
        return ret

    rge = rg.get_api_access_list_entries()
    if rge is None:
        rge = RbacRuleEntriesType([])
    show_rbac_rules(rge)

    # avoid duplicates
    match = find_rule(rge, rule)
    if not match:
        rge.add_rbac_rule(rule)
    else:
        build_perms(rge.rbac_rule[match[0]-1], match[3])

    show_rbac_rules(rge)

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Rule " + add_rule
        ret['comment'] += " will be created for RBAC group " + uuid

        return ret
    else:
        rg.set_api_access_list_entries(rge)
        vnc.api_access_list_update(rg)
        ret['comment'] = "Rule " + add_rule
        ret['comment'] += " has been added for RBAC group " + uuid

        return ret


def rbac_delete_rule(name, uuid, del_rule, **kwargs):
    '''
    Delete rule to specific RBAC group

    CLI Example
    .. code-block:: bash
        salt-call contrail.rbac_delete_rule name \
            'default-domain:default-project:default' \
            '* admin:CRUD'

    params:
    name - one of pair {name, uuid} addresing to access-list
    uuid(str) - UUID in case of "uuid" specified OR full RBAC group name \
        including domain and project
    rule(str) - Appropriate RBAC-based rule in format '<object, field> \
        list of <role:CRUD>' to be deleted

    '''
    vnc = _auth(**kwargs)
    fq_name = vnc.id_to_fq_name(uuid) if name == 'uuid' else uuid.split(':')
    rg = vnc_read_obj(vnc, 'api-access-list', fq_name)
    ret = {'name': fq_name,
           'changes': {},
           'result': True,
           'comment': ''}
    if not rg:
        ret['comment'] = 'No rules found'
        return ret
    rge = rg.get_api_access_list_entries()
    show_rbac_rules(rge)

    del_idx = re.match("^[0-9]+$", del_rule)
    if del_idx:
        del_idx = int(del_idx.group())
        rc = len(rge.rbac_rule)
        if del_idx > rc or del_idx < 1:
            ret['comment'] = 'Invalid rule index to delete.'
            ret['comment'] += 'Value must be 1-%d' % rc
            return ret
        match = (del_idx, True)
    else:
        rule = build_rule(del_rule)
        match = find_rule(rge, rule)

    if not match:
        ret['comment'] = "Rule not found. Unchanged"
        return ret
    elif match[1]:
        rge.rbac_rule.pop(match[0]-1)
    else:
        build_perms(rge.rbac_rule[match[0]-1], match[2])
    show_rbac_rules(rge)

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = "Rule " + del_rule
        ret['comment'] += " will be cleared from RBAC group " + uuid

        return ret
    else:
        rg.set_api_access_list_entries(rge)
        vnc.api_access_list_update(rg)
        ret['comment'] = "Rule " + del_rule
        ret['comment'] += " has been cleared from RBAC group " + uuid

        return ret
