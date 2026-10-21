# 🎙️ DubStage Windows Studio: On-Device Video Dubbing & Demucs v4 Neural Stem Separation DAW

[![Build & Package Windows MSIX](https://github.com/edwinjosephshiju/DubStage-windowsStudio/actions/workflows/build.yml/badge.svg)](https://github.com/edwinjosephshiju/DubStage-windowsStudio/actions/workflows/build.yml)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(x64)-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![UI Framework](https://img.shields.io/badge/UI-PyQt6%20(Qt%206)-41CD52?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Package Format](https://img.shields.io/badge/Package-MSIX%20(Desktop%20Bridge)-00A4EF?logo=microsoft)](https://learn.microsoft.com/en-us/windows/msix/)
[![Neural Engine](https://img.shields.io/badge/Neural%20Engine-Demucs%20v4%20(HTDemucs)-FF6F00?logo=onnx&logoColor=white)](https://huggingface.co/StemSplitio/htdemucs-ft-vocals-onnx)
[![Hardware Acceleration](https://img.shields.io/badge/Acceleration-DirectX%2012%20DirectML%20%2F%20CPU-8B5CF6)](#hardware-acceleration)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## 🌟 Overview

**DubStage Windows Studio** is a unified on-device **Video Dubbing, Neural Stem Separation, and Automated Dialogue Recording (ADR) Digital Audio Workstation (DAW)** engineered specifically for modern Windows 10 & 11 PCs using **PyQt6**.

It brings the complete architectural capabilities of the DubStage Android studio to the desktop, optimized for desktop workflows with full keyboard navigation, high-DPI Per-Monitor V2 scaling, low-latency audio capture, and MSIX packaging for direct Microsoft Store submission.

---

## 🚀 Key Features

* **Demucs v4 Neural Stem Separation**: Meta's state-of-the-art Hybrid Transformer Demucs model running locally via ONNX Runtime with FP16 weights.
* **Phase-Perfect Residual Subtraction**: Subtracts isolated vocals directly from the original PCM to produce pristine, artifact-free instrumental backing with zero digital noise.
* **Acoustic Voice Activity Detection (VAD)**: Adaptive noise-floor profiling, dual-threshold hysteresis, acoustic pitch ($F_0$) autocorrelation, and speaker turn segmentation.
* **Multi-Take ADR Dubbing Booth**: 3-second pre-roll visual countdown, real-time animated VU meter (-60 dB to 0 dB), take auditioning, slip offset alignment, and take gain control.
* **Studio Audition Modes**:
  1. *Full Dub Mix*: Backing + user recorded takes (with original reference vocals filling in for unrecorded dialogue lines).
  2. *Original + Residual*: Reference vocal stem + synchronized instrumental backing.
  3. *Recorded + Residual*: Active recorded actor take + synchronized instrumental backing.
  4. *Solo Original Vocals*: Reference vocal stem only.
  5. *Solo Active Take*: Currently highlighted user take only.
  6. *Backing Only*: Clean instrumental backing without any vocal cues (karaoke).
* **Dual-Waveform Synchronizer**: Interactive canvas showing reference vocal stem against recorded actor take with dialogue cue boundary overlays and scrub playhead.
* **Master MP4 & Subtitle Export**: High-performance multi-track master render muxing video with dubbed audio via bundled FFmpeg, accompanied by frame-accurate `.srt` and `.vtt` subtitle files.
* **Microsoft Store MSIX Packaging**: Packaged into Windows Desktop Bridge `.msix` with complete AppxManifest capabilities (`runFullTrust`, `microphone`, `internetClient`) and all visual asset variants to pass Store review.
* **100% On-Device & Private**: Zero cloud dependencies, zero telemetry, zero data exfiltration.

---

## ⌨️ Desktop Keyboard Shortcuts

DubStage Windows Studio is built for professional desktop DAW workflows with comprehensive keyboard control:

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Space`** | **Toggle Play / Pause** | Play or pause at current playhead position |
| **`R`** | **Record / Stop Take** | Initiate 3s countdown & record take in active cue |
| **`S`** | **Slice Cue at Playhead** | Split active dialogue cue into two sequence-indexed cues |
| **`Left` / `Right`** | **Nudge 1s** | Step playhead backward or forward by 1 second |
| **`Shift+Left` / `Shift+Right`** | **Nudge 5s** | Step playhead backward or forward by 5 seconds |
| **`Up` / `Down`** or **`[` / `]`** | **Navigate Cues** | Select previous or next dialogue cue |
| **`1` – `6`** | **Audition Modes** | Switch between Full Dub Mix, Stems, Solo, and Backing |
| **`Ctrl+O`** | **Import Video** | Open file dialog to ingest video file |
| **`Ctrl+D`** | **Stem Separation** | Run Demucs v4 neural stem separation |
| **`Ctrl+Shift+V`** | **Auto-VAD Detection** | Detect dialogue cues automatically |
| **`Ctrl+E`** | **Export Master MP4** | Render master dubbed video & subtitles |
| **`Ctrl+M`** | **Studio Settings** | Configure model preset, backend, and preferences |
| **`Delete`** | **Delete Active Take** | Remove currently selected actor take |
| **`F11`** | **Toggle Fullscreen** | Borderless fullscreen DAW interface |
| **`F1`** | **Shortcuts Cheatsheet** | Display interactive shortcuts reference modal |
| **`Esc`** | **Cancel / Stop** | Stop playback, cancel recording, or dismiss modal |

---

## 🖥️ Display & Viewport Scaling (High-DPI)

DubStage supports dynamic Windows display scaling (100%, 125%, 150%, 175%, and 200% DPI):
* Embedded `app.manifest` configuring `<dpiAwareness>PerMonitorV2, PerMonitor</dpiAwareness>`.
* Qt High-DPI PassThrough scale factor policy eliminating blurriness on Windows laptops.
* Geometry clamped to the desktop work area to ensure the window never overflows or cuts off buttons on smaller 1080p laptop displays.

---

## 🛠️ GitHub Actions Automated Build & MSIX Packaging

All compiling, PyInstaller standalone bundling, FFmpeg packaging, and Windows SDK MSIX signing run entirely in the cloud via GitHub Actions in [`.github/workflows/build.yml`](.github/workflows/build.yml). **Your local machine remains completely clean of heavy IDEs.**

### Workflow Pipeline Steps:
1. **Runner**: Windows Server (`windows-latest`).
2. **Environment**: Python 3.11 with dependencies cached.
3. **FFmpeg Bundling**: Downloads standalone official Windows binaries (`ffmpeg.exe`, `ffprobe.exe`).
4. **PyInstaller Compilation**: Bundles Python runtime, PyQt6, ONNX Runtime, and FFmpeg into a standalone directory (`dist/DubStage/`).
5. **Layout Structuring**: Prepares `msix_layout/` containing `AppxManifest.xml`, `Assets/`, and application binaries.
6. **Code Signing**: Generates self-signed developer certificate matching `Publisher="CN=DubStageStudioDev"`.
7. **MSIX Packaging**: Uses Windows SDK `makeappx.exe` and `signtool.exe` to package and sign `DubStage_1.0.4.0_x64.msix`.
8. **Artifact Upload**: Publishes `DubStage-Windows-MSIX` containing `.msix`, `Install.ps1`, `DubStageTestCert.cer`, and `SHA256SUMS.txt`.

### Pulling and Testing the MSIX on Local PC:
You can pull the latest workflow artifact directly via GitHub CLI (`gh`):
```powershell
# List latest workflow runs
gh run list --workflow="build.yml" --limit 5

# View run logs if needed
gh run view <run-id> --log-failed

# Download the MSIX artifact package
gh run download -n DubStage-Windows-MSIX -D ./TestArtifact

# Run the automated installer (elevates to install test certificate and MSIX)
cd ./TestArtifact
powershell -ExecutionPolicy Bypass -File .\Install.ps1
```

---

## 🏬 Microsoft Store Submission Guide

To submit DubStage to the Microsoft Partner Center:
1. In `Package.appxmanifest`, update `<Identity>` with your Publisher ID and Package Name from Partner Center:
   ```xml
   <Identity
     Name="YourCompany.DubStage"
     Publisher="CN=YOUR-PUBLISHER-ID-HERE"
     Version="1.0.4.0"
     ProcessorArchitecture="x64" />
   ```
2. Build via the GitHub Actions workflow.
3. Submit the resulting `.msix` package in Partner Center under **Packages**. Microsoft will automatically sign the package with Microsoft's trusted root certificate for global distribution.

---

## 📜 License

Distributed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
