import asyncio
import logging
import threading
from typing import Optional
from config import config
from server import create_agent_server
from livekit.agents import AgentServer

logger = logging.getLogger(__name__)


class AgentWorkerManager:
    """Manages running the LiveKit Agent Server in a background thread."""

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[AgentServer] = None
        self._run_task: Optional[asyncio.Task] = None
        self._is_running = False

    def start(self) -> None:
        """Starts the agent server in a dedicated background thread."""
        if self._is_running:
            logger.warning("Agent worker is already running.")
            return

        # Check LiveKit credentials before attempting to start
        try:
            config.validate_livekit()
        except ValueError as e:
            logger.warning(
                "LiveKit credentials not configured. Agent worker will not start: %s",
                e,
            )
            return

        logger.info("Starting LiveKit Agent Worker in background thread...")
        self._is_running = True
        self._thread = threading.Thread(
            target=self._run_worker_loop,
            name="LiveKitAgentWorkerThread",
            daemon=True,
        )
        self._thread.start()

    def _run_worker_loop(self) -> None:
        """Worker thread entrypoint with its own asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._server = create_agent_server()
            devmode = config.environment.lower() == "development"

            async def _run() -> None:
                logger.info(
                    "LiveKit Agent Server running (devmode=%s, agent_name=%s)",
                    devmode,
                    config.agent_name,
                )
                await self._server.run(devmode=devmode)

            self._run_task = self._loop.create_task(_run())
            self._loop.run_until_complete(self._run_task)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("LiveKit Agent Worker encountered an error: %s", e, exc_info=True)
        finally:
            self._is_running = False
            try:
                # Cancel pending tasks
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            self._loop.close()
            logger.info("LiveKit Agent Worker thread stopped.")

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stops the background agent server."""
        if not self._is_running or not self._loop or not self._server:
            return

        logger.info("Stopping LiveKit Agent Worker background thread...")
        try:
            # Schedule aclose on the worker loop
            async def _shutdown() -> None:
                if self._server:
                    await self._server.aclose()
                if self._run_task and not self._run_task.done():
                    self._run_task.cancel()

            future = asyncio.run_coroutine_threadsafe(_shutdown(), self._loop)
            future.result(timeout=timeout)
        except Exception as e:
            logger.warning("Error while closing agent server: %s", e)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        self._is_running = False
        logger.info("LiveKit Agent Worker stopped successfully.")


# Global singleton instance
agent_worker_manager = AgentWorkerManager()
