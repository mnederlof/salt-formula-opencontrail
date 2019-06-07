opencontrail:
  common:
    version: 4.0
    identity:
      engine: keystone
      protocol: http
      host: 127.0.0.1
      port: 35357
      token: token
      password: password
    network:
      engine: neutron
      host: 127.0.0.1
      port: 9696
  client:
    api:
      host: 127.0.0.1
      use_ssl: False
    identity:
      host: 127.0.0.1
      user: contrail
      password: contrail
      tenant: admin
  compute:
    version: 4.0
    enabled: True
    collector:
      members:
      - host: 127.0.0.1
      - host: 127.0.0.1
      - host: 127.0.0.1
    control:
      members:
      - host: 127.0.0.1
      - host: 127.0.0.1
      - host: 127.0.0.1
    bind:
      address: 127.0.0.1
    interface:
      address: 127.0.0.1
      dev: eth0
      gateway: 127.0.0.1
      mask: /24
      dns: 127.0.0.1
      mtu: 9000
    tor:
      enabled: false
      agent:
        tor01:
          id: 0
          address: 127.0.0.1
          tor_name: TOR01
          tor_ip: 127.0.0.1
          tor_ovs_protocol: tcp
          tor_ovs_port: 6640
          http_server_port: 9090
          tsn_ip: 127.0.0.1
          tor_tunnel_ip: 127.0.0.1
          tor_vendor_name: ovs
          xmpp_auth_enable: False
          xmpp_dns_auth_enable: False
    lbaas:
      enabled: true
      secret_manager:
        engine: barbican
        identity:
          user: admin
          password: "supersecretpassword123"
          tenant: admin
    xmpp:
      tls:
        enabled: True
        auth:
          enabled: True
        cert_file: /etc/contrail/server.pem
        key_file: /etc/contrail/privkey.pem
        ca_cert_file: /etc/contrail/ca-cert.pem