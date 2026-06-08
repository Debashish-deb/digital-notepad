#!/usr/bin/env python3
"""
Snakemake launcher with friendly live progress for biologists.

- Hides shell noise and most technical warnings from the live panel by default.
- Shows plain-language status per sample/job on stderr.
- Full technical output still goes to the Snakemake log file (stdout).
"""

import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from log_humanize import (  # noqa: E402
    format_live_prefix,
    format_submit_line,
    friendly_log_enabled,
    humanize_line,
    is_bash_noise,
    is_progress_bar,
    progress_percent,
)

VERBOSE = os.environ.get("PIPELINE_VERBOSE_LOG", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _debug(msg: str) -> None:
    if VERBOSE:
        print(f"       {msg}", file=sys.stderr)
        sys.stderr.flush()


# Prevent SLURM_NTASKS_PER_GPU from breaking GPU job submission on LUMI.
if "SLURM_NTASKS_PER_GPU" in os.environ:
    try:
        del os.environ["SLURM_NTASKS_PER_GPU"]
        _debug("Adjusted cluster GPU settings for this site.")
    except Exception:
        pass

HAS_SQUEUE = shutil.which("squeue") is not None


def check_job_active(job_id: str) -> bool:
    if not HAS_SQUEUE:
        return False
    try:
        res = subprocess.run(
            ["squeue", "-j", str(job_id)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return str(job_id) in res.stdout
    except Exception:
        return False


def tail_job_log(job_id: str, log_path: str, rule: str, wildcards: str) -> None:
    prefix = format_live_prefix(rule, wildcards)

    for _ in range(120):
        if os.path.exists(log_path):
            break
        time.sleep(0.5)
    else:
        return

    last_pct = -1
    last_pos = 0
    announced = False

    with open(log_path, "r", encoding="utf-8", errors="replace", newline="\n") as handle:
        while True:
            handle.seek(last_pos)
            has_new_data = False

            while True:
                line = handle.readline()
                if not line:
                    break

                if not line.endswith("\n") and check_job_active(job_id):
                    break

                last_pos = handle.tell()
                has_new_data = True

                parts = [p.strip() for p in line.split("\r") if p.strip()]
                if not parts:
                    continue

                sub_line = parts[-1]

                if is_bash_noise(sub_line):
                    continue

                if is_progress_bar(sub_line):
                    pct = progress_percent(sub_line)
                    if pct is not None:
                        if pct == 0 or pct == 100 or (pct % 20 == 0 and pct != last_pct):
                            print(
                                f"  ▶ LIVE  {prefix}",
                                file=sys.stderr,
                            )
                            print(
                                f"         Progress: {pct}% complete",
                                file=sys.stderr,
                            )
                            sys.stderr.flush()
                            last_pct = pct
                    continue

                friendly = humanize_line(sub_line)
                if not friendly:
                    if VERBOSE:
                        friendly = sub_line
                    else:
                        continue

                if not announced:
                    print(f"  ▶ LIVE  {prefix}", file=sys.stderr)
                    announced = True

                print(f"         {friendly}", file=sys.stderr)
                sys.stderr.flush()

            if not check_job_active(job_id) and not has_new_data:
                break

            time.sleep(5)


original_Popen = subprocess.Popen


def _format_resources(arg_list: list[str]) -> str:
    cpus = "1"
    mem = ""
    gpus = ""

    i = 0
    while i < len(arg_list):
        arg = arg_list[i]

        def get_val(flag: str, next_i: int) -> tuple[str, int]:
            if "=" in flag:
                return flag.split("=", 1)[1], next_i
            if next_i < len(arg_list):
                return arg_list[next_i], next_i + 1
            return "", next_i

        if arg == "-c" or arg.startswith("--cpus-per-task"):
            val, i = get_val(arg, i + 1)
            cpus = val
        elif arg.startswith("--mem"):
            val, i = get_val(arg, i + 1)
            try:
                digits = "".join(c for c in val if c.isdigit())
                if digits:
                    val_mb = int(digits)
                    val = f"{val_mb / 1024:.1f}G" if val_mb > 1000 else f"{val_mb}M"
            except Exception:
                pass
            mem = val
        elif arg.startswith("--gpus"):
            val, i = get_val(arg, i + 1)
            gpus = val
        else:
            i += 1

    parts = [f"{cpus} CPU"]
    if mem:
        parts.append(mem)
    if gpus:
        parts.append(f"{gpus} GPU")
    return ", ".join(parts)


def _parse_sbatch_comment(arg_list: list[str]) -> tuple[str, str]:
    rule = "unknown"
    wildcards = ""

    i = 0
    while i < len(arg_list):
        arg = arg_list[i]
        if arg.startswith("--comment"):
            if "=" in arg:
                val = arg.split("=", 1)[1]
                i += 1
            elif i + 1 < len(arg_list):
                val = arg_list[i + 1]
                i += 2
            else:
                i += 1
                continue

            if val.startswith("rule_"):
                part = val[5:]
                if "_wildcards_" in part:
                    rule, wildcards = part.split("_wildcards_", 1)
                else:
                    rule = part
            continue
        i += 1

    return rule, wildcards


class WrappedPopen(original_Popen):
    def __init__(self, args, *nargs, **kwargs):
        env = kwargs.get("env")
        if env is not None:
            if "SLURM_NTASKS_PER_GPU" in env:
                env = dict(env)
                del env["SLURM_NTASKS_PER_GPU"]
                kwargs["env"] = env
        elif "SLURM_NTASKS_PER_GPU" in os.environ:
            try:
                del os.environ["SLURM_NTASKS_PER_GPU"]
            except Exception:
                pass

        new_args = args
        if isinstance(args, str):
            new_args = re.sub(r"--ntasks-per-gpu[=\s]+\d+", "", args)
            new_args = re.sub(r"--gpus=([a-zA-Z0-9_:]+)", r"--gpus-per-node=\1", new_args)
            new_args = re.sub(r"--gpus\s+([a-zA-Z0-9_:]+)", r"--gpus-per-node \1", new_args)
        elif isinstance(args, (list, tuple)):
            rebuilt: list = []
            skip = 0
            for i, arg in enumerate(args):
                if skip > 0:
                    skip -= 1
                    continue
                arg_str = arg.decode("utf-8") if isinstance(arg, bytes) else str(arg)

                if arg_str == "--ntasks-per-gpu":
                    skip = 1 if i + 1 < len(args) else 0
                    continue
                if arg_str.startswith("--ntasks-per-gpu="):
                    continue
                if arg_str == "--gpus":
                    rebuilt.append("--gpus-per-node")
                    continue
                if arg_str.startswith("--gpus="):
                    rebuilt.append(f"--gpus-per-node={arg_str.split('=', 1)[1]}")
                    continue

                rebuilt.append(arg)
            new_args = type(args)(rebuilt)

        self._is_sbatch = False
        if isinstance(new_args, (list, tuple)) and new_args and "sbatch" in str(new_args[0]):
            self._is_sbatch = True
        elif isinstance(new_args, str) and "sbatch" in new_args:
            self._is_sbatch = True

        self._cleaned_args = new_args

        if self._is_sbatch and friendly_log_enabled():
            try:
                if isinstance(new_args, (list, tuple)):
                    arg_list = [
                        a.decode("utf-8", errors="replace") if isinstance(a, bytes) else str(a)
                        for a in new_args
                    ]
                else:
                    import shlex

                    arg_list = shlex.split(str(new_args))

                rule, wildcards = _parse_sbatch_comment(arg_list)
                resources = _format_resources(arg_list)
                print(format_submit_line(rule, wildcards, resources), file=sys.stderr)
                sys.stderr.flush()
            except Exception:
                pass

        super().__init__(new_args, *nargs, **kwargs)

    def communicate(self, input=None, timeout=None):
        stdout, stderr = super().communicate(input=input, timeout=timeout)

        if getattr(self, "_is_sbatch", False):
            out_str = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else str(stdout or "")
            err_str = stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else str(stderr or "")

            if self.returncode != 0:
                print("  ▶ QUEUE  Could not submit this job to the cluster.", file=sys.stderr)
                if friendly_log_enabled():
                    if err_str.strip():
                        print(f"         {err_str.strip()}", file=sys.stderr)
                else:
                    print(f"         Exit code: {self.returncode}", file=sys.stderr)
                    if out_str.strip():
                        print(f"         {out_str.strip()}", file=sys.stderr)
                    if err_str.strip():
                        print(f"         {err_str.strip()}", file=sys.stderr)
                sys.stderr.flush()
            else:
                job_id = out_str.strip()
                args = getattr(self, "_cleaned_args", self.args)

                if isinstance(args, (list, tuple)):
                    arg_list = [
                        a.decode("utf-8", errors="replace") if isinstance(a, bytes) else str(a)
                        for a in args
                    ]
                else:
                    import shlex

                    try:
                        arg_list = shlex.split(str(args))
                    except Exception:
                        arg_list = str(args).split()

                output_arg = None
                rule = "unknown"
                wildcards = ""

                i = 0
                while i < len(arg_list):
                    arg = arg_list[i]

                    if arg == "-o" or arg.startswith("--output"):
                        if "=" in arg:
                            output_arg = arg.split("=", 1)[1]
                            i += 1
                        elif i + 1 < len(arg_list):
                            output_arg = arg_list[i + 1]
                            i += 2
                        else:
                            i += 1
                    elif arg.startswith("--comment"):
                        if "=" in arg:
                            val = arg.split("=", 1)[1]
                            i += 1
                        elif i + 1 < len(arg_list):
                            val = arg_list[i + 1]
                            i += 2
                        else:
                            i += 1
                            continue

                        if val.startswith("rule_"):
                            part = val[5:]
                            if "_wildcards_" in part:
                                rule, wildcards = part.split("_wildcards_", 1)
                            else:
                                rule = part
                    else:
                        i += 1

                if output_arg and job_id:
                    log_path = output_arg.replace("%j", job_id)
                    threading.Thread(
                        target=tail_job_log,
                        args=(job_id, log_path, rule, wildcards),
                        daemon=True,
                    ).start()

        return stdout, stderr


subprocess.Popen = WrappedPopen

original_submit = concurrent.futures.ThreadPoolExecutor.submit


def debug_submit(self, fn, *args, **kwargs):
    def wrapped_fn(*fargs, **fkwargs):
        try:
            return fn(*fargs, **fkwargs)
        except Exception as exc:
            print("\n  ▶ ERROR  An unexpected error occurred in the workflow engine.", file=sys.stderr)
            if VERBOSE:
                traceback.print_exc(file=sys.stderr)
            else:
                print(f"         {exc}", file=sys.stderr)
            sys.stderr.flush()
            raise exc

    return original_submit(self, wrapped_fn, *args, **kwargs)


concurrent.futures.ThreadPoolExecutor.submit = debug_submit

try:
    import snakemake_executor_plugin_slurm.accounts

    snakemake_executor_plugin_slurm.accounts.test_account = lambda account, logger: None

    import snakemake_executor_plugin_slurm

    snakemake_executor_plugin_slurm.test_account = lambda account, logger: None
    _debug("Cluster account check bypassed for this environment.")
except Exception as exc:
    _debug(f"Could not patch SLURM account validation: {exc}")

try:
    from snakemake.cli import main
except ImportError:
    from snakemake import main

if __name__ == "__main__":
    sys.argv[0] = "snakemake"
    main()
