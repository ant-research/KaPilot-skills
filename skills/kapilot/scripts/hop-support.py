#!/usr/bin/env python3
"""Deterministic KaPilot staging, command bridging, rendering, and publishing.

The original Kani scripts are retained unchanged under assets/. They load
RESULT_FLDR from a carrier-specific location; this adapter supplies the value
from the staged .claude/.env file without depending on that install layout.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import yaml


PACKAGE = Path(__file__).resolve().parent.parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Path must be workspace-relative without '..': {value}")
    return path


def inside(path: Path, root: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path is outside the permitted directory: {path}")
    return path


def prepare(data: dict) -> dict:
    workspace = Path(data["workspace_dir"]).resolve()
    source_relative = relative_path(data["file_path"])
    save_relative = relative_path(data["save_dir_root"])
    source = inside(workspace / source_relative, workspace)
    save_root = inside(workspace / save_relative, workspace)
    if not source.is_file() or (save_root.exists() and not save_root.is_dir()):
        raise ValueError("The source must exist and save_dir_root must be a directory path")
    if not data["target_func_name"] or int(data["line_number"]) < 1:
        raise ValueError("The function name must be nonempty and the line number positive")
    scratch = Path(data["scratch_root"]).resolve()
    if scratch.exists():
        raise FileExistsError("The staging directory already exists; start a fresh run")
    # Dereference symlinks so editing the copy cannot edit the original file.
    default_ignore = shutil.ignore_patterns(".git", ".hopstate", ".hoplog",
                                           "target", "node_modules", ".venv")
    scratch_parent = scratch.relative_to(workspace).parts[0] if scratch.is_relative_to(workspace) else None

    def ignore(directory: str, names: list[str]) -> set[str]:
        excluded = set(default_ignore(directory, names))
        if Path(directory).resolve() == workspace and scratch_parent:
            excluded.add(scratch_parent)
        return excluded

    shutil.copytree(workspace, scratch, symlinks=False, ignore=ignore)
    (scratch / save_relative).mkdir(parents=True, exist_ok=True)
    command = ["bash", str(PACKAGE / "scripts/mk-result-dir.sh"),
               str(scratch / source_relative), str(data["line_number"]),
               str(scratch / save_relative)]
    run = subprocess.run(command, cwd=scratch, text=True, capture_output=True)
    if run.returncode != 0 or not run.stdout.strip():
        raise RuntimeError(f"mk-result-dir failed: {run.stdout}\n{run.stderr}")
    staged_result = inside(Path(run.stdout.strip()), scratch)
    if not staged_result.is_dir():
        raise RuntimeError("mk-result-dir did not create the reported directory")
    result_relative = staged_result.relative_to(scratch)
    env_file = scratch / ".claude/.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(f"RESULT_FLDR={staged_result}\n")
    job = {"workspace": str(workspace), "scratch_root": str(scratch),
           "file_path": str(source_relative), "staged_file_path": str(scratch/source_relative),
           "target_func_name": data["target_func_name"], "line_number": int(data["line_number"]),
           "result_fldr": str(staged_result), "result_relative": str(result_relative),
           "final_result_fldr": str(workspace/result_relative), "original_sha256": digest(source)}
    job_path = Path(data["job_path"])
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2))
    return {**job, "job_path": str(job_path), "preparation_stdout": run.stdout,
            "preparation_stderr": run.stderr}


def load_job(data: dict) -> dict:
    return json.loads(Path(data["job_path"]).read_text())


def run_kani(data: dict, mode: str) -> dict:
    job = load_job(data)
    names = data["harness_name_list"]
    if not names or any(not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9:]*", n) for n in names):
        raise ValueError("At least one valid Rust harness name is required")
    scratch = Path(job["scratch_root"])
    result_dir = inside(Path(job["result_fldr"]), scratch)
    env_value = (scratch/".claude/.env").read_text().strip()
    if env_value != f"RESULT_FLDR={result_dir}":
        raise ValueError("The staged RESULT_FLDR compatibility file is inconsistent")
    environment = os.environ.copy()
    environment["RESULT_FLDR"] = str(result_dir)
    script_name = "kani-compile" if mode == "compile" else "verify-spec"
    script = PACKAGE/"assets"/script_name/"scripts"/(script_name+".py")
    command = [sys.executable, str(script), "--work-dir", str(scratch),
               "--harnesses", ",".join(names)]
    run = subprocess.run(command, cwd=scratch, env=environment,
                         text=True, capture_output=True)
    pattern = "*__kani_harn_out.txt" if mode == "compile" else "*__kani_vrf_out.txt"
    logs = sorted(result_dir.glob(pattern), key=lambda p: p.stat().st_mtime_ns)
    raw = logs[-1].read_text() if logs else ""
    syntax_error = "Syntax Errors detected" in run.stdout or bool(
        re.search(r"^(?:error: |error\[)", raw, re.MULTILINE))
    covered = re.findall(r"Checking harness\s+([^\s]+)", raw)
    all_covered = all(any(c.rstrip(':.').split('::')[-1] == n.split('::')[-1]
                          for c in covered) for n in names)
    if mode == "compile":
        successful = run.returncode == 0 and "Syntax Correct." in run.stdout and not syntax_error
        status = "Syntax Correct" if successful else "Syntax Errors detected"
    else:
        # The source script can print success for an empty parsed harness list.
        # Retain its output verbatim, but require actual requested harness coverage.
        successful = (run.returncode == 0 and "Verify Success" in run.stdout
                      and not syntax_error and all_covered
                      and "Status: FAILURE" not in raw)
        status = "Verify Success" if successful else (
            "Syntax Errors detected" if syntax_error else "Verify Failed")
    return {"status": status, "successful": successful, "returncode": run.returncode,
            "stdout": run.stdout, "stderr": run.stderr, "raw_output": raw,
            "requested_harnesses": names, "covered_harnesses": covered,
            "coverage_complete": all_covered,
            "result_text": run.stdout + ("\n"+run.stderr if run.stderr else "")}


def fill(template: str, values: dict) -> str:
    pattern = re.compile(r"\{\{([^}]+)\}\}")
    missing = {match.group(1) for match in pattern.finditer(template)} - values.keys()
    if missing:
        raise ValueError(f"Unfilled template placeholders: {sorted(missing)}")
    # Replace only template tokens, never token-like text inside inserted Rust.
    return pattern.sub(lambda match: str(values[match.group(1)]), template)


def render(data: dict) -> dict:
    job = load_job(data)
    events = data["execution_log"]
    template = (PACKAGE/"templates/report.md").read_text()
    start = template.index("Record each subagent and skill result")
    end = template.index("## Final Artifacts")
    entries = []
    for index, event in enumerate(events, 1):
        text = event["result_text"]
        fence = "`" * max(3, max((len(x) for x in re.findall(r"`+", text)), default=0)+1)
        entries.append(f"### Step {index}: {event['executor_name']}\n"
                       f"- Kind: {event['kind']}\n- Round: {event['round']}\n"
                       f"- Status: executed\n- Result:\n\n{fence}text\n{text}\n{fence}\n")
    template = template[:start]+"\n".join(entries)+"\n"+template[end:]
    values = {"target_func_name": job["target_func_name"], "file_path": job["file_path"],
              "line_num": job["line_number"], "result_fldr": job["final_result_fldr"],
              "final_verification_status": data["final_status"],
              "total_verify_rounds": data["total_verify_rounds"],
              "total_precheck_rounds": data["total_precheck_rounds"],
              "final_verification_target": json.dumps(data["verification_target"], ensure_ascii=False, indent=2),
              "final_safety_requirements": data["safety_requirements"],
              "final_verification_artifacts": data["final_artifacts"],
              "final_target_function_code": data["final_target_code"],
              "final_harnesses_code": data["final_harness_code"],
              "final_verification_details": data["final_details"]}
    report_text = fill(template, values)
    artifact_values = {"target function name": job["target_func_name"],
                       "file path": job["file_path"], "line number": job["line_number"],
                       "RESULT_FLDR": job["final_result_fldr"],
                       "final verification status: fail/success": data["final_status"],
                       "final verification artifacts": data["final_artifacts"],
                       "final target function code": data["final_target_code"]}
    artifact_text = fill((PACKAGE/"templates/spec.md").read_text(), artifact_values)
    result_dir = Path(job["result_fldr"])
    (result_dir/"execution_report.md").write_text(report_text)
    (result_dir/data["final_status"]).write_text(artifact_text)
    return {"report_text": report_text, "artifact_text": artifact_text,
            "report_path": str(Path(job["result_relative"])/"execution_report.md"),
            "artifact_path": str(Path(job["result_relative"])/data["final_status"])}


def publish(data: dict) -> dict:
    job = load_job(data)
    workspace = Path(job["workspace"])
    original = inside(workspace/job["file_path"], workspace)
    staged_source = inside(Path(job["staged_file_path"]), Path(job["scratch_root"]))
    staged_result = inside(Path(job["result_fldr"]), Path(job["scratch_root"]))
    destination = inside(workspace/job["result_relative"], workspace)
    if digest(original) != job["original_sha256"]:
        raise RuntimeError("Original source changed after staging; refusing to overwrite it")
    if destination.exists():
        raise FileExistsError("The final result directory already exists; refusing to overwrite it")
    report = staged_result/"execution_report.md"
    artifact = staged_result/data["final_status"]
    if not report.is_file() or not artifact.is_file():
        raise ValueError("The checked final report and artifact must both exist")
    env_file = inside(workspace/".claude/.env", workspace)
    shutil.copytree(staged_result, destination)
    backup = destination/"previous-workspace"
    backup.mkdir()
    shutil.copyfile(original, backup/"target-source")
    if env_file.exists():
        shutil.copyfile(env_file, backup/"compatibility.env")
    try:
        shutil.copyfile(staged_source, original)
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text(f"RESULT_FLDR={destination}\n")
    except Exception:
        shutil.copyfile(backup/"target-source", original)
        if (backup/"compatibility.env").exists():
            shutil.copyfile(backup/"compatibility.env", env_file)
        elif env_file.exists():
            env_file.unlink()
        raise
    return {"report_path": str(Path(job["result_relative"])/"execution_report.md"),
            "artifact_path": str(Path(job["result_relative"])/data["final_status"])}


def main() -> None:
    try:
        # HopSpec str(structured_value) yields YAML, while results are JSON.
        data = yaml.safe_load(sys.stdin)
        mode = sys.argv[1]
        if mode == "prepare":
            result = prepare(data)
        elif mode in ("compile", "verify"):
            result = run_kani(data, mode)
        elif mode == "render":
            result = render(data)
        elif mode == "publish":
            result = publish(data)
        else:
            raise ValueError(f"Unknown operation: {mode}")
        print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
