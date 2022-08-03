import subprocess
from typing import List, Dict, Any


def run_shell_cmd(cmd: List[str]):
    result = subprocess.run(cmd, capture_output=True)
    result_text = None
    if result.returncode == 0:
        result_text = result.stdout.decode()
    return result_text


def get_file_size(file_name: str):
    result_text = run_shell_cmd(['stat', '-c' '%s %n', file_name])
    return result_text.split()[0]


def get_img_wxh(file_name: str) -> List[int]:
    result_text = run_shell_cmd(['identify', '-ping', '-format', '"%wx%h"', file_name])
    return list(map(int, result_text.strip("\"").split("x")))


def split_fstring_not_args(f_str_vars: Dict[str, Any], in_fstr: str) -> List[str]:
    """
    Formats an fstring and splits on space. The spaces in any of arguments
    are however preserved.

    subprocess.run likes the split string format best.

    :param f_str_vars: dictionary of arguments to the f string.
    :param cmd: the command including f-string place holders.
    :return: list of input tokens.
    """
    curlied_dict = {"{" + k + "}": str(v) for k,v in f_str_vars.items()}
    rebuilt_cmd = []
    for token in in_fstr.split():
        for k, v in curlied_dict.items():
            token = token.replace(k, v)
        rebuilt_cmd.append(token)
    return rebuilt_cmd


def get_name_decor(w: int, h: int, ext: str):
    return '-{}x{}.{}'.format(w, h, ext)