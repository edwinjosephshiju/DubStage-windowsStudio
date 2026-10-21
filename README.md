# DubStage Windows Studio

[![Build & Package Windows MSIX](https://github.com/edwinjosephshiju/DubStage-windowsStudio/actions/workflows/build.yml/badge.svg)](https://github.com/edwinjosephshiju/DubStage-windowsStudio/actions/workflows/build.yml)

**DubStage Windows Studio** is a professional, high-performance desktop application for **AI-powered Video Dubbing, Demucs Neural Stem Separation, and Automated Dialogue Recording (ADR)** built with **WinUI 3** and the **Windows App SDK (.NET 8)**.

Converted and enhanced from the original [DubStage Android Studio](https://github.com/edwinjosephshiju/DubStage-androidStudio) codebase, this Windows edition introduces desktop-grade digital audio workstation (DAW) workflows, low-latency WASAPI audio capture, real-time dual-waveform sync visualizers, comprehensive keyboard shortcuts, and responsive viewport scaling.

---

## 🚀 Key Features

* **WinUI 3 & Windows App SDK (.NET 8):** Native modern Windows user interface adhering to Windows 11 Fluent Design with Mica/Acrylic backdrops and dark studio DAW aesthetics.
* **Demucs v4 Neural Stem Separation:** High-fidelity vocal and instrumental backing separation via ONNX Runtime with residual phase preservation and peak waveform calculation.
* **Acoustic Voice Activity Detection (VAD):** Automatic speech segmentation, energy RMS profiling, pitch autocorrelation, and speaker turn detection.
* **Low-Latency ADR Recording Booth:** Real-time microphone capture at 44.1 kHz 16-bit stereo with live VU meter (RMS & peak levels) and tally lamp visual indicator.
* **Dual-Waveform Sync Visualizer:** Side-by-side comparative waveform rendering (original vocal reference vs active voiceover take) with real-time scrub line and cue markers.
* **Takes Carousel & Micro-Sync Deck:** Fine-tune user takes with per-take gain sliders (-12 dB to +12 dB) and sub-second time-offset nudge sliders (-500 ms to +500 ms) for lip-sync precision.
* **Multi-Track Audition Modes:** Switch between Full Dubbed Mix, Mute Original Vocals (Karaoke Mode), and Solo Active Take.
* **Master MP4 & Subtitle Export:** Export finished dubbed video along with synchronized `.srt` and `.vtt` subtitle files.
* **Microsoft Store Packaging (`.msix`):** Fully compliant `Package.appxmanifest` configured for Microsoft Store submission and side-by-side sideloading.

---

## ⌨️ Desktop Keyboard Shortcuts

Designed for keyboard-driven studio efficiency:

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Space</kbd> | **Play / Pause** | Toggles multi-track studio audio & video playback |
| <kbd>R</kbd> | **Record / Stop Take** | Starts or stops voiceover recording for selected cue |
| <kbd>↑</kbd> | **Previous Dialogue Cue** | Moves selection to the preceding dialogue span |
| <kbd>↓</kbd> | **Next Dialogue Cue** | Advances selection to the next dialogue span |
| <kbd>←</kbd> | **Scrub Backward** | Rewinds playhead by 1 second |
| <kbd>→</kbd> | **Scrub Forward** | Advances playhead by 1 second |
| <kbd>Ctrl</kbd> + <kbd>O</kbd> | **Open Video** | Launches file picker to import MP4, MKV, MOV, or AVI |
| <kbd>Ctrl</kbd> + <kbd>S</kbd> | **Save Project** | Persists project state and script changes to SQLite |
| <kbd>Ctrl</kbd> + <kbd>E</kbd> | **Export Master** | Renders dubbed master MP4 and subtitles |
| <kbd>Ctrl</kbd> + <kbd>M</kbd> | **Mute Vocals Toggle** | Toggles between Full Dub Mix and Karaoke Mode |
| <kbd>Delete</kbd> | **Delete Take** | Removes currently selected voiceover take |
| <kbd>1</kbd> | **DubForge View** | Switches to video monitor, model cards, and dialogue editor |
| <kbd>2</kbd> | **DubStage View** | Switches to recording booth and audition deck |

---

## 🖥️ Display & Viewport Scaling

DubStage is optimized for high-DPI Windows displays:
* **Per-Monitor V2 DPI Awareness:** Automatically scales crystal-clear typography, vector icons, and waveforms from 100% to 250% scaling without blurriness.
* **Adaptive DAW Grid:**
  * **Compact Laptops (1366x768 / 1080p):** Responsive scrolling workbench with stacked monitors.
  * **Widescreen Displays (1440p / 4K / 21:9):** Wide side-by-side split view with expanded waveform timeline and full script prompter.

---

## 🛠️ Automated GitHub Actions CI/CD Pipeline

DubStage compiles and packages `.msix` bundles directly in GitHub Actions using `.github/workflows/build.yml`.

### Testing Workflow Artifacts
To fetch the latest MSIX build artifact without installing local IDE tooling:
```powershell
# Check latest workflow run status
gh run list --workflow="build.yml"

# Inspect failed run logs if needed
gh run view $(gh run list --workflow="build.yml" --status=failure --limit 1 --json databaseId -q ".[0].databaseId") --log-failed

# Download completed MSIX artifact to test locally
gh run download --name DubStage-Windows-MSIX
```

### Sideloading the MSIX
1. Extract the downloaded `DubStage-Windows-MSIX` archive.
2. Double-click `DubStageTestCert.cer` and install to **Local Machine -> Trusted People** (one-time setup for self-signed test builds).
3. Double-click `DubStageStudio_1.0.0.0_x64.msix` to install.

---

## 📦 Project Structure

```
DubStage-windowsStudio/
├── .github/workflows/build.yml    # GitHub Actions CI/CD building Windows MSIX
├── Assets/                        # Windows Store high-DPI logos & splash screen
├── Converters/                    # XAML data-binding converters
├── Data/                          # SQLite database & project repository
├── Engine/                        # Demucs ONNX, VAD, WASAPI Recording, Mixer & Muxer
├── Models/                        # Project, Clip, Take, and Model preset entities
├── Styles/                        # StudioTheme dark DAW palette and styles
├── ViewModels/                    # MainViewModel state machine & RelayCommands
├── Views/
│   ├── Components/                # DualWaveformControl & VuMeterControl
│   ├── DubForgeView.xaml          # Video monitor, Demucs manager & dialogue table
│   └── DubStageView.xaml          # Teleprompter booth, dual waveform & audition deck
├── app.manifest                   # PerMonitorV2 DPI awareness & Windows 10/11 manifest
├── DubStage.csproj                # WinUI 3 .NET 8 MSIX project configuration
├── MainWindow.xaml                # Desktop window shell with keyboard accelerators
└── Package.appxmanifest           # Microsoft Store submission manifest
```

---

## 📜 License

Distributed under the Apache License 2.0.
