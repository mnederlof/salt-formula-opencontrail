{%- from "opencontrail/map.jinja" import client, compute with context -%}

{%- for agent_name, agent in compute.tor.agent.iteritems() %}

contrail-toragent-setup --cfgm_ip {{ client.api.host }} \
--self_ip {{ agent.address }} \
--control-nodes {% for member in compute.control.members %}{{ member.host }}{% if not loop.last %} {% endif %}{% endfor %} \
--collectors {% for member in compute.collector.members %}{{ member.host }}{% if not loop.last %} {% endif %}{% endfor %} \
--authserver_ip {{ client.identity.host }} \
--admin_user {{ client.identity.user }} \
--admin_password {{ client.identity.password }} \
--admin_tenant_name {{ client.identity.tenant }} \
--auth_protocol http \
--tor_name {{ agent.tor_name }} \
--http_server_port {{ agent.http_server_port }} \
--tor_ip {{ agent.tor_ip }} \
--tor_id {{ agent.id }} \
--tsn_ip {{ agent.tsn_ip }} \
--tor_tunnel_ip {{ agent.tor_tunnel_ip }} \
{%- if agent.get('xmpp_auth_enable', False) == True %}
--xmpp_auth_enable \
{%- endif %}
{%- if agent.get('xmpp_dns_auth_enable', False) == True %}
--xmpp_dns_auth_enable \
{%- endif %}
--tor_ovs_port {{ agent.tor_ovs_port }} \
--tor_ovs_protocol {{ agent.tor_ovs_protocol }} \
{%- if agent.tor_product_name is defined %}
----tor_product_name {{ agent.tor_product_name }} \
{%- endif %}
--tor_vendor_name {{ agent.tor_vendor_name }}

{%- endfor %}
