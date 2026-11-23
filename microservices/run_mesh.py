"""
Microservice Mesh Runner
CLI to run any individual microservice from the 100-service ecosystem or orchestrate the core commerce chain.
"""

import argparse
import importlib.util
import os
import sys
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def find_service_dir(service_id: str) -> Optional[str]:
    clean_sid = service_id.replace("-", "_").lower()
    for entry in os.listdir(BASE_DIR):
        if entry.startswith(clean_sid) and os.path.isdir(os.path.join(BASE_DIR, entry)):
            return os.path.join(BASE_DIR, entry)
    return None


def run_service(service_id: str, port: int = None, host: str = "127.0.0.1"):
    svc_dir = find_service_dir(service_id)
    if not svc_dir:
        print(f"[!] Error: Microservice {service_id} not found in {BASE_DIR}")
        sys.exit(1)

    app_path = os.path.join(svc_dir, "app.py")
    spec = importlib.util.spec_from_file_location("app", app_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    listen_port = port or getattr(mod, "DEFAULT_PORT", 8080)
    print(f"[*] Starting Microservice: {mod.SERVICE_NAME} ({mod.SERVICE_ID}) on http://{host}:{listen_port}")
    uvicorn.run(mod.app, host=host, port=listen_port)


def main():
    parser = argparse.ArgumentParser(description="Run ecosystem microservice")
    parser.add_argument("--service", "-s", default="svc-066", help="Microservice ID (e.g. svc-066, svc-016)")
    parser.add_argument("--port", "-p", type=int, default=None, help="Port override")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")

    args = parser.parse_args()
    run_service(args.service, args.port, args.host)


if __name__ == "__main__":
    from typing import Optional
    main()
