import os
from pathlib import Path
from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from compressor import ImgConvertor, CompressorException

__TEST_ALLDIRS = [(43023, "NotAnOption1"), (3841, "NotAnOption2"), (21841, "NotAnOption3")]


def get_foobar_processor():
    img_name = "../par1/tests/foobar.samp"
    widths_and_heights = []
    subdir_root = "/x/y/z/"
    img_processor = ImgConvertor(img_name, widths_and_heights, subdir_root)
    return img_processor, subdir_root


def test_ImgConvertor():
    img_processor, _ = get_foobar_processor()
    assert img_processor.stem_name == "foobar"
    assert img_processor.all_dirs == []


def test_extract_final_dir_and_suffix():
    img_processor, subdir_root = get_foobar_processor()
    sequestering_subdir = "img_magickhappens/"
    fqdir_name = os.path.join(subdir_root, sequestering_subdir)
    dir_name, final_suffix = img_processor.extract_final_dir_and_suffix(
        fqdir_name)
    assert sequestering_subdir == dir_name
    assert final_suffix == "img"


def test_print_summary():
    img_processor, subdir_root = get_foobar_processor()
    img_processor.all_dirs = __TEST_ALLDIRS
    size_list = img_processor.print_summary()
    assert size_list == sorted(__TEST_ALLDIRS)


def test_select_one():
    img_processor, subdir_root = get_foobar_processor()
    img_processor.all_dirs = __TEST_ALLDIRS
    sorted_all_dirs = sorted(__TEST_ALLDIRS)
    img_processor.print_summary = Mock(return_value=sorted_all_dirs)
    with patch("builtins.input", side_effect = ['42', '1']) as mocked_open:
        chosen_dir = img_processor.select_one()
    assert chosen_dir == sorted_all_dirs[1][1]


def test_select_one_fails_uninitialised():
    img_processor, subdir_root = get_foobar_processor()
    with pytest.raises(CompressorException):
        img_processor.select_one()


@patch("compressor.Path", autospec=True)
@patch("compressor.run_shell_cmd", autospec=True)
@patch("compressor.split_cmd_not_args", autospec=True, return_value=sentinel.cmd_split)
def test_transform_to_dir(mock_split_cmd, mock_run_shell, mock_path):
    img_processor, subdir_root = get_foobar_processor()
    img_processor.extract_final_dir_and_suffix = Mock(autospec=True, return_value=("img_magickhappens/", "img"))
    img_processor.path_to_new_img = Mock(return_value=sentinel.dest_img)
    img_processor.path_to_resized_img = Mock(return_value=sentinel.resized)
    img_processor.count_bytes_in_subdir = Mock(return_value=sentinel.dirsize)
    img_processor.widths_and_heights = [(42, 65)]
    img_processor.transform_to_dir(
        5, "tif", "test_description", "do foo bar", ["do nada"])
    assert img_processor.subdir_name == '/x/y/z/tif_q5_test_description'
    assert img_processor.all_dirs == [(sentinel.dirsize, img_processor.subdir_name)]
    mock_run_shell.assert_has_calls([
        call(sentinel.cmd_split),
        call(sentinel.cmd_split)
    ])
    img_processor.count_bytes_in_subdir.assert_called_once_with()
    assert len(mock_split_cmd.mock_calls) == 2


@patch("compressor.Path", autospec=True)
@patch("compressor.get_client", autospec=True)
@patch("compressor.execute_remotely", autospec=True, return_value=(sentinel.out, []))
def test_replace_generated_sizes(mock_execute_remotely, mock_get_client, mock_path):
    img_processor, subdir_root = get_foobar_processor()
    img_processor.widths_and_heights = [(42, 65)]
    img_processor.path_to_resized_img = Mock(return_value=sentinel.src_name)
    fq_rmt_path = os.path.join("/var/www/html/wp-content/uploads/", "2022/07/the-uploaded.png")
    img_processor.replace_generated_sizes(
        sentinel.host, 666, sentinel.credentials, "bmp", fq_rmt_path)
    mock_get_client.assert_called_once_with(sentinel.host, 666, sentinel.credentials)
    mock_get_client.return_value.open_sftp.assert_called_once_with()
    mock_get_client.return_value.open_sftp.return_value.put.assert_called_once()
    mock_get_client.return_value.open_sftp.return_value.close.assert_called_once_with()
    mock_get_client.return_value.close.assert_called_once_with()


@patch("compressor.Path", autospec=True)
@patch("compressor.get_client", autospec=True)
@patch("compressor.execute_remotely", autospec=True,
       side_effect=[RuntimeError(sentinel.error), (sentinel.out, [])])
def test_replace_generated_sizes_rmt_exec_errs_first(
        mock_execute_remotely, mock_get_client, mock_path):
    img_processor, subdir_root = get_foobar_processor()
    img_processor.widths_and_heights = [(42, 65)]
    img_processor.path_to_resized_img = Mock(return_value=sentinel.src_name)
    fq_rmt_path = os.path.join("/var/www/html/wp-content/uploads/", "2022/07/the-uploaded.png")
    with pytest.raises(RuntimeError) as rterr:
        img_processor.replace_generated_sizes(
            sentinel.host, 666, sentinel.credentials, "bmp", fq_rmt_path)
    assert "sentinel.error" in str(rterr)
    mock_get_client.assert_called_once_with(sentinel.host, 666, sentinel.credentials)
    mock_get_client.return_value.open_sftp.assert_not_called()
    mock_get_client.return_value.open_sftp.return_value.put.assert_not_called()
    mock_get_client.return_value.open_sftp.return_value.close.assert_not_called()
    mock_get_client.return_value.close.assert_called_once_with()


@patch("compressor.Path", autospec=True)
@patch("compressor.get_client", autospec=True)
@patch("compressor.execute_remotely", autospec=True, side_effect=[(sentinel.out, []), (sentinel.out, sentinel.err)])
def test_replace_generated_sizes_rmt_exec_errs_second(
        mock_execute_remotely, mock_get_client, mock_path):
    img_processor, subdir_root = get_foobar_processor()
    img_processor.widths_and_heights = [(42, 65)]
    img_processor.path_to_resized_img = Mock(return_value=sentinel.src_name)
    fq_rmt_path = os.path.join("/var/www/html/wp-content/uploads/", "2022/07/the-uploaded.png")
    with pytest.raises(RuntimeError) as rterr:
        img_processor.replace_generated_sizes(
            sentinel.host, 666, sentinel.credentials, "bmp", fq_rmt_path)
    assert "sentinel.err" in str(rterr)
    mock_get_client.assert_called_once_with(sentinel.host, 666, sentinel.credentials)
    mock_get_client.return_value.open_sftp.assert_called_once_with()
    mock_get_client.return_value.open_sftp.return_value.put.assert_called_once()
    mock_get_client.return_value.open_sftp.return_value.close.assert_called_once_with()
    mock_get_client.return_value.close.assert_called_once_with()

