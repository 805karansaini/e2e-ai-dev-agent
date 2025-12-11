from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from asyncio.subprocess import PIPE, create_subprocess_exec
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from loguru import logger

from .models import TaskPayload

USE_SCRIPT = True


class ClineExecutor:
    """Execute the CLINE CLI with a prepared prompt."""

    def __init__(
        self,
        cli_bin: str,
        extra_args: Optional[list[str]] = None,
        workdir: Optional[str] = None,
        on_output: Callable[[str, str, str], Awaitable[None]] | None = None,
        timeout_seconds: float = 20 * 60,
        *,
        use_script: bool = False,
        script_path: str | Path | None = None,
    ) -> None:
        self.cli_bin = cli_bin
        self.extra_args = extra_args or []
        self.workdir = workdir
        self._on_output = on_output
        self.timeout_seconds = timeout_seconds
        self.use_script = use_script or USE_SCRIPT
        self.script_path = Path(script_path) if script_path else None

    @property
    def cli_available(self) -> bool:
        return shutil.which(self.cli_bin) is not None

    @staticmethod
    def _default_script_path() -> Path:
        return Path(__file__).resolve().parents[2] / "scripts" / "run_cline_task_v1.sh"

    async def _emit_output(
        self, payload: TaskPayload, stream_name: str, text: str
    ) -> None:
        cleaned = text.rstrip("\r\n")
        if not cleaned:
            return

        logger.info(
            "CLINE {stream} {task_id}: {text}",
            stream=stream_name,
            task_id=payload.task_id,
            text=cleaned,
        )

        if self._on_output is None:
            return

        try:
            await self._on_output(payload.task_id, stream_name, text)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to forward CLINE {stream} output for task '{task_id}'.",
                stream=stream_name,
                task_id=payload.task_id,
            )

    async def _maybe_parse_json(
        self,
        line: str,
        on_json: Callable[[dict[str, Any]], Awaitable[None]] | None,
    ) -> None:
        if on_json is None:
            return

        candidate = line.strip()
        if not candidate.startswith("{"):
            return

        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                await on_json(obj)
                return
        except ValueError:
            pass

        # Heuristic: detect completion_result in malformed/multi-line JSON.
        if "completion_result" in candidate and '"text"' in candidate:
            match = re.search(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"', candidate)
            if match:
                extracted = match.group(1)
                try:
                    decoded = bytes(extracted, "utf-8").decode("unicode_escape")
                except Exception:
                    decoded = extracted
                await on_json({"say": "completion_result", "text": decoded})

    @staticmethod
    def _normalize_summary(text: str) -> str:
        # Convert escaped newlines to real ones for readability.
        return text.replace("\\n", "\n").strip()

    async def _stream_reader(
        self,
        payload: TaskPayload,
        stream_name: str,
        stream: asyncio.StreamReader | None,
        on_json: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        if stream is None:
            return

        buffer = ""
        pending_text: str | None = None
        while not stream.at_eof():
            chunk = await stream.read(1024)
            if not chunk:
                break

            # Replace carriage returns so we surface progress updates too.
            buffer += chunk.decode(errors="replace").replace("\r", "\n")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                await self._emit_output(payload, stream_name, line)

                # Reset cached text at the start of a new JSON object so that
                # we only associate a text field with the subsequent lines from
                # the same message.
                if re.match(r"^\s*{", line):
                    pending_text = None

                if '"text"' in line and pending_text is None:
                    match = re.search(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"', line)
                    if match:
                        try:
                            pending_text = (
                                bytes(match.group(1), "utf-8")
                                .decode("unicode_escape")
                                .strip()
                            )
                        except Exception:
                            pending_text = match.group(1)

                if "completion_result" in line and on_json is not None:
                    text_for_completion = pending_text
                    if text_for_completion is None:
                        match = re.search(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"', line)
                        if match:
                            try:
                                text_for_completion = (
                                    bytes(match.group(1), "utf-8")
                                    .decode("unicode_escape")
                                    .strip()
                                )
                            except Exception:
                                text_for_completion = match.group(1)
                    if text_for_completion:
                        await on_json(
                            {"say": "completion_result", "text": text_for_completion}
                        )
                        pending_text = None

                await self._maybe_parse_json(line, on_json)

        if buffer:
            await self._emit_output(payload, stream_name, buffer)
            await self._maybe_parse_json(buffer, on_json)

    async def execute(self, prompt: str, payload: TaskPayload) -> None:
        if not self.cli_available:
            raise RuntimeError(
                f"CLINE CLI binary '{self.cli_bin}' not found in PATH; cannot start task."
            )

        script_log_dir = Path(__file__).resolve().parents[2] / "script_log"
        script_log_dir.mkdir(parents=True, exist_ok=True)
        raw_task_id = payload.task_id or "unknown"
        safe_task_id = re.sub(r"[^A-Za-z0-9._-]", "_", raw_task_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_log_path = script_log_dir / f"cline_{timestamp}_{safe_task_id}.log"

        env = os.environ.copy()
        env.update(
            {
                "TASK_ID": raw_task_id,
                "TASK_REPO_URL": payload.repo_url,
                "TASK_BASE_BRANCH": payload.base_branch,
                "DEBUG": "1",
                "SCRIPT_LOG_DIR": str(script_log_dir),
                "CLINE_STREAM_LOG_PATH": str(default_log_path),
            }
        )

        completion: dict[str, Any] = {"summary": None, "emitted": False}

        async def handle_json(obj: dict[str, Any]) -> None:
            say = obj.get("say")
            if say == "completion_result":
                logger.warning("CLINE completion_result: {payload}", payload=obj)

                text = obj.get("text") or obj.get("content")
                if isinstance(text, str):
                    normalized = self._normalize_summary(text)
                    completion["summary"] = normalized
                    if not completion["emitted"]:
                        await self._emit_output(payload, "SUMMARY", normalized)
                        completion["emitted"] = True

        if self.use_script:
            script = self.script_path or self._default_script_path()
            if not script.exists():
                raise RuntimeError(f"Cline script not found at {script}")
            if not os.access(script, os.X_OK):
                raise RuntimeError(f"Cline script is not executable: {script}")

            command = [
                str(script),
                prompt,
                *self.extra_args,
            ]
        else:
            command = [
                self.cli_bin,
                *self.extra_args,
                "-y",
                "--mode",
                "act",
                "-F",
                "json",
                prompt,
            ]

        logger.info("Launching CLINE CLI (headless): {}\n\n", " ".join(command))

        try:
            process = await create_subprocess_exec(
                *command, stdout=PIPE, stderr=PIPE, cwd=self.workdir, env=env
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"CLINE CLI binary '{self.cli_bin}' not found in PATH"
            ) from exc

        stdout_task = asyncio.create_task(
            self._stream_reader(payload, "STDOUT", process.stdout, handle_json)
        )
        stderr_task = asyncio.create_task(
            self._stream_reader(payload, "STDERR", process.stderr, handle_json)
        )

        try:
            returncode = await asyncio.wait_for(
                process.wait(), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(
                "CLINE task '{task_id}' exceeded {timeout}s; terminating.",
                task_id=payload.task_id,
                timeout=self.timeout_seconds,
            )
            process.kill()
            returncode = await process.wait()
        finally:
            await asyncio.gather(stdout_task, stderr_task)

        logger.info(
            "CLINE task '{task_id}' completed with return code {returncode}",
            task_id=payload.task_id,
            returncode=returncode,
        )

        summary = completion.get("summary")

        if summary and not completion.get("emitted"):
            await self._emit_output(payload, "SUMMARY", str(summary))

        if returncode != 0:
            # Some CLINE runs may finish work but return a non-zero code.
            # If we observed a completion_result/summary, downgrade to warning.
            if summary:
                logger.warning(
                    "CLINE CLI exited with status {status} for task '{task_id}', "
                    "but a completion summary was received; treating as success.",
                    status=returncode,
                    task_id=payload.task_id,
                )
                logger.info(
                    "CLINE task '{task_id}' summary:\n{summary}",
                    task_id=payload.task_id,
                    summary=summary,
                )
                return

            raise RuntimeError(
                f"CLINE CLI exited with status {returncode} "
                f"for task '{payload.task_id}'"
            )

        logger.info(
            "CLINE task '{task_id}' completed successfully.", task_id=payload.task_id
        )
        if summary:
            logger.info(
                "CLINE task '{task_id}' summary:\n{summary}",
                task_id=payload.task_id,
                summary=summary,
            )


__all__ = ["ClineExecutor"]
