#!/usr/bin/env python3

import logging, ops, os

logger = logging.getLogger(__name__)

CONTROL_RELATION = "microovn-cluster"
WORKER_RELATION = "cluster"

def secretid(unitname):
    return "{0}-secret".format(unitname)

class MicroovnCharmCharm(ops.CharmBase):
    """Charm the application."""
    _stored = ops.StoredState()

    @property
    def relevant_relation(self):
        return WORKER_RELATION if self.is_worker else CONTROL_RELATION

    @property
    def is_control_plane(self) -> bool:
        """Returns true if the unit is a control-plane."""
        return not self.is_worker

    @property
    def lead_control_plane(self) -> bool:
        """Returns true if the unit is the leader control-plane."""
        return self.is_control_plane and self.unit.is_leader()

    @property
    def is_worker(self) -> bool:
        """Returns true if the unit is a worker."""
        return self.meta.name == "microovn-worker"


    def update_tokens(self, relation_name):
        relation = self.model.get_relation(relation_name)
        if relation == None:
            return

        relation_data = relation.data

        newToken = False
        for unit in relation_data:
            # need hostname
            if not "hostname" in relation_data[unit]:
                continue

            # dont generate token for self or already generated
            if self.unit.name == unit.name or unit.name in relation_data[self.unit]:
                continue

            # get hostname
            hostname = relation_data[unit]["hostname"]
            token = os.popen(
                    "microovn cluster add {}".format(hostname)).read()
            token = token.strip()
            relation.data[self.unit][unit.name] = token
            logger.info("added token to {}".format(unit.name))
            newToken=True

        return newToken

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self._stored.set_default(in_cluster=False)
        framework.observe(self.on.start, self._on_start)
        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.remove, self._on_remove)
        if self.is_control_plane:
            framework.observe(self.on[CONTROL_RELATION].relation_changed,
                              self._on_peers_changed)
        else:
            framework.observe(self.on[WORKER_RELATION].relation_changed,
                              self._on_cluster_changed)


    def add_hostname(self, relation_name):
        relation = self.model.get_relation(relation_name)
        relation.data[self.unit]["hostname"] = os.uname()[1]

    def find_token(self, relation_name):
        if not (relation := self.model.get_relation(relation_name)):
            return False

        tokens = {
            token
            for unit in relation.units | {self.unit}
            if (token := relation.data[unit].get(self.unit.name))
        }
        if len(tokens) != 1:
            return False
        (token,) = tokens
        return token

    def join_with_token(self, token):
        self.unit.status = ops.MaintenanceStatus("Joining cluster")
        os.system("microovn cluster join {}".format(token))
        self._stored.in_cluster=True
        self.unit.status = ops.ActiveStatus("Joined cluster")

    def _on_install(self, event: ops.InstallEvent):
        self.unit.status = ops.MaintenanceStatus("installing microovn snap")
        os.system("snap install microovn --channel latest/edge")
        self.unit.status = ops.MaintenanceStatus("waiting for microovn ready")
        os.system("microovn waitready")
        self.unit.status = ops.MaintenanceStatus("waiting for cluster setup")

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.add_hostname(self.relevant_relation)

        if not self.lead_control_plane:
            return

        # only bootstrap if leader
        os.system(f"microovn cluster bootstrap")
        self._stored.in_cluster = True
        self.unit.status = ops.ActiveStatus("cluster bootstrapped")
        self.update_tokens(CONTROL_RELATION)
        self.update_tokens(WORKER_RELATION)

    def _on_remove(self, event: ops.RemoveEvent):
        os.system("microovn cluster remove {}".format(os.uname()[1]))

    def _handle_relation_joined(self, relation_name):
        if not self.unit.is_leader() or not self._stored.in_cluster:
            return False

        if self.update_tokens(relation_name):
            return True
        return False


    def _on_cluster_changed(self, event: ops.RelationChangedEvent):
        if not self._stored.in_cluster:
            if (token := self.find_token(WORKER_RELATION)):
                self.join_with_token(token)

        self._handle_relation_joined(WORKER_RELATION)

    def _on_peers_changed(self, event: ops.RelationChangedEvent):
        if not self.unit.is_leader() and not self._stored.in_cluster:
            if (token := self.find_token(CONTROL_RELATION)):
                self.join_with_token(token)

        self._handle_relation_joined(CONTROL_RELATION)

if __name__ == "__main__":  # pragma: nocover
    ops.main(MicroovnCharmCharm)
