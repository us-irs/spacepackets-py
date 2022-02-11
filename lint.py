#!/usr/bin/env python3
import os
import sys


def main():
    exclude_dirs_flag = ""
    if not os.path.exists("setup.cfg"):
        exclude_dirs_flag = (
            "--exclude .git,__pycache__,docs/conf.py,old,build,dist,venv"
        )
    additional_flags_both_steps = "--count --statistics"
    additional_flags_first_step = "--select=E9,F63,F7,F82 --show-source"
    flake8_first_step_cmd = (
        f"flake8 . {additional_flags_both_steps} "
        f"{additional_flags_first_step} {exclude_dirs_flag}"
    )
    status = os.system(flake8_first_step_cmd)
    if os.name == "nt":
        if status != 0:
            print(f"Flake8 linter errors with status {status}")
    else:
        if os.WEXITSTATUS(status) != 0:
            print(f"Flake8 linter errors with status {status}")
            sys.exit(0)
    additional_flags_second_step = (
        '--exit-zero --max-complexity=10 --per-file-ignores="__init__.py:F401"'
    )
    if not os.path.exists("setup.cfg"):
        additional_flags_second_step += " --max-line-length=100"
    flake8_second_step_cmd = (
        f"flake8 . {additional_flags_both_steps}  {additional_flags_second_step}"
        f" {exclude_dirs_flag}"
    )
    os.system(flake8_second_step_cmd)


if __name__ == "__main__":
    main()
