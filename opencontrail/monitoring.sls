{%- if pillar.opencontrail is defined and pillar.telegraf is defined %}
  {%- if pillar.opencontrail.collector is defined %}
    {%- set version = pillar.opencontrail.collector.version %}
  {%- endif %}
  {%- if pillar.opencontrail.control is defined %}
    {%- set version = pillar.opencontrail.control.version %}
  {%- endif %}
  {%- if pillar.opencontrail.database is defined %}
    {%- set version = pillar.opencontrail.database.version %}
  {%- endif %}

  {%- if pillar.opencontrail.collector is defined or
         pillar.opencontrail.control is defined or
         pillar.opencontrail.database is defined %}
contrail_control_status_check_telegraf_script:
  file.managed:
  - name: /usr/local/bin/check_contrail_health.py
  - source: salt://opencontrail/files/{{ version }}/check_contrail_health.py
  - template: jinja
  - mode: 755
  {%- endif %}

  {%- if pillar.opencontrail.control is defined %}
contrail_control_vrouter_check_telegraf_script:
  file.managed:
  - name: /usr/local/bin/check_global_vrouter_config.py
  - source: salt://opencontrail/files/{{ version }}/check_global_vrouter_config.py
  - template: jinja
  - mode: 755
  {%- endif %}
{%- endif %}
