linux:
  system:
    enabled: true
    repo:
      mcp_opencontrail_repo:
        source: "deb [arch=amd64] http://mirror.mirantis.com/nightly/opencontrail-4.1/{{ grains.get('oscodename') }} {{ grains.get('oscodename') }} main"
        architectures: amd64
        key_url: "http://mirror.mirantis.com/nightly/opencontrail-4.1/{{ grains.get('oscodename') }}/archive-opencontrail-4.1.key"
        pin:
        - pin: 'release a=nightly'
          priority: 1100
          package: '*'
      mcp_extra_repo:
        source: "deb [arch=amd64] http://mirror.mirantis.com/nightly/extra/{{ grains.get('oscodename') }} {{ grains.get('oscodename') }} main"
        architectures: amd64
        key_url: "http://mirror.mirantis.com/nightly/extra/{{ grains.get('oscodename') }}/archive-extra.key"
        pin:
        - pin: 'release a=nightly'
          priority: 1100
          package: '*'
      mcp_openstack_ocata:
        source: "deb [arch=amd64] http://mirror.mirantis.com/nightly/openstack-ocata/{{ grains.get('oscodename') }} {{ grains.get('oscodename') }} main"
        architectures: amd64
        key_url: "http://mirror.mirantis.com/nightly/openstack-ocata/{{ grains.get('oscodename') }}/archive-ocata.key"
        pin:
        - pin: 'release a=ocata'
          priority: 1100
          package: '*'
