import paramiko
from paramiko import SSHClient


def filter_dict_for_creds(conf: dict):
    return {k: v for k, v in conf.items() if k in {
        "username", "password", "key_filename"}}


def execute_remotely(client: SSHClient, command: str):
    """
    :param client: SSHClient
    :param command: no terminating newline required.
    :return:
    """
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.readlines(), stderr.readlines()


def get_client(
        ip_address: str, port: int, credentials: dict) -> SSHClient:
    client = None
    try:
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=ip_address, port=port, **credentials)
    except Exception as e:
        if client:
            client.close()
        raise
    return client

