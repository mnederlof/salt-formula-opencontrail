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
      # TODO: deprecate repos on fuel-infra (use mirror.mirantis.com), at the moment tests use same repos as for docker images
      mcp_ocata_fuel_infra:
        source: "deb [arch=amd64] http://mirror.fuel-infra.org/mcp-repos/ocata/{{ grains.get('oscodename') }} ocata main"
        architectures: amd64
        key_url: "http://mirror.fuel-infra.org/mcp-repos/ocata/{{ grains.get('oscodename') }}/archive-mcpocata.key"
        pin:
        - pin: 'release a=ocata'
          priority: 1100
          package: '*'
