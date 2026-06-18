"""进程辅助工具"""
import subprocess
import asyncio
from typing import Tuple, Optional
import os


def execute_command(
    command: str,
    timeout: int = 30,
    cwd: Optional[str] = None,
    env: Optional[dict] = None
) -> Tuple[int, str, str]:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=proc_env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        return (
            proc.returncode,
            stdout.decode('utf-8', errors='ignore'),
            stderr.decode('utf-8', errors='ignore')
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


async def execute_command_async(
    command: str,
    timeout: int = 30,
    cwd: Optional[str] = None,
    env: Optional[dict] = None
) -> Tuple[int, str, str]:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=proc_env
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
        return (
            proc.returncode,
            stdout.decode('utf-8', errors='ignore'),
            stderr.decode('utf-8', errors='ignore')
        )
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def execute_adb(
    args: str,
    adb_path: str = "adb",
    timeout: int = 30,
    device_id: Optional[str] = None
) -> Tuple[int, str, str]:
    cmd = adb_path
    if device_id:
        cmd += f" -s {device_id}"
    cmd += f" {args}"
    return execute_command(cmd, timeout)
