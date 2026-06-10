# Sprite Sheet Tool

Sprite Sheet Tool is a Windows-local browser tool for turning AI-generated or rendered green-screen video frames into transparent sprite sheets for Godot 4.x. The MVP combines a FastAPI backend for project storage, frame processing, chroma keying, and export generation with a Vite/React frontend for preview, cleanup, and export controls.

The current tool is local-only. It stores projects under `projects/`, runs backend and frontend servers on the local machine, and does not upload assets or provide packaged desktop installation yet.

## Install Dependencies

Run these commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .\backend[dev]
Set-Location frontend
npm install
Set-Location ..
```

## Run Backend Tests

```powershell
.\.venv\Scripts\pytest backend\tests -v
```

## Run Frontend Tests And Build

```powershell
Set-Location frontend
npm run test
npm run build
Set-Location ..
```

## Start The Tool

The launcher checks dependencies and ports, starts the backend on `127.0.0.1:8765`, starts the frontend on `127.0.0.1:5173`, and opens the browser.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-SpritesheetTool.ps1
```

To run only launcher preflight checks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-SpritesheetTool.ps1 -PreflightOnly
```

When launched normally, keep the launcher PowerShell window open while using the tool. Press Enter in that window to stop both servers.

## Create Desktop Shortcut

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Create-DesktopShortcut.ps1
```

This creates a desktop shortcut named `Spritesheet 工具.lnk` that starts the local launcher for this checkout.

## Expected Export Files

Each project exports into its `exports/` directory. The MVP export contract is:

- `sheet.png`: transparent PNG sprite sheet.
- `frames.json`: Godot 4.x-friendly frame metadata with sheet layout, frame rectangles, source frame numbers, anchors, FPS, and frame count.

The exported PNG is intended for Godot 4.x workflows such as `AnimatedSprite2D`/`SpriteFrames` or `Sprite2D` with `AnimationPlayer`.
