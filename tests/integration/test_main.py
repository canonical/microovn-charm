import json
import os

import jubilant

def get_charm_from_env(env):
    charm_path = "./" + os.environ.get(env)
    if charm_path is None:
        raise EnvironmentError("{0} is not set".format(env))
    return charm_path

def is_command_passing(juju, commandstring, unitname):
    try:
        juju.exec(commandstring, unit=unitname)
        return True
    except:
        return False


microovn_charm_path = get_charm_from_env("MICROOVN_CHARM_PATH")
token_distributor_charm_path = get_charm_from_env("TOKEN_DISTRIBUTOR_CHARM_PATH")
dummy_charm_path = get_charm_from_env("INTERFACE_CONSUMER_CHARM_PATH")

def test_integrate(juju: jubilant.Juju):
    juju.deploy(microovn_charm_path)
    juju.add_unit("microovn")
    juju.deploy(token_distributor_charm_path)
    juju.integrate("microovn","microcluster-token-distributor")
    juju.wait(jubilant.all_active)
    juju.exec("microovn status", unit="microovn/1")

def test_integrate_post_start(juju: jubilant.Juju):
    juju.deploy(microovn_charm_path)
    juju.deploy(token_distributor_charm_path)
    juju.wait(lambda status: jubilant.all_active(status, "microcluster-token-distributor"))
    juju.wait(lambda status: jubilant.all_maintenance(status, "microovn"))
    juju.integrate("microovn","microcluster-token-distributor")
    juju.add_unit("microovn")
    juju.wait(jubilant.all_active)
    juju.exec("microovn status", unit="microovn/1")

def test_token_distributor_down(juju: jubilant.Juju):
    juju.deploy(microovn_charm_path)
    juju.deploy(token_distributor_charm_path)
    juju.integrate("microovn","microcluster-token-distributor")
    juju.add_unit("microovn")
    juju.wait(jubilant.all_active)
    juju.remove_unit("microcluster-token-distributor/0")
    juju.add_unit("microcluster-token-distributor")
    juju.add_unit("microovn")
    juju.wait(jubilant.all_active)
    juju.exec("microovn status", unit="microovn/2")

def test_microcluster_leader_down(juju: jubilant.Juju):
    juju.deploy(microovn_charm_path)
    juju.add_unit("microovn")
    juju.deploy(token_distributor_charm_path)
    juju.integrate("microovn","microcluster-token-distributor")
    juju.wait(jubilant.all_active)
    output = juju.exec("microovn cluster list -f json", unit="microovn/0").stdout
    json_output = json.loads(output)
    voter_names = [ x["name"] for x in json_output
                    if (x["role"] in ["voter", "PENDING"]) and (x["status"] == "ONLINE") ]
    voter_name = min(voter_names)
    hostname = juju.exec("hostname -s",unit="microovn/0").stdout[:-1]
    if hostname == voter_name:
        juju.remove_unit("microovn/0")
    else:
        juju.remove_unit("microovn/1")
    juju.add_unit("microovn")
    juju.wait(jubilant.all_active)

def test_integrate_ovsdb(juju: jubilant.Juju):
    juju.deploy(microovn_charm_path)
    juju.add_unit("microovn")
    juju.deploy(token_distributor_charm_path)
    juju.integrate("microovn","microcluster-token-distributor")
    juju.wait(jubilant.all_active)
    juju.deploy(dummy_charm_path)
    juju.integrate("microovn","interface-consumer")
    juju.wait(jubilant.all_active)
    output = juju.cli("show-unit","interface-consumer/0", "--format", "json", "--endpoint", "ovsdb")
    json_output = json.loads(output)
    data = json_output["interface-consumer/0"]["relation-info"][0]["application-data"]
    assert(data.get("db_nb_connection_str"))
    assert(data.get("db_sb_connection_str"))

def test_certificates_integration(juju: jubilant.Juju):
    juju.deploy(microovn_charm_path)
    juju.add_unit("microovn")
    juju.deploy(token_distributor_charm_path)
    juju.deploy("self-signed-certificates")
    juju.integrate("microovn","microcluster-token-distributor")
    juju.integrate("microovn","self-signed-certificates")
    juju.wait(jubilant.all_active)
    juju.wait(lambda _: "CA certificate updated, new certificates issued" in juju.debug_log())
    destination = juju.status().apps["microovn"].units["microovn/1"].public_address
    destination = destination + ":6643"
    command_str = "openssl s_client -connect {0}".format(destination)
    output = juju.exec(command_str + "|| true", unit="self-signed-certificates/0")
    assert("Verification: OK" not in output.stdout)

    # this check is checking if the certificate chain is intact and as we expect,
    # the command will return with a nonzero exit code due to not having a actual
    # certificate and private key therefore the connection cannot be fully done,
    # causing the error. However we can still check it is as we expect.
    #
    # https://github.com/openssl/openssl/blob/2d978786f3e97a2701d5f62c26a4baab4a224e69/apps/lib/s_cb.c#L1265
    command_str = "openssl s_client -connect {0} -CAfile /tmp/ca-cert.pem || true".format(
        destination)
    output = juju.exec(command_str, unit="self-signed-certificates/0")
    assert("Verification: OK" in output.stdout)
    # this checks the full certificate chain works and will work in the standard
    # use case.
    juju.deploy(dummy_charm_path)
    juju.integrate("self-signed-certificates","interface-consumer")
    juju.integrate("microovn","interface-consumer")
    juju.wait(jubilant.all_active)
    juju.wait(lambda _: is_command_passing(juju,"ls /root/pki/consumer.pem","interface-consumer/0"))
    command_str = "openssl s_client -connect {0} -CAfile /root/pki/ca.pem -cert /root/pki/consumer.pem -key /root/pki/consumer.key -verify_return_error".format(destination)
    output = juju.exec(command_str, unit="interface-consumer/0")
