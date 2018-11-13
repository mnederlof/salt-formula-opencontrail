{%- from "opencontrail/map.jinja" import web with context %}
/*
 * Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
 */

/****************************************************************************
 * Specify the authentication parameters for admin user
 ****************************************************************************/
var auth = {};
auth.admin_token = '';
{%- if web.identity.engine == "keystone" %}
auth.admin_user = '{{ web.identity.user }}';
auth.admin_password = '{{ web.identity.password }}';
auth.admin_tenant_name = '{{ web.identity.tenant }}';
{%- else %}
/* NOTE(ivasilevskaya) should be configured at the model level */
auth.admin_user = 'admin';
/* NOTE(ivasilevskaya) should be configured at the model level */
auth.admin_password = 'contrail123';
{%- endif %}

module.exports = auth;
