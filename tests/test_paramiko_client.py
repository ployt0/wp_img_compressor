from unittest.mock import patch, Mock, sentinel

import pytest
from paramiko.ssh_exception import AuthenticationException
from paramiko.channel import ChannelFile

from paramiko_client import get_client, filter_dict_for_creds, execute_remotely

MOCK_CONFIG = {
    "host": "272.170.10.22",
    "username": "tips",
    "password": "schwarzkopf",
    "wp_uploads": "don'twannaknow"
}


@patch("paramiko_client.SSHClient", autospec=True)
@patch("paramiko_client.paramiko.AutoAddPolicy", autospec=True)
def test_initialise_connection(mock_autoaddpolicy, mock_ssh_client):
    mock_ssh_object = mock_ssh_client.return_value
    get_client(MOCK_CONFIG["host"], 42, filter_dict_for_creds(MOCK_CONFIG))
    mock_ssh_object.load_system_host_keys.assert_called_once_with()
    mock_ssh_object.set_missing_host_key_policy.assert_called_once_with(mock_autoaddpolicy.return_value)
    mock_ssh_object.connect.assert_called_once_with(
        hostname=MOCK_CONFIG["host"],
        port=42,
        **filter_dict_for_creds(MOCK_CONFIG)
    )
    mock_ssh_client.assert_called_once_with()
    mock_ssh_object.close.assert_not_called()


@patch("paramiko_client.SSHClient", autospec=True)
@patch("paramiko_client.paramiko.AutoAddPolicy", autospec=True)
def test_initialise_connection_fail(mock_autoaddpolicy, mock_ssh_client):
    mock_ssh_object = mock_ssh_client.return_value
    mock_ssh_object.connect.side_effect=AuthenticationException
    with pytest.raises(AuthenticationException) as e_info:
        get_client(MOCK_CONFIG["host"], 42, filter_dict_for_creds(MOCK_CONFIG))
    mock_ssh_object.load_system_host_keys.assert_called_once_with()
    mock_ssh_object.set_missing_host_key_policy.assert_called_once_with(mock_autoaddpolicy.return_value)
    mock_ssh_object.connect.assert_called_once_with(
        hostname=MOCK_CONFIG["host"],
        port=42,
        **filter_dict_for_creds(MOCK_CONFIG)
    )
    mock_ssh_client.assert_called_once_with()
    mock_ssh_object.close.assert_called_once_with()


def test_filter_dict_for_creds():
    result = filter_dict_for_creds(MOCK_CONFIG)
    assert result == {
        "username": "tips",
        "password": "schwarzkopf"
    }
    MOCK_CONFIG_W_KEY = {
        "host": "272.170.10.22",
        "username": "tips",
        "password": "schwarzkopf",
        "wp_uploads": "don'twannaknow",
        "any_junk": "don'tcare",
        "key_filename": "../../.vagrant/machines/default/virtualbox/private_key"
    }
    result = filter_dict_for_creds(MOCK_CONFIG_W_KEY)
    # Unsure what happens when both key and password present...
    assert result == {
        "username": "tips",
        "password": "schwarzkopf",
        "key_filename": "../../.vagrant/machines/default/virtualbox/private_key"
    }


@patch("paramiko_client.SSHClient", autospec=True)
def test_execute_remotely(mock_client):
    mock_lines = """\
Genwine output from a shell command.
Or perhaps I made this bit up?""".split("\n")
    mock_readlines = Mock(return_value=mock_lines)
    mock_errlines = Mock(return_value="")
    mock_channel_out = Mock(spec=ChannelFile, readlines=mock_readlines)
    mock_channel_err = Mock(spec=ChannelFile, readlines=mock_errlines)
    mock_client.exec_command = Mock(autospec=True, return_value=(
        sentinel, mock_channel_out, mock_channel_err))
    sample_command = "level me up"
    stdout, stderr = execute_remotely(mock_client, sample_command)
    mock_client.exec_command.assert_called_once_with(sample_command)
    mock_channel_out.readlines.assert_called_once_with()
    mock_channel_err.readlines.assert_called_once_with()

