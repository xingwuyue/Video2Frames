# Sprite Sheet Tool MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-local browser tool that converts AI/rendered green-screen videos into Godot 4.x-ready transparent sprite sheets with anchor alignment and manual cleanup.

**Architecture:** Use a local FastAPI backend for file management, FFmpeg-driven frame extraction, OpenCV/Pillow image processing, and export generation. Use a Vite + React + TypeScript frontend for video/project workflow, frame preview, canvas editing, and export controls. Provide PowerShell launch scripts and a Windows shortcut creator so users can start the tool from a desktop icon.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, Pillow, NumPy, OpenCV, imageio-ffmpeg, pytest; Node 22, Vite, React, TypeScript, Vitest, Canvas 2D API; PowerShell for Windows launcher and shortcut.

---

## Scope Check

The approved specification covers backend processing, frontend editing, export metadata, and Windows startup. These are tightly coupled for the first usable vertical slice, so this plan keeps them in one MVP plan. Work is sequenced so each task creates a testable layer and no task depends on unfinished UI polish.

## File Structure

Create this project structure:

```text
D:\工具\spritesheet\
  .gitignore
  README.md
  backend\
    pyproject.toml
    app\
      __init__.py
      main.py
      api\
        __init__.py
        projects.py
        processing.py
        exports.py
      core\
        __init__.py
        paths.py
        models.py
        project_store.py
      services\
        __init__.py
        video_probe.py
        frame_extract.py
        chroma_key.py
        bounds.py
        refine_masks.py
        sheet_export.py
    tests\
      conftest.py
      test_project_store.py
      test_chroma_key.py
      test_bounds.py
      test_refine_masks.py
      test_sheet_export.py
  frontend\
    package.json
    index.html
    tsconfig.json
    vite.config.ts
    src\
      main.tsx
      App.tsx
      api\
        client.ts
        types.ts
      components\
        ProjectPanel.tsx
        FrameTimeline.tsx
        PreviewStage.tsx
        RefineEditor.tsx
        ExportPanel.tsx
      state\
        projectStore.ts
      utils\
        canvasTools.ts
        floodFill.ts
      tests\
        floodFill.test.ts
        canvasTools.test.ts
  scripts\
    Start-SpritesheetTool.ps1
    Create-DesktopShortcut.ps1
  docs\
    superpowers\
      specs\
        2026-06-04-spritesheet-tool-design.md
      plans\
        2026-06-04-spritesheet-tool-mvp.md
```

## Task 1: Repository and Tooling Scaffold

**Files:**
- Create: `D:\工具\spritesheet\.gitignore`
- Create: `D:\工具\spritesheet\README.md`
- Create: `D:\工具\spritesheet\backend\pyproject.toml`
- Create: `D:\工具\spritesheet\frontend\package.json`
- Create: `D:\工具\spritesheet\frontend\tsconfig.json`
- Create: `D:\工具\spritesheet\frontend\vite.config.ts`
- Create: `D:\工具\spritesheet\frontend\index.html`

- [ ] **Step 1: Initialize git**

Run:

```powershell
git init
```

Expected: `Initialized empty Git repository`.

- [ ] **Step 2: Add `.gitignore`**

Write:

```gitignore
.venv/
__pycache__/
.pytest_cache/
node_modules/
dist/
coverage/
.superpowers/
projects/
*.log
```

- [ ] **Step 3: Add backend dependency config**

Write `backend\pyproject.toml`:

```toml
[project]
name = "spritesheet-tool-backend"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.34",
  "pillow>=11.0",
  "numpy>=2.2",
  "opencv-python>=4.10",
  "imageio-ffmpeg>=0.6",
  "pydantic>=2.10"
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "httpx>=0.28"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 4: Add frontend dependency config**

Write `frontend\package.json`:

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^5.0.0",
    "vite": "^7.0.0",
    "typescript": "^5.8.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "vitest": "^3.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0"
  }
}
```

- [ ] **Step 5: Install dependencies**

Run:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .\backend[dev]
Set-Location frontend
npm install
Set-Location ..
```

Expected: pip and npm complete without dependency resolution errors.

- [ ] **Step 6: Commit scaffold**

```powershell
git add .gitignore README.md backend frontend docs
git commit -m "chore: scaffold spritesheet tool"
```

## Task 2: Backend Domain Models and Project Store

**Files:**
- Create: `D:\工具\spritesheet\backend\app\core\models.py`
- Create: `D:\工具\spritesheet\backend\app\core\paths.py`
- Create: `D:\工具\spritesheet\backend\app\core\project_store.py`
- Create: `D:\工具\spritesheet\backend\tests\test_project_store.py`

- [ ] **Step 1: Write project store tests**

Use this test shape:

```python
from app.core.models import ProjectConfig
from app.core.project_store import create_project, load_project, save_project

def test_create_project_writes_project_json(tmp_path):
    project = create_project(tmp_path, "walk")
    assert project.name == "walk"
    assert (tmp_path / "walk" / "project.json").exists()

def test_save_and_load_project_preserves_anchor_and_layout(tmp_path):
    project = create_project(tmp_path, "attack")
    project.anchor.preset = "foot_center"
    project.export.rows = 4
    project.export.columns = 3
    save_project(project)
    loaded = load_project(tmp_path / "attack")
    assert loaded.anchor.preset == "foot_center"
    assert loaded.export.rows == 4
    assert loaded.export.columns == 3
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```powershell
.\.venv\Scripts\pytest backend\tests\test_project_store.py -v
```

Expected: FAIL because `app.core.models` is missing.

- [ ] **Step 3: Implement models**

Define Pydantic models with these fields:

```python
from pathlib import Path
from pydantic import BaseModel, Field

class BackgroundKey(BaseModel):
    mode: str = "green"
    color: tuple[int, int, int] = (0, 255, 0)
    tolerance: int = 45
    edge_feather: int = 1
    spill_suppression: float = 0.25

class AnchorConfig(BaseModel):
    preset: str = "foot_center"
    x: float = 0.5
    y: float = 1.0
    frame_offsets: dict[str, tuple[float, float]] = Field(default_factory=dict)

class ExportConfig(BaseModel):
    cell_width: int = 256
    cell_height: int = 256
    rows: int = 4
    columns: int = 4
    fps: int = 12
    include_frames: bool = True
    include_godot_helper: bool = True

class FrameRecord(BaseModel):
    id: str
    source_frame: int
    raw_path: str
    keyed_path: str | None = None
    enabled: bool = True

class ProjectConfig(BaseModel):
    name: str
    root: Path
    source_video: str | None = None
    source_fps: float | None = None
    source_width: int | None = None
    source_height: int | None = None
    sample_every_n_frames: int = 1
    background: BackgroundKey = Field(default_factory=BackgroundKey)
    anchor: AnchorConfig = Field(default_factory=AnchorConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    frames: list[FrameRecord] = Field(default_factory=list)
```

- [ ] **Step 4: Implement project persistence**

Use `project.json` with `model_dump_json(indent=2)` and create `source`, `frames/raw`, `frames/keyed`, `edits`, `exports` folders when creating a project.

- [ ] **Step 5: Run project store tests**

Run:

```powershell
.\.venv\Scripts\pytest backend\tests\test_project_store.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```powershell
git add backend\app\core backend\tests\test_project_store.py
git commit -m "feat: add project persistence"
```

## Task 3: Chroma Key, Bounds, and Smart Erase Algorithms

**Files:**
- Create: `D:\工具\spritesheet\backend\app\services\chroma_key.py`
- Create: `D:\工具\spritesheet\backend\app\services\bounds.py`
- Create: `D:\工具\spritesheet\backend\app\services\refine_masks.py`
- Create: `D:\工具\spritesheet\backend\tests\test_chroma_key.py`
- Create: `D:\工具\spritesheet\backend\tests\test_bounds.py`
- Create: `D:\工具\spritesheet\backend\tests\test_refine_masks.py`

- [ ] **Step 1: Test chroma key removes green and preserves red**

Create a 4x4 RGB image in memory with green background and a red 2x2 square. Assert green pixels have alpha 0 and red pixels have alpha 255.

- [ ] **Step 2: Test alpha bounds**

Create an RGBA array with nonzero alpha at `x=2..4`, `y=1..3`. Assert bounds returns `{ "x": 2, "y": 1, "w": 3, "h": 3 }`.

- [ ] **Step 3: Test smart erase only removes connected similar pixels**

Create a 5x5 image with two separated green islands and click the left island. Assert only the connected left island becomes alpha 0.

- [ ] **Step 4: Run tests and verify failure**

```powershell
.\.venv\Scripts\pytest backend\tests\test_chroma_key.py backend\tests\test_bounds.py backend\tests\test_refine_masks.py -v
```

Expected: FAIL because services are missing.

- [ ] **Step 5: Implement chroma key**

Implement `apply_chroma_key(image: Image.Image, key_color: tuple[int, int, int], tolerance: int) -> Image.Image` using Euclidean RGB distance. Output RGBA.

- [ ] **Step 6: Implement bounds**

Implement `alpha_bounds(image: Image.Image) -> dict[str, int] | None` using NumPy alpha channel. Return `None` when no visible pixels exist.

- [ ] **Step 7: Implement smart erase**

Implement `connected_color_erase(image, start_x, start_y, tolerance)` using flood fill over 4-neighbors. Match pixels by RGB distance from the clicked pixel and set alpha to 0 only in the connected region.

- [ ] **Step 8: Run algorithm tests**

```powershell
.\.venv\Scripts\pytest backend\tests\test_chroma_key.py backend\tests\test_bounds.py backend\tests\test_refine_masks.py -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```powershell
git add backend\app\services backend\tests
git commit -m "feat: add keying bounds and smart erase"
```

## Task 4: Frame Extraction and Video Probe

**Files:**
- Create: `D:\工具\spritesheet\backend\app\services\video_probe.py`
- Create: `D:\工具\spritesheet\backend\app\services\frame_extract.py`
- Create: `D:\工具\spritesheet\backend\tests\conftest.py`

- [ ] **Step 1: Add a generated test video fixture**

In `conftest.py`, generate a tiny MP4 with 6 frames using OpenCV `VideoWriter`, green background, and a moving red square.

- [ ] **Step 2: Write video probe test**

Assert `probe_video(path)` returns width, height, fps, and frame count.

- [ ] **Step 3: Write extraction test**

Extract every 2 frames from the 6-frame fixture. Assert 3 PNG files are written and source frame numbers are `[0, 2, 4]`.

- [ ] **Step 4: Run tests and verify failure**

```powershell
.\.venv\Scripts\pytest backend\tests -k "video or extract" -v
```

Expected: FAIL because services are missing.

- [ ] **Step 5: Implement probe and extraction**

Use OpenCV for probe and `imageio_ffmpeg.get_ffmpeg_exe()` for frame extraction. Keep function names:

```python
def probe_video(video_path: Path) -> dict[str, float | int]: ...
def extract_frames(video_path: Path, output_dir: Path, every_n: int) -> list[FrameRecord]: ...
```

Extraction command shape:

```python
[
    ffmpeg_exe,
    "-y",
    "-i",
    str(video_path),
    "-vf",
    f"select='not(mod(n\\,{every_n}))'",
    "-vsync",
    "0",
    str(output_dir / "frame_%06d.png"),
]
```

After FFmpeg writes files, create `FrameRecord` entries with `source_frame = output_index * every_n`.

- [ ] **Step 6: Run tests**

```powershell
.\.venv\Scripts\pytest backend\tests -k "video or extract" -v
```

Expected: generated fixture passes probe and extraction tests.

- [ ] **Step 7: Commit**

```powershell
git add backend\app\services\video_probe.py backend\app\services\frame_extract.py backend\tests
git commit -m "feat: add video probing and frame extraction"
```

## Task 5: Sprite Sheet Export and Godot Metadata

**Files:**
- Create: `D:\工具\spritesheet\backend\app\services\sheet_export.py`
- Create: `D:\工具\spritesheet\backend\tests\test_sheet_export.py`

- [ ] **Step 1: Write export test**

Create three 32x32 RGBA frame images, export them into a 2x2 sheet, and assert:

- `sheet.png` size is 64x64.
- fourth cell is transparent.
- `frames.json` has three frame records.
- each frame includes `x`, `y`, `w`, `h`, `anchor`, and `source_frame`.

- [ ] **Step 2: Run and verify failure**

```powershell
.\.venv\Scripts\pytest backend\tests\test_sheet_export.py -v
```

Expected: FAIL because `sheet_export.py` is missing.

- [ ] **Step 3: Implement exporter**

Implement:

```python
def export_sheet(project: ProjectConfig, output_dir: Path) -> dict[str, Path]:
    ...
```

Rules:

- Use enabled frames only.
- Raise `ValueError("Frame count exceeds sheet capacity")` when enabled frames exceed `rows * columns`.
- Paste each RGBA frame into a transparent sheet.
- Write `sheet.png`.
- Write `frames.json` with Godot 4.x-friendly metadata.

- [ ] **Step 4: Run export tests**

```powershell
.\.venv\Scripts\pytest backend\tests\test_sheet_export.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend\app\services\sheet_export.py backend\tests\test_sheet_export.py
git commit -m "feat: export godot spritesheet metadata"
```

## Task 6: Backend HTTP API

**Files:**
- Create: `D:\工具\spritesheet\backend\app\main.py`
- Create: `D:\工具\spritesheet\backend\app\api\projects.py`
- Create: `D:\工具\spritesheet\backend\app\api\processing.py`
- Create: `D:\工具\spritesheet\backend\app\api\exports.py`
- Create: `D:\工具\spritesheet\backend\tests\test_api.py`

- [ ] **Step 1: Write API tests with FastAPI TestClient**

Cover:

- `POST /api/projects` creates a project.
- `GET /api/projects/{name}` returns saved config.
- `POST /api/projects/{name}/process/key` applies chroma key to cached frames.
- `POST /api/projects/{name}/export` writes `sheet.png` and `frames.json`.

- [ ] **Step 2: Run API tests and verify failure**

```powershell
.\.venv\Scripts\pytest backend\tests\test_api.py -v
```

Expected: FAIL because API modules are missing.

- [ ] **Step 3: Implement API routes**

Use `PROJECTS_ROOT = Path("projects")` for MVP storage. Return JSON responses with explicit errors:

```json
{ "error": "Frame count exceeds sheet capacity" }
```

- [ ] **Step 4: Run full backend tests**

```powershell
.\.venv\Scripts\pytest backend\tests -v
```

Expected: all backend tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend\app backend\tests
git commit -m "feat: expose processing api"
```

## Task 7: Frontend Types, API Client, and Shell

**Files:**
- Create: `D:\工具\spritesheet\frontend\src\api\types.ts`
- Create: `D:\工具\spritesheet\frontend\src\api\client.ts`
- Create: `D:\工具\spritesheet\frontend\src\main.tsx`
- Create: `D:\工具\spritesheet\frontend\src\App.tsx`

- [ ] **Step 1: Define shared frontend types**

Create TypeScript interfaces matching backend `ProjectConfig`, `FrameRecord`, `BackgroundKey`, `AnchorConfig`, and `ExportConfig`.

- [ ] **Step 2: Implement API client**

Implement `createProject`, `loadProject`, `processKey`, and `exportProject` functions using `fetch`. Throw `Error(message)` when response contains `{ error }`.

- [ ] **Step 3: Build app shell**

Create a full-screen workbench with:

- left project panel
- center preview/editor area
- bottom frame timeline
- right export/settings panel

Use restrained tool UI, icon buttons from `lucide-react`, and no marketing hero.

- [ ] **Step 4: Run frontend build**

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

Expected: TypeScript and Vite build succeed.

- [ ] **Step 5: Commit**

```powershell
git add frontend\src frontend\index.html frontend\package.json frontend\tsconfig.json frontend\vite.config.ts
git commit -m "feat: add frontend shell"
```

## Task 8: Frontend Timeline, Preview, and Background Check

**Files:**
- Create: `D:\工具\spritesheet\frontend\src\components\ProjectPanel.tsx`
- Create: `D:\工具\spritesheet\frontend\src\components\FrameTimeline.tsx`
- Create: `D:\工具\spritesheet\frontend\src\components\PreviewStage.tsx`

- [ ] **Step 1: Implement project controls**

Add project name input, create/load buttons, sample interval input, and keying controls for background mode, RGB color, and tolerance.

- [ ] **Step 2: Implement frame timeline**

Render frames with source frame numbers, selected state, enabled toggle, and delete/hide action.

- [ ] **Step 3: Implement preview stage backgrounds**

Support checkerboard, white, green, and red-purple preview modes. Ensure preview background never changes exported alpha data.

- [ ] **Step 4: Build**

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add frontend\src\components
git commit -m "feat: add frame preview workflow"
```

## Task 9: Frontend Refine Editor with Zoom, Pan, Brush, and Smart Erase

**Files:**
- Create: `D:\工具\spritesheet\frontend\src\components\RefineEditor.tsx`
- Create: `D:\工具\spritesheet\frontend\src\utils\canvasTools.ts`
- Create: `D:\工具\spritesheet\frontend\src\utils\floodFill.ts`
- Create: `D:\工具\spritesheet\frontend\src\tests\floodFill.test.ts`
- Create: `D:\工具\spritesheet\frontend\src\tests\canvasTools.test.ts`

- [ ] **Step 1: Test flood fill**

Use a small RGBA buffer with two separated same-color islands. Assert the returned mask only includes the island connected to the clicked pixel.

- [ ] **Step 2: Test zoom utility**

Assert `fitToViewport(imageWidth, imageHeight, viewportWidth, viewportHeight)` returns a scale that fits the image and preserves aspect ratio.

- [ ] **Step 3: Run tests and verify failure**

```powershell
Set-Location frontend
npm run test
Set-Location ..
```

Expected: FAIL because utilities are missing.

- [ ] **Step 4: Implement utilities**

Implement:

```ts
export function connectedColorMask(data: Uint8ClampedArray, width: number, height: number, x: number, y: number, tolerance: number): Uint8Array
export function fitToViewport(imageWidth: number, imageHeight: number, viewportWidth: number, viewportHeight: number): number
```

- [ ] **Step 5: Implement editor UI**

Add:

- zoom in/out buttons
- mouse wheel zoom
- pan while holding space or middle mouse
- fit to window
- 100% view
- optional pixel grid above 600% zoom
- normal eraser brush with size and hardness
- smart erase preview with tolerance, apply, cancel, undo
- restore brush mode

- [ ] **Step 6: Run frontend tests and build**

```powershell
Set-Location frontend
npm run test
npm run build
Set-Location ..
```

Expected: tests and build pass.

- [ ] **Step 7: Commit**

```powershell
git add frontend\src\components\RefineEditor.tsx frontend\src\utils frontend\src\tests
git commit -m "feat: add refine editor tools"
```

## Task 10: Export Panel and Godot 4.x Output UX

**Files:**
- Create: `D:\工具\spritesheet\frontend\src\components\ExportPanel.tsx`

- [ ] **Step 1: Implement export controls**

Add inputs for rows, columns, cell width, cell height, FPS, include single frames, and include Godot helper.

- [ ] **Step 2: Add capacity validation**

Before export, calculate `rows * columns`. If enabled frame count is larger, show: `帧数超过当前行列容量，请增加行列或删除帧。`

- [ ] **Step 3: Add export result display**

After export, show paths for `sheet.png`, `frames.json`, and optional frame folder/helper script.

- [ ] **Step 4: Build**

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add frontend\src\components\ExportPanel.tsx
git commit -m "feat: add godot export panel"
```

## Task 11: Windows Launcher and Desktop Shortcut

**Files:**
- Create: `D:\工具\spritesheet\scripts\Start-SpritesheetTool.ps1`
- Create: `D:\工具\spritesheet\scripts\Create-DesktopShortcut.ps1`

- [ ] **Step 1: Write launcher script**

The launcher should:

- start backend with `.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765`
- start frontend dev server with `npm run dev -- --port 5173`
- open `http://localhost:5173`
- keep a PowerShell window open with clear stop instructions

- [ ] **Step 2: Write shortcut creation script**

Use `WScript.Shell` COM object to create `%USERPROFILE%\Desktop\Spritesheet 工具.lnk` pointing to PowerShell with:

```powershell
-ExecutionPolicy Bypass -File "D:\工具\spritesheet\scripts\Start-SpritesheetTool.ps1"
```

- [ ] **Step 3: Run shortcut script**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Create-DesktopShortcut.ps1
```

Expected: desktop shortcut exists.

- [ ] **Step 4: Manual launch check**

Double-click the shortcut. Expected:

- backend starts on port 8765
- frontend starts on port 5173
- browser opens the tool

- [ ] **Step 5: Commit**

```powershell
git add scripts
git commit -m "feat: add windows launcher"
```

## Task 12: End-to-End MVP Verification

**Files:**
- Modify: `D:\工具\spritesheet\README.md`

- [ ] **Step 1: Add README run instructions**

Document:

- install dependencies
- run backend tests
- run frontend tests
- start tool
- create desktop shortcut
- expected export files

- [ ] **Step 2: Run backend tests**

```powershell
.\.venv\Scripts\pytest backend\tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend tests and build**

```powershell
Set-Location frontend
npm run test
npm run build
Set-Location ..
```

Expected: tests and build pass.

- [ ] **Step 4: Run manual export fixture**

Use the generated green-screen fixture video from backend tests or create a small AI/rendered test video. In the UI:

- create project
- import video
- sample every 2 frames
- apply green key
- inspect on red-purple background
- use smart erase preview on a residue area
- export 2x2 sheet

Expected:

- `projects\<project>\exports\sheet.png` exists
- `projects\<project>\exports\frames.json` exists
- transparent background is preserved
- no frame is clipped
- metadata frame count matches enabled frames

- [ ] **Step 5: Commit README and verification notes**

```powershell
git add README.md
git commit -m "docs: add mvp runbook"
```

## Self-Review

Spec coverage:

- Local browser tool: covered by Tasks 7-11.
- FFmpeg/OpenCV backend processing: covered by Tasks 3-6. Task 4 uses FFmpeg for extraction and OpenCV for probe/test fixture support.
- Desktop shortcut: covered by Task 11.
- Green/red-purple/white/custom background strategy: covered by Tasks 3, 8, and 12.
- Every N frames: covered by Task 4.
- 256x256 base canvas with expansion: covered by Task 5 and export validation.
- Max alpha bounds: covered by Task 3.
- Rows/columns export: covered by Tasks 5 and 10.
- Manual eraser, zoom, pan, smart connected-region erase: covered by Task 9.
- Background inspection: covered by Task 8.
- Godot 4.x PNG and JSON export: covered by Tasks 5 and 10.
- Project persistence: covered by Task 2.

Placeholder scan:

- This plan contains no unresolved placeholder markers.
- Each implementation task names concrete files, test commands, and expected verification results.

Type consistency:

- Backend project state uses `ProjectConfig`, `FrameRecord`, `BackgroundKey`, `AnchorConfig`, and `ExportConfig`.
- Frontend shared types mirror those backend model names.
- Export function is consistently named `export_sheet`.
- Smart erase functions use connected-region behavior in both backend and frontend.
