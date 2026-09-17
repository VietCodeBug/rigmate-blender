# TÀI LIỆU BÀN GIAO CHO KỸ SƯ TIẾP QUẢN (HANDOFF DOCUMENT)

Tài liệu này được viết độc lập để bất kỳ kỹ sư hoặc AI Agent nào có thể tiếp quản dự án **RigMate** ngay lập tức mà không cần phụ thuộc vào lịch sử chat trước đó.

---

## 1. Thông Tin Workspace & Repository
- **Workspace Path**: `D:\Ark_3\RigMate`
- **Git Remote**: `https://github.com/VietCodeBug/rigmate-blender.git`
- **Nhánh chính**: `main`
- **Giấy phép**: `LICENSE` (GPL-3.0-or-later)

---

## 2. Sơ Đồ Cấu Trúc Module (Module Map)

```text
D:\Ark_3\RigMate\
├── pyproject.toml              # Cấu hình dự án & dependencies (pydantic, mcp, fastapi, uvicorn...)
├── .gitignore                  # Bỏ qua storage, token, cache, build
├── dist/                       # Chứa file ZIP add-on sau khi đóng gói
│   └── rigmate_blender_addon_v0.1.0.zip
├── scripts/
│   ├── run_demo.py             # Demo console tương tác 3 bước không cần Blender
│   └── package_addon.py        # Đóng gói add-on chuẩn cấu trúc kèm automated validation
├── src/
│   └── rigmate/
│       ├── core/               # Phân tích rig, models, quota độc lập hoàn toàn bpy
│       │   ├── models.py       # Pydantic schemas: SceneInfo, MeshInfo, ArmatureInfo, BoneInfo
│       │   ├── analyzer.py     # Chẩn đoán mô hình Hunyuan 3D + Meshy + Godot checks
│       │   └── quota.py        # QuotaSnapshot, TokenUsage, Energy percentage calculation
│       ├── storage/            # Quản lý lưu trữ local an toàn
│       │   ├── paths.py        # %LOCALAPPDATA%/RigMate
│       │   ├── manager.py      # Atomic write, corrupt file backup, UTF-8 Vietnamese
│       │   └── runtime_state.py# bridge_state.json: discovery token an toàn giữa các process
│       ├── providers/          # AI Providers
│       │   ├── base.py         # Abstract interfaces BaseAIProvider, BaseQuotaProvider
│       │   ├── mock_provider.py# MockProvider chuyên sâu cho Hunyuan/Meshy workflow
│       │   └── antigravity_provider.py # Adapter agy/SDK có fallback UNVERIFIED_ENV
│       ├── bridge/             # Localhost Bridge Server (FastAPI)
│       │   ├── __main__.py     # Entrypoint: python -m rigmate.bridge [--host] [--port]
│       │   ├── server.py       # API endpoints: /health, /chat, /cancel, /quota, /quota/manual
│       │   └── session.py      # Quản lý session continuity & task cancellation
│       ├── mcp_server/         # FastMCP Server
│       │   ├── server.py       # Stdio MCP Server expose 4 tools
│       │   └── tools.py        # inspect_scene, inspect_mesh, inspect_armature, diagnose_rig
│       └── blender_addon/      # Blender Add-on UI & Operators
│           ├── __init__.py     # bl_info, register, unregister
│           ├── ui.py           # Panel Sidebar 3D View (N-Panel), Energy bar slider, Chat
│           ├── operators.py    # Gửi chat, hủy chat, phiên mới, chẩn đoán nhanh, nhập quota
│           ├── client.py       # HTTP client bất đồng bộ daemon thread, token discovery
│           └── bpy_inspectors.py # Trích xuất bpy sang core models, context gọn gàng
├── tests/                      # Bộ kiểm thử tự động 27 bài test pytest
└── docs/                       # Toàn bộ tài liệu kỹ thuật, kiến trúc, quyết định, hướng dẫn
```

---

## 3. Các Lệnh Cần Thiết

### A. Thiết lập môi trường
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[bridge,dev]"
```

### B. Chạy kiểm thử tự động
```powershell
python -m pytest tests -v
```

### C. Khởi chạy Bridge Server
```powershell
python -m rigmate.bridge --host 127.0.0.1 --port 8765
```

### D. Đóng gói Add-on ZIP
```powershell
python scripts/package_addon.py
```

### E. Chạy Demo Console độc lập (Không cần Blender)
```powershell
python scripts/run_demo.py
```

---

## 4. Trạng Thái Môi Trường Hiện Tại
- **Blender trên máy này**: Chưa có (REAL BLENDER TEST: NOT PERFORMED).
- **Antigravity CLI trên máy này**: Chưa có lệnh `agy` hoặc package `google.antigravity` (UNVERIFIED_ENV).
- **Tất cả các bài test Python thuần & Mock Bridge**: Đều đã PASS 100% (27/27 tests).

---

## 5. Những Việc Tiếp Theo Khi Về Nhà (Next Steps)
1. Cài đặt file ZIP `dist/rigmate_blender_addon_v0.1.0.zip` vào Blender thật.
2. Bật Bridge `python -m rigmate.bridge`.
3. Kiểm tra handshake tự động token discovery trong tab **RigMate** (Sidebar 3D View).
4. Thực hiện đối soát theo bảng kiểm tra [docs/BLENDER_TESTING_CHECKLIST.md](BLENDER_TESTING_CHECKLIST.md).
