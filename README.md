# Sprite Sheet Tool / 精灵图工具

<p align="center">
  <b>🎬 视频 → 🖼️ 透明精灵图 → 🎮 Godot 4.x</b>
</p>

---

<!-- Language Switcher -->

<details open>
<summary><b>🇨🇳 中文（点击切换语言 / Click to switch language）</b></summary>

## 简介

Sprite Sheet Tool 是一款 Windows 本地浏览器工具，用于将绿幕视频转换为带透明通道的精灵图（Sprite Sheet），专为 **Godot 4.x** 工作流设计。

**核心流程**：导入视频 → 自动抽帧 → 高精度绿幕抠像 → 溢色修复 → 导出精灵图

无需繁琐的项目设置，直接导入视频即可全自动处理。如有极少数未扣干净的细节，可在右侧进行本地精修。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Python + OpenCV |
| 前端 | Vite + React + TypeScript |
| 运行环境 | Windows 本地（127.0.0.1） |

## 快速开始

### 1. 安装依赖

在仓库根目录运行：

```powershell
# 后端依赖（使用 uv）
cd backend
uv sync

# 前端依赖
cd ../frontend
npm install
```

### 2. 启动工具

双击运行根目录下的启动脚本：

```
启动工具.bat
```

或手动分别启动：

```powershell
# 终端 1：启动后端（端口 8765）
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765

# 终端 2：启动前端（端口 5173）
cd frontend
npm run dev
```

启动后浏览器自动打开 `http://localhost:5173`。

### 3. 使用流程

1. 点击 **「导入视频并自动抠图」** 选择绿幕视频
2. 设置 **抽帧间隔**（默认每 3 帧抽 1 帧）
3. 系统自动完成抽帧、绿幕抠像、溢色修复
4. 在右侧精修面板对个别帧进行局部修正（可选）
5. 调整导出参数，点击导出获得 `sheet.png` + `frames.json`

## 导出文件说明

| 文件 | 说明 |
|------|------|
| `sheet.png` | 透明 PNG 精灵图合图 |
| `frames.json` | Godot 4.x 兼容的帧元数据（布局、矩形、锚点、FPS 等）|

导出的 PNG 可直接用于 Godot 4.x 的 `AnimatedSprite2D` / `SpriteFrames` 或 `Sprite2D` + `AnimationPlayer`。

## 运行测试

```powershell
# 后端测试
cd backend
uv run pytest tests -v

# 前端测试
cd frontend
npm run test
```

## 注意事项

- 本工具为**纯本地运行**，不会上传任何文件到网络
- 视频文件临时保存在 `backend/uploads/`，处理结果保存在视频同名的输出目录
- 支持格式：`.mp4`、`.mov`、`.webm`、`.avi`、`.mkv`

</details>

---

<details>
<summary><b>🇺🇸 English (Click to switch language / 点击切换语言)</b></summary>

## Introduction

Sprite Sheet Tool is a Windows-local browser tool for converting green-screen videos into transparent sprite sheets, designed for **Godot 4.x** workflows.

**Core Pipeline**: Import Video → Auto Frame Extraction → High-Precision Chroma Keying → Spill Suppression → Export Sprite Sheet

No complex project setup required — just import a video and the system handles everything automatically. For rare imperfect edges, use the refine panel on the right for local touch-ups.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + Python + OpenCV |
| Frontend | Vite + React + TypeScript |
| Runtime | Windows local (127.0.0.1) |

## Quick Start

### 1. Install Dependencies

Run from the repository root:

```powershell
# Backend dependencies (using uv)
cd backend
uv sync

# Frontend dependencies
cd ../frontend
npm install
```

### 2. Launch the Tool

Double-click the launcher script in the root directory:

```
启动工具.bat
```

Or start backend and frontend manually:

```powershell
# Terminal 1: Start backend (port 8765)
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765

# Terminal 2: Start frontend (port 5173)
cd frontend
npm run dev
```

The browser will automatically open at `http://localhost:5173`.

### 3. Usage Flow

1. Click **「Import Video & Auto Keying」** to select a green-screen video
2. Set the **frame sampling interval** (default: every 3rd frame)
3. The system auto-extracts frames, applies chroma keying, and fixes color spill
4. Use the refine panel on the right for local touch-ups on individual frames (optional)
5. Adjust export settings and click export to get `sheet.png` + `frames.json`

## Export Files

| File | Description |
|------|-------------|
| `sheet.png` | Transparent PNG sprite sheet |
| `frames.json` | Godot 4.x-compatible frame metadata (layout, rectangles, anchors, FPS, etc.) |

The exported PNG is ready for Godot 4.x workflows such as `AnimatedSprite2D` / `SpriteFrames` or `Sprite2D` + `AnimationPlayer`.

## Running Tests

```powershell
# Backend tests
cd backend
uv run pytest tests -v

# Frontend tests
cd frontend
npm run test
```

## Notes

- This tool runs **entirely locally** — no files are uploaded to the internet
- Video files are temporarily stored in `backend/uploads/`, results are saved in an output directory named after the video
- Supported formats: `.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`

</details>
