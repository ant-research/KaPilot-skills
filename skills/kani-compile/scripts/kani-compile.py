"""
kani-compile: Run Kani on specified harnesses and analyze results.

This script runs Kani verification on specified harnesses and:
1. Checks for syntax errors
2. Reports success or detailed failure messages

Usage:
    python3 kani-compile.py --harnesses <harn1,harn2,...>
"""

import datetime
import os
import re
import shlex
import click
import subprocess
from pathlib import Path
from dotenv import load_dotenv

CLAUDE_DIR = Path(__file__).resolve().parents[3]


def retrieve_result_fldr():
    load_dotenv(CLAUDE_DIR / ".env")
    return os.getenv("RESULT_FLDR", "")


def _is_syntax_err(out: str):
    # pat = r"^(?:error: |error\[).*?(?=^(?:error: |error\[))"
    pat = r"^(?:error: |error\[).*?(?=^(?:error: |error\[)|\Z)"
    chunks = re.findall(pat, out, re.MULTILINE | re.DOTALL)
    return len(chunks) > 0


def _get_err_msgs(full_err_msg: str, n: int):
    # pat = r"^(?:error: |error\[).*?(?=^(?:error: |error\[))"
    pat = r"^(?:error: |error\[).*?(?=^(?:error: |error\[)|\Z)"
    chunks = re.findall(pat, full_err_msg, re.MULTILINE | re.DOTALL)

    print(f"get first {min(n, len(chunks))} err msgs:")
    err_msg = "".join([e for e in chunks[0:n]])
    return f"```text\n{err_msg}\n```"


def _get_kani_cmd(
    work_dir: str,
    harnesses: list,
    timeout: int = 1800,
    cmd: str = None,
    unwind: int = None,
):
    harn_s = ""
    for harn in harnesses:
        harn_s += f"--harness {harn} "

    if cmd:
        cmd += f" {harn_s} -Z unstable-options --harness-timeout {timeout}"
        if "manifest-path" not in cmd:
            cmd += f" --manifest-path {os.path.join(work_dir, 'Cargo.toml')}"
    else:
        # For verify-rust-std
        repo_root = _find_verify_rust_std_root(work_dir)
        run_kani_script = repo_root / "scripts" / "run-kani.sh"
        cmd = (
            f"{shlex.quote(str(run_kani_script))} "
            f"--path {shlex.quote(str(repo_root))} "
            f"--kani-args {harn_s} --harness-timeout {timeout}"
        )

    if unwind:
        cmd += f" -Z unstable-options --unwind {unwind} --no-unwinding-checks"
    # counterexample
    # cmd += " -Z concrete-playback --concrete-playback=print "
    return cmd


def run_kani(work_dir: str, harnesses: list = []):
    cmd = _get_kani_cmd(work_dir, harnesses)
    ret, out, err = run_cmd(cmd, work_dir)
    return ret, out, err


def _find_verify_rust_std_root(work_dir: str) -> Path:
    candidates = [Path(work_dir).resolve()]
    candidates.extend(Path(work_dir).resolve().parents)
    candidates.append(Path(__file__).resolve().parents[4])

    for candidate in candidates:
        if (candidate / "scripts" / "run-kani.sh").is_file():
            return candidate

    raise FileNotFoundError(
        "Could not locate verify-rust-std root containing scripts/run-kani.sh"
    )


def run_cmd(cmd: str, work_dir: str = "./"):
    print(f"run cmd: {cmd}")
    print(f"cwd: {work_dir}")
    res = subprocess.run(cmd, shell=True, cwd=work_dir, capture_output=True)
    return res.returncode, res.stdout.decode().strip(), res.stderr.decode().strip()


def no_prfx(ident_path: str):
    return ident_path.split("::")[-1]


@click.command()
@click.option(
    "--work-dir",
    default=".",
    help="working directory to run kani",
)
@click.option(
    "--harnesses",
    help="target harnesses to run, separated by comma",
)
@click.option(
    "--timeout",
    default=1800,
    help="timeout for kani verification in seconds",
)
def main(work_dir: str, harnesses: str, timeout: int):
    now_ts = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    result_fldr = retrieve_result_fldr()

    harnesses_list = harnesses.split(",") if harnesses else []
    cmd = _get_kani_cmd(work_dir, harnesses=harnesses_list, timeout=timeout)
    _ret, out, _err = run_cmd(cmd, work_dir)
    print(f"kani return code: {_ret}")
    # save raw output
    with open(
        os.path.expanduser(f"{result_fldr}/{now_ts}__kani_harn_out.txt"), "w"
    ) as f:
        f.write(f"kani cmd: {cmd}\n\n")
        f.write(out)
        f.write(_err)

    if _is_syntax_err(out):
        print("Syntax Errors detected.")
        print(_get_err_msgs(out, 5))
    else:
        print("Syntax Correct.")


if __name__ == "__main__":
    main()
