#!/bin/bash
{%- from "opencontrail/map.jinja" import compute with context %}
{%- set bind_addr=compute.interface.address|replace('0.0.0.0', '127.0.0.1') %}

metadata=$(curl --silent http://{{ bind_addr|default('127.0.0.1') }}:8085/Snh_LinkLocalServiceInfo | grep -c 169.254.169.254 )
echo "{ \"contrail_instance_metadata_present\": $metadata }"
