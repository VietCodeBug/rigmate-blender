"""Antigravity CLI / Python SDK Adapter with safe environment error detection."""

import asyncio
import os
import shutil
import subprocess
from typing import AsyncGenerator, List, Optional
from rigmate.core.quota import QuotaSnapshot, TokenUsage
from rigmate.providers.base import BaseAIProvider, BaseQuotaProvider, ChatMessage, ProviderResponse


class AntigravityProvider(BaseAIProvider, BaseQuotaProvider):
    """
    Adapter interfacing with official Antigravity CLI (`agy`) or Python SDK.
    - Does not speculate flags or APIs if CLI is not present.
    - Explicitly sets state to UNVERIFIED_ENV when running without live CLI or authentication.
    - Strictly avoids extracting internal cookies or tokens; does not enable paid APIs.
    """

    def __init__(self, model: str = "gemini-3.8-flash"):
        self._model = model
        self.cli_path = self._detect_cli_path()
        self.sdk_available = self._detect_sdk()

    @property
    def provider_id(self) -> str:
        return "antigravity"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check whether CLI or Python SDK is callable in the current environment."""
        return bool(self.cli_path or self.sdk_available)

    def _detect_cli_path(self) -> Optional[str]:
        """Detect binary `agy` in system PATH."""
        return shutil.which("agy")

    def _detect_sdk(self) -> bool:
        """Check whether google.antigravity SDK is installed in current Python env."""
        try:
            import google.antigravity  # type: ignore
            return True
        except ImportError:
            return False

    async def generate_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
        timeout_seconds: float = 30.0,
    ) -> ProviderResponse:
        if not self.is_available():
            # Missing CLI or SDK
            return ProviderResponse(
                text=(
                    "[UNVERIFIED_ENV] Antigravity CLI ('agy') or Python SDK ('google.antigravity') "
                    "was not detected in this environment. Please consult HOME_SETUP_GUIDE.md "
                    "or switch to 'Mock Provider' mode in RigMate settings."
                ),
                token_usage=TokenUsage.create(0, 0),
                suggested_actions=["Switch to Mock Provider", "Open Setup Guide"],
                raw_metadata={"status": "UNVERIFIED_ENV", "session_id": session_id},
            )

        last_prompt = messages[-1].content if messages else ""

        # SDK execution pathway
        if self.sdk_available:
            try:
                from google.antigravity import Agent, LocalAgentConfig  # type: ignore
                config = LocalAgentConfig(
                    system_instructions=(
                        "You are RigMate, an AI assistant in Blender assisting non-expert 3D users "
                        "with character rig validation and adjustments targeting Godot Engine."
                    )
                )
                async with Agent(config) as agent:
                    agent_resp = await asyncio.wait_for(
                        agent.chat(last_prompt),
                        timeout=timeout_seconds,
                    )
                    tokens = []
                    async for token in agent_resp:
                        tokens.append(token)
                    full_text = "".join(tokens)
                    return ProviderResponse(
                        text=full_text,
                        token_usage=TokenUsage.create(len(last_prompt) // 3, len(full_text) // 3),
                        suggested_actions=[],
                        raw_metadata={"backend": "sdk", "session_id": session_id},
                    )
            except Exception as e:
                return ProviderResponse(
                    text=f"[Antigravity SDK Error]: {e}",
                    suggested_actions=["Switch to Mock Provider"],
                    raw_metadata={"error": str(e)},
                )

        # CLI pathway
        if self.cli_path:
            try:
                process = await asyncio.create_subprocess_exec(
                    self.cli_path,
                    "--prompt",
                    last_prompt,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
                if process.returncode == 0:
                    out_text = stdout.decode("utf-8", errors="replace")
                    return ProviderResponse(
                        text=out_text,
                        token_usage=TokenUsage.create(len(last_prompt) // 3, len(out_text) // 3),
                        raw_metadata={"backend": "cli", "session_id": session_id},
                    )
                else:
                    err_text = stderr.decode("utf-8", errors="replace")
                    return ProviderResponse(
                        text=f"[CLI Execution Error (exit code {process.returncode})]: {err_text}",
                        suggested_actions=["Check CLI logs"],
                    )
            except asyncio.TimeoutError:
                return ProviderResponse(
                    text=f"[Timeout]: Request to Antigravity CLI exceeded {timeout_seconds}s.",
                    suggested_actions=["Retry", "Cancel"],
                )
            except Exception as e:
                return ProviderResponse(
                    text=f"[CLI Error]: {e}",
                    suggested_actions=["Verify CLI configuration"],
                )

        return ProviderResponse(text="Unable to initialize AI provider.")

    async def stream_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        resp = await self.generate_response(messages, session_id)
        for chunk in resp.text.splitlines(keepends=True):
            yield chunk

    async def fetch_quota_snapshot(self, account_profile: str = "default") -> QuotaSnapshot:
        """
        Fetch quota from Antigravity:
        Currently CLI/SDK lacks a public machine-readable quota API (/usage is interactive TUI).
        Reports 'UNKNOWN' source to prompt user for manual snapshot entry.
        """
        return QuotaSnapshot(
            provider_name="Antigravity",
            model_name=self._model,
            account_profile=account_profile,
            source="UNKNOWN",
            quota_remaining=None,
            quota_total=None,
            quota_unit="requests",
        )
