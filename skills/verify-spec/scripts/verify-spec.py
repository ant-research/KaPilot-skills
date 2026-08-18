"""
verify-spec: Run Kani verification on generated specs and analyze results.

This script runs Kani verification on specified harnesses and:
1. Checks for syntax errors
2. Parses verification results (failed checks, counterexamples)
3. Reports success or detailed failure messages

Usage:
    python3 verify-spec.py --harnesses <harn1,harn2,...>
"""

import datetime
import os
from pathlib import Path
import re
import shlex
import click
import subprocess
from dotenv import load_dotenv

CLAUDE_DIR = Path(__file__).resolve().parents[3]


def retrieve_result_fldr():
    load_dotenv(CLAUDE_DIR / ".env")
    return os.getenv("RESULT_FLDR", "")


def separate_checks_and_ces(text: str):
    ce_search_s = "Concrete playback unit test for "
    harn_check_s, left_s = text.split("SUMMARY:")
    harn_check_s = harn_check_s.strip()
    ce_list = []
    for ce in left_s.split(ce_search_s)[1:]:
        ce = ce.strip()
        if "INFO: " in ce:
            ce = ce.split("INFO: ")[0].strip()
        ce_list += [f"{ce_search_s}{ce}\n\n"]
    return harn_check_s, ce_list


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
        # cmd = f"./scripts/run-kani.sh --path . --kani-args {harn_s} --harness-timeout {timeout}"
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


def run_cmd(cmd: str, work_dir: str = "./"):
    print(f"run cmd: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=work_dir, capture_output=True)
    return res.returncode, res.stdout.decode().strip(), res.stderr.decode().strip()


def sep_check_res_one_harn(kani_out_one_harn: str):
    """get failed checks in one harness"""
    pat = r"^Check\s+\d+:[\s\S]*?(?=\n^Check\s+\d+:|\Z)"
    checks = re.findall(pat, kani_out_one_harn, flags=re.MULTILINE)
    checks = list(set(checks))
    return checks


def _get_failed_checks(kani_out_one_harn: str):
    """get failed checks in one harness"""
    fail_checks = []
    checks = sep_check_res_one_harn(kani_out_one_harn)
    for check in checks:
        if "Status: FAILURE" in check:
            fail_checks += [check]
    return fail_checks


def _get_ces_for_failed_checks(ce_list: list, fail_checks: list):
    """get counterexamples for failed checks in one harness"""
    ce_fail_checks = []
    desc_pat = r'- Description: "(.+)"'
    for check in fail_checks:
        if m := re.search(desc_pat, check, flags=re.MULTILINE | re.DOTALL):
            desc = m.group(1).strip()
            ce_fail_checks += [ce for ce in ce_list if rf': "{desc}"' in ce]
    return ce_fail_checks


def no_prfx(ident_path: str):
    return ident_path.split("::")[-1]


def triage_check_results(kani_out: str):
    check_harns = kani_out.split("Checking harness ")[1:]
    fail_checks_harn, succ_checks_harn = {}, {}
    for harn_check_s in check_harns:
        harn_check_s, ce_list = separate_checks_and_ces(harn_check_s)
        harn_name_path = harn_check_s.split("\n")[0][:-3]
        if fail_checks := _get_failed_checks(harn_check_s):
            counterexamples = _get_ces_for_failed_checks(ce_list, fail_checks)
            fail_checks_s, ce_s = "".join(fail_checks), "".join(counterexamples)
            fail_checks_harn[harn_name_path] = (fail_checks_s, ce_s)
        else:
            succ_checks_harn[harn_name_path] = ""
    return fail_checks_harn, succ_checks_harn


def _get_fail_prop_errs(fail_checks_harn: dict, succ_check_harn: dict):
    CE_DESC = """
The elements in `concrete_vals` follow the assignment order of nondeterministic variables during the Kani harness execution. Each element records the concrete value assigned to one nondeterministic variable, stored in raw byte form. For example, on a 64-bit little-endian system, `vec![42, 0, 0, 0, 0, 0, 0, 0]` represents the usize value `42`.

"""
    msg = ""
    if len(fail_checks_harn) == 0:
        return msg
    for harn_name_path, (fail_check_s, ce_s) in fail_checks_harn.items():
        harn_name_path = no_prfx(harn_name_path)
        msg += f"### Failed checks on harness `{harn_name_path}`:\n"
        msg += f"```text\n{fail_check_s}\n```\n"
        if ce_s:
            msg += f"\nCounterexamples for failed checks:\n{CE_DESC}`````text\n{ce_s}\n`````\n"
    if len(succ_check_harn) > 0:
        msg += "Below are harnesses that pass Kani. Differences from the failing harnesses above can inform corrections to the specifications.\n"
        msg += "## Successful Checks\n"
        for harn_name_path, harn_code in succ_check_harn.items():
            harn_name_path = no_prfx(harn_name_path)
            msg += f"Harness `{harn_name_path}`:\n"
            msg += f"```rust\n{harn_code}\n```\n"
    return msg


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
    # _ret, out, _err = run_kani(work_dir, harnesses=harnesses_list)
    cmd = _get_kani_cmd(work_dir, harnesses=harnesses_list, timeout=timeout)
    _ret, out, _err = run_cmd(cmd, work_dir)

    # save raw output
    with open(
        os.path.expanduser(f"{result_fldr}/{now_ts}__kani_vrf_out.txt"), "w"
    ) as f:
        f.write(f"kani cmd: {cmd}\n\n")
        f.write(f"---stdout:\n{out}\n\n")
        f.write(f"---stderr:\n{_err}\n")

    if _is_syntax_err(out):
        print("Syntax Errors detected.")
        print(_get_err_msgs(out, 5))
    else:
        fail_harns, succ_harns = triage_check_results(out)
        err_msg = _get_fail_prop_errs(fail_harns, succ_harns)
        if err_msg:
            print(f"Syntax pass, but Verify Failed. Below are messages:\n {err_msg}")
        else:
            print(
                "Verify Success. All generated specs are correct when checked with all harnesses."
            )


if __name__ == "__main__":
    main()
