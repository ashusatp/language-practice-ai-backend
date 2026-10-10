import ctypes
import os
from config import config
from livekit.agents import AgentServer, JobRequest, cli
from agent import rtc_entrypoint

# Suppress benign AssertionError in LiveKit FfiHandle.__del__ on worker process teardown
try:
    from livekit.rtc._ffi_client import FfiClient, FfiHandle, INVALID_HANDLE

    def _safe_ffi_dispose(self) -> None:
        if self.handle != INVALID_HANDLE and not self._disposed:
            self._disposed = True
            ffi = FfiClient._instance
            if ffi is None or ffi._pid != os.getpid():
                return
            try:
                ffi._ffi_lib.livekit_ffi_drop_handle(ctypes.c_uint64(self.handle))
            except Exception:
                pass

    FfiHandle.dispose = _safe_ffi_dispose
except Exception:
    pass


async def handle_request(req: JobRequest):
    # Accept incoming job requests from LiveKit
    await req.accept()


def create_agent_server() -> AgentServer:
    server = AgentServer(
        ws_url=config.livekit_url,
        api_key=config.livekit_api_key,
        api_secret=config.livekit_api_secret,
    )

    server.rtc_session(
        rtc_entrypoint,
        agent_name=config.agent_name or "ashu-testing-agent",
        on_request=handle_request,
    )


    return server


if __name__ == "__main__":
    server = create_agent_server()
    cli.run_app(server)
