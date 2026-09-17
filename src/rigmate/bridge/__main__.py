"""Entrypoint khởi chạy Bridge Server bằng command: python -m rigmate.bridge"""

import argparse
import sys
import uvicorn
from rigmate.bridge.server import BridgeServer
from rigmate.providers.mock_provider import MockAIProvider
from rigmate.providers.antigravity_provider import AntigravityProvider


def parse_args():
    parser = argparse.ArgumentParser(
        prog="python -m rigmate.bridge",
        description="Khởi chạy RigMate Local Bridge Server (kết nối Blender với AI Engine)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host lắng nghe (mặc định: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (mặc định: 8765)")
    parser.add_argument(
        "--provider",
        choices=["mock", "antigravity"],
        default="mock",
        help="AI Provider backend (mặc định: mock)",
    )
    parser.add_argument("--model", default=None, help="Tên model (tùy chọn)")
    return parser.parse_args()


def main():
    # Đảm bảo console UTF-8 trên Windows
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = parse_args()

    server = BridgeServer(host=args.host, port=args.port, save_state=True)

    # Cấu hình provider
    if args.provider == "antigravity":
        model = args.model or "gemini-3.8-flash"
        server.set_provider(AntigravityProvider(model=model))
    else:
        model = args.model or "mock-hunyuan-assistant-v1"
        server.set_provider(MockAIProvider(model=model))

    state_path = server.state_manager.state_file

    print("=" * 65)
    print("  RIGMATE LOCAL BRIDGE SERVER (v0.1.0)")
    print("=" * 65)
    print(f"• Địa chỉ: http://{args.host}:{args.port}")
    print(f"• AI Provider: {server.current_provider.provider_id} ({server.current_provider.model_name})")
    print(f"• Runtime state file: {state_path}")
    print(f"• Auth Token: [Đã lưu tự động vào AppData - Tự động nhận diện bởi Blender Add-on]")
    print(f"• Kiểm tra sức khỏe: http://{args.host}:{args.port}/health")
    print("=" * 65)
    print("Server đang lắng nghe... Bấm Ctrl+C để dừng.")

    try:
        uvicorn.run(server.app, host=args.host, port=args.port, log_level="info")
    finally:
        print("\nĐang dọn dẹp runtime state...")
        server.cleanup_state()
        print("Đã tắt RigMate Bridge an toàn.")


if __name__ == "__main__":
    main()
