# EAWS Regions

Provides all region definitions for EAWS (and more).

https://regions.avalanches.org/

This repository provides the regions in a GeoJSON format and their names in different languages.
In addition, the historical polygons are also included to process older bulletins. For this there are the attributes `valid_from` and `valid_until` in the polygons JSON property, which indicate in which period these were used.
Current polygons have no end of validity.

## Contributing

Contributions are very welcome. When changing any [metadata](https://gitlab.com/eaws/eaws-regions/-/blob/master/public/outline_properties/index.json) (such as names, URLs) or polygon of micro regions, feel free to either submit an issue or provide a merge request.

Follow-up actions performed by the ALBINA software community are:

- releasing a new `eaws-regions` version+packages
- updating `eaws-regions` dependency in:
  - albina-website
  - albina-admin-gui
  - pyAvaCore
  - eaws-bulletin-map
- updating avalanche-warning-maps

Please communicate to person in charge of https://www.avalanches.org/about/#organization to have the details updated there.

## NPM packages

For each git tag, we build and publish NPM packages to the GitLab Registry: https://gitlab.com/eaws/eaws-regions/-/packages

In order to `npm install @eaws/...`, configure npm/yarn/bun:

```yaml
# .npmrc
@eaws:registry=https://gitlab.com/api/v4/packages/npm/

# .yarnrc.yml
npmScopes:
  eaws:
    npmRegistryServer: "https://gitlab.com/api/v4/packages/npm/"

# bunfig.toml
[install.scopes]
"@eaws" = "https://gitlab.com/api/v4/packages/npm/"
```

## Latest regions

The repository contains the current regions as well as a history and therefore "outdated" regions. A subset containing only the currently valid regions can be found within the downloadable artifact in the additional "latest" folders:
https://gitlab.com/eaws/eaws-regions/-/jobs/artifacts/master/download?job=pages

## Translations

The region names are being translated on Transifex: https://app.transifex.com/albina-euregio/eaws-regions/dashboard/
