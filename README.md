<!--
Avoid using this README file for information that is maintained or published elsewhere, e.g.:

* metadata.yaml > published on Charmhub
* documentation > published on (or linked to from) Charmhub
* detailed contribution guide > documentation or CONTRIBUTING.md

Use links instead.
-->

# microovn-operator

More information: https://charmhub.io/microovn

This is a thin layer over [MicroOVN](https://github.com/canonical/microovn), to allow MicroOVN to be used within the charm ecosystem. 

This is to be deployed alongside [microcluster-token-distributor](https://github.com/canonical/microcluster-token-distributor-operator) for cluster management. 

## Deployment

An example deployment looks something like this:

```
juju deploy microovn -n 3
juju deploy microcluster-token-distributor
juju relate microovn microcluster-token-distributor
```

This will give you 3 MicroOVN nodes, that should set up a stable microcluster using the microcluster-token-distributor.

## Integrations

MicroOVN supports a couple of useful relations:
- ovsdb: which exposes the connection strings for the ovs northbound and southbound databases.
- tls-certificates: which integrates with a certificate provider and then adds the application certificate provided into the chain for the certificates it issues to the MicroOVN units allowing for other applications to properly interface with it.

## Other resources

- [Contributing](CONTRIBUTING.md) <!-- or link to other contribution documentation -->

- See the [Juju SDK documentation](https://juju.is/docs/sdk) for more information about developing and improving charms.
