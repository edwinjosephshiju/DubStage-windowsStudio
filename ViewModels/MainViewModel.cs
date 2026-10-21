using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using DubStage.Data;
using DubStage.Engine;
using DubStage.Models;

namespace DubStage.ViewModels;

public class MainViewModel : INotifyPropertyChanged
{
    private readonly ProjectRepository _repository;
    private readonly ModelManager _modelManager;
    private readonly AudioExtractionEngine _extractionEngine;
    private readonly DemucsOnnxSeparationEngine _separationEngine;
    private readonly VadEngine _vadEngine;
    private readonly AudioRecordingEngine _recordingEngine;
    private readonly PcmSoftwareMixerEngine _mixerEngine;
    private readonly Mp4ExportMuxer _muxer;

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        OnPropertyChanged(name);
        return true;
    }

    public MainViewModel()
    {
        _repository = new ProjectRepository();
        _modelManager = new ModelManager(_repository);
        _extractionEngine = new AudioExtractionEngine();
        _separationEngine = new DemucsOnnxSeparationEngine();
        _vadEngine = new VadEngine();
        _recordingEngine = new AudioRecordingEngine();
        _mixerEngine = new PcmSoftwareMixerEngine();
        _muxer = new Mp4ExportMuxer();

        _selectedModelPreset = DemucsModelPreset.VocalsSpecialist;
        _modelStatus = _modelManager.CheckModelStatus(_selectedModelPreset);
        _modelManager.StatusChanged += status =>
        {
            if (status is ModelStatus.Ready r && r.Preset.Id == _selectedModelPreset.Id)
            {
                ModelStatus = r;
            }
            else if (status is ModelStatus.Downloading d && d.Preset.Id == _selectedModelPreset.Id)
            {
                ModelStatus = d;
            }
            else if (status is ModelStatus.Error err && err.Preset.Id == _selectedModelPreset.Id)
            {
                ModelStatus = err;
            }
        };

        _recordingEngine.LevelReported += (s, e) =>
        {
            VuMeterLeftDb = e.LeftRmsDb;
            VuMeterRightDb = e.RightRmsDb;
            VuMeterPeakDb = e.PeakDb;
        };

        _mixerEngine.PlayheadUpdated += ms =>
        {
            PlayheadMs = ms;
        };

        _mixerEngine.PlaybackFinished += () =>
        {
            IsPlaying = false;
        };

        // Commands
        TogglePlayPauseCommand = new RelayCommand(TogglePlayPause);
        ToggleRecordCommand = new RelayCommand(ToggleRecord);
        NextClipCommand = new RelayCommand(SelectNextClip);
        PreviousClipCommand = new RelayCommand(SelectPreviousClip);
        ScrubForwardCommand = new RelayCommand(() => SeekBy(1000));
        ScrubBackwardCommand = new RelayCommand(() => SeekBy(-1000));
        SaveProjectCommand = new RelayCommand(async () => await SaveCurrentProjectAsync());
        ToggleMuteOriginalCommand = new RelayCommand(ToggleMuteOriginalVocals);
        SwitchTabCommand = new RelayCommand<string>(tab =>
        {
            if (int.TryParse(tab, out int idx)) SelectedTabIndex = idx;
        });
        DeleteActiveTakeCommand = new RelayCommand(async () => await DeleteActiveTakeAsync());
    }

    public async Task InitializeAsync()
    {
        await _repository.InitializeAsync();
        var projects = await _repository.GetAllProjectsAsync();
        if (projects.Count > 0)
        {
            await LoadProjectAsync(projects[0]);
        }
    }

    #region Observable State Properties

    private ProjectEntity? _activeProject;
    public ProjectEntity? ActiveProject
    {
        get => _activeProject;
        set
        {
            if (SetProperty(ref _activeProject, value))
            {
                OnPropertyChanged(nameof(HasProject));
                OnPropertyChanged(nameof(ProjectTitle));
            }
        }
    }

    public bool HasProject => _activeProject != null;
    public string ProjectTitle => _activeProject?.Title ?? "No Project Open";
    public double VideoDurationMsDouble => _activeProject?.VideoDurationMsDouble ?? 1000.0;
    public long ProjectDurationMs => _activeProject?.VideoDurationMs ?? 1000L;

    public ObservableCollection<ClipEntity> Clips { get; } = new();

    private ClipEntity? _activeClip;
    public ClipEntity? ActiveClip
    {
        get => _activeClip;
        set
        {
            if (SetProperty(ref _activeClip, value))
            {
                OnPropertyChanged(nameof(ActiveClipIndexText));
                OnPropertyChanged(nameof(ActiveClipSpeakerText));
                OnPropertyChanged(nameof(ActiveClipDurationMs));
                OnPropertyChanged(nameof(ActiveClipScriptText));
                _ = LoadTakesForClipAsync(value);
            }
        }
    }

    public string ActiveClipIndexText => _activeClip != null ? _activeClip.ClipIndex.ToString() : "-";
    public string ActiveClipSpeakerText => _activeClip?.SpeakerName ?? "No Speaker";
    public long ActiveClipDurationMs => _activeClip?.DurationMs ?? 0L;
    public string ActiveClipScriptText => _activeClip?.ScriptText ?? "No clip selected. Select a cue or detect dialogue in DubForge.";

    public ObservableCollection<TakeEntity> Takes { get; } = new();

    private TakeEntity? _activeTake;
    public TakeEntity? ActiveTake
    {
        get => _activeTake;
        set
        {
            if (SetProperty(ref _activeTake, value))
            {
                if (_activeClip != null && value != null)
                {
                    _activeClip.ActiveTakeId = value.Id;
                    _ = _repository.UpdateClipAsync(_activeClip);
                }
                UpdateTakePeaks(value);
                OnPropertyChanged(nameof(ActiveTakeGainDbDouble));
                OnPropertyChanged(nameof(ActiveTakeGainDbText));
                OnPropertyChanged(nameof(ActiveTakeTimeOffsetMsDouble));
                OnPropertyChanged(nameof(ActiveTakeTimeOffsetMsText));
                OnPropertyChanged(nameof(HasActiveTake));
            }
        }
    }

    public bool HasActiveTake => _activeTake != null;

    public double ActiveTakeGainDbDouble
    {
        get => _activeTake?.GainDbDouble ?? 0.0;
        set
        {
            if (_activeTake != null)
            {
                _activeTake.GainDbDouble = value;
                OnPropertyChanged(nameof(ActiveTakeGainDbDouble));
                OnPropertyChanged(nameof(ActiveTakeGainDbText));
                _ = _repository.UpdateTakeAsync(_activeTake);
            }
        }
    }

    public string ActiveTakeGainDbText => _activeTake != null ? $"{_activeTake.GainDb:F1} dB" : "0.0 dB";

    public double ActiveTakeTimeOffsetMsDouble
    {
        get => _activeTake?.TimeOffsetMsDouble ?? 0.0;
        set
        {
            if (_activeTake != null)
            {
                _activeTake.TimeOffsetMsDouble = value;
                OnPropertyChanged(nameof(ActiveTakeTimeOffsetMsDouble));
                OnPropertyChanged(nameof(ActiveTakeTimeOffsetMsText));
                _ = _repository.UpdateTakeAsync(_activeTake);
            }
        }
    }

    public string ActiveTakeTimeOffsetMsText => _activeTake != null ? $"{_activeTake.TimeOffsetMs} ms" : "0 ms";

    private void UpdateTakePeaks(TakeEntity? take)
    {
        if (take != null && !string.IsNullOrEmpty(take.AudioFilePath) && File.Exists(take.AudioFilePath))
        {
            try
            {
                using var reader = new NAudio.Wave.AudioFileReader(take.AudioFilePath);
                var samples = new List<float>();
                var buf = new float[2048];
                int read;
                while ((read = reader.Read(buf, 0, buf.Length)) > 0)
                {
                    for (int i = 0; i < read; i++) samples.Add(buf[i]);
                }
                var left = samples.Where((x, idx) => idx % 2 == 0).ToArray();
                var right = samples.Where((x, idx) => idx % 2 != 0).ToArray();
                ActiveTakePeaks = DemucsOnnxSeparationEngine.ComputePeaks(left, right, 400);
            }
            catch
            {
                ActiveTakePeaks = Array.Empty<float>();
            }
        }
        else
        {
            ActiveTakePeaks = Array.Empty<float>();
        }
    }

    private int _selectedTabIndex = 0;
    public int SelectedTabIndex
    {
        get => _selectedTabIndex;
        set => SetProperty(ref _selectedTabIndex, value);
    }

    private long _playheadMs = 0;
    public long PlayheadMs
    {
        get => _playheadMs;
        set
        {
            if (SetProperty(ref _playheadMs, value))
            {
                OnPropertyChanged(nameof(TimecodeDisplay));
                OnPropertyChanged(nameof(PlayheadMsDouble));
            }
        }
    }

    public double PlayheadMsDouble
    {
        get => _playheadMs;
        set => PlayheadMs = (long)value;
    }

    public string TimecodeDisplay
    {
        get
        {
            var ts = TimeSpan.FromMilliseconds(_playheadMs);
            return $"{ts.Hours:D2}:{ts.Minutes:D2}:{ts.Seconds:D2}.{ts.Milliseconds:D3}";
        }
    }

    private bool _isPlaying = false;
    public bool IsPlaying
    {
        get => _isPlaying;
        set => SetProperty(ref _isPlaying, value);
    }

    private bool _isRecording = false;
    public bool IsRecording
    {
        get => _isRecording;
        set => SetProperty(ref _isRecording, value);
    }

    private bool _isExtracting = false;
    public bool IsExtracting
    {
        get => _isExtracting;
        set => SetProperty(ref _isExtracting, value);
    }

    private bool _isSeparating = false;
    public bool IsSeparating
    {
        get => _isSeparating;
        set => SetProperty(ref _isSeparating, value);
    }

    private bool _isExporting = false;
    public bool IsExporting
    {
        get => _isExporting;
        set => SetProperty(ref _isExporting, value);
    }

    private SeparationProgress? _sepProgress;
    public SeparationProgress? SeparationProgress
    {
        get => _sepProgress;
        set => SetProperty(ref _sepProgress, value);
    }

    private ExportProgress? _expProgress;
    public ExportProgress? ExportProgress
    {
        get => _expProgress;
        set => SetProperty(ref _expProgress, value);
    }

    private DemucsModelPreset _selectedModelPreset;
    public DemucsModelPreset SelectedModelPreset
    {
        get => _selectedModelPreset;
        set
        {
            if (SetProperty(ref _selectedModelPreset, value))
            {
                ModelStatus = _modelManager.CheckModelStatus(value);
            }
        }
    }

    private ModelStatus _modelStatus;
    public ModelStatus ModelStatus
    {
        get => _modelStatus;
        set => SetProperty(ref _modelStatus, value);
    }

    private StudioAuditionMode _auditionMode = StudioAuditionMode.FullDubMix;
    public StudioAuditionMode AuditionMode
    {
        get => _auditionMode;
        set => SetProperty(ref _auditionMode, value);
    }

    private float _vuMeterLeftDb = -60f;
    public float VuMeterLeftDb
    {
        get => _vuMeterLeftDb;
        set => SetProperty(ref _vuMeterLeftDb, value);
    }

    private float _vuMeterRightDb = -60f;
    public float VuMeterRightDb
    {
        get => _vuMeterRightDb;
        set => SetProperty(ref _vuMeterRightDb, value);
    }

    private float _vuMeterPeakDb = -60f;
    public float VuMeterPeakDb
    {
        get => _vuMeterPeakDb;
        set => SetProperty(ref _vuMeterPeakDb, value);
    }

    private float _backingGainDb = 0.0f;
    public float BackingGainDb
    {
        get => _backingGainDb;
        set => SetProperty(ref _backingGainDb, value);
    }

    private float _vadSensitivity = 0.60f;
    public float VadSensitivity
    {
        get => _vadSensitivity;
        set
        {
            if (SetProperty(ref _vadSensitivity, value))
            {
                OnPropertyChanged(nameof(VadSensitivityDouble));
            }
        }
    }

    public double VadSensitivityDouble
    {
        get => _vadSensitivity;
        set => VadSensitivity = (float)value;
    }

    private float[] _vocalPeaks = Array.Empty<float>();
    public float[] VocalPeaks
    {
        get => _vocalPeaks;
        set => SetProperty(ref _vocalPeaks, value);
    }

    private float[] _backingPeaks = Array.Empty<float>();
    public float[] BackingPeaks
    {
        get => _backingPeaks;
        set => SetProperty(ref _backingPeaks, value);
    }

    private float[] _activeTakePeaks = Array.Empty<float>();
    public float[] ActiveTakePeaks
    {
        get => _activeTakePeaks;
        set => SetProperty(ref _activeTakePeaks, value);
    }

    private string _statusMessage = "Ready";
    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    private string? _errorMessage;
    public string? ErrorMessage
    {
        get => _errorMessage;
        set => SetProperty(ref _errorMessage, value);
    }

    #endregion

    #region Commands

    public RelayCommand TogglePlayPauseCommand { get; }
    public RelayCommand ToggleRecordCommand { get; }
    public RelayCommand NextClipCommand { get; }
    public RelayCommand PreviousClipCommand { get; }
    public RelayCommand ScrubForwardCommand { get; }
    public RelayCommand ScrubBackwardCommand { get; }
    public RelayCommand SaveProjectCommand { get; }
    public RelayCommand ToggleMuteOriginalCommand { get; }
    public RelayCommand<string> SwitchTabCommand { get; }
    public RelayCommand DeleteActiveTakeCommand { get; }

    #endregion

    #region Transport & Workflow Methods

    public void TogglePlayPause()
    {
        if (IsPlaying)
        {
            _mixerEngine.Stop();
            IsPlaying = false;
        }
        else
        {
            if (_activeProject == null) return;

            var mixTracks = new List<MixTakeTrack>();
            foreach (var clip in Clips)
            {
                if (clip.IsMuted) continue;
                if (!string.IsNullOrEmpty(clip.ActiveTakeId))
                {
                    // Find matching take
                    var take = Takes.FirstOrDefault(t => t.Id == clip.ActiveTakeId);
                    if (take != null)
                    {
                        mixTracks.Add(new MixTakeTrack
                        {
                            TakeId = take.Id,
                            AudioFilePath = take.AudioFilePath,
                            StartMs = clip.StartMs,
                            DurationMs = take.DurationMs,
                            GainDb = take.GainDb,
                            TimeOffsetMs = take.TimeOffsetMs
                        });
                    }
                }
            }

            _mixerEngine.PlayMix(
                backingWavPath: _activeProject.BackingWavPath,
                originalVocalsWavPath: _activeProject.VocalsWavPath ?? _activeProject.OriginalWavPath,
                takes: mixTracks,
                startPositionMs: _playheadMs,
                auditionMode: _auditionMode,
                activeTakeId: _activeTake?.Id,
                backingGainDb: _backingGainDb
            );

            IsPlaying = true;
        }
    }

    public void ToggleRecord()
    {
        if (IsRecording)
        {
            // Stop recording
            var recordedFile = _recordingEngine.StopRecording();
            IsRecording = false;

            if (_activeClip != null && !string.IsNullOrEmpty(recordedFile) && File.Exists(recordedFile))
            {
                var fi = new FileInfo(recordedFile);
                var takeNumber = Takes.Count + 1;
                var durationMs = Math.Max(500, _activeClip.DurationMs);

                var newTake = new TakeEntity
                {
                    Id = Guid.NewGuid().ToString(),
                    ClipId = _activeClip.Id,
                    TakeNumber = takeNumber,
                    AudioFilePath = recordedFile,
                    DurationMs = durationMs,
                    GainDb = 0.0f,
                    TimeOffsetMs = 0L,
                    NoiseGateThresholdDb = -60f
                };

                _ = Task.Run(async () =>
                {
                    await _repository.SaveTakeAsync(newTake);
                    App.DispatcherQueue.TryEnqueue(() =>
                    {
                        Takes.Add(newTake);
                        ActiveTake = newTake;
                        StatusMessage = $"Saved Take {takeNumber} for Clip {_activeClip.ClipIndex}";
                    });
                });
            }
        }
        else
        {
            // Start recording
            if (_activeProject == null || _activeClip == null)
            {
                StatusMessage = "Please select a clip to record a vocal take.";
                return;
            }

            var takesDir = _repository.GetTakesDirectory(_activeProject.Id);
            var takeNum = Takes.Count + 1;
            var takePath = Path.Combine(takesDir, $"take_clip{_activeClip.ClipIndex}_{takeNum}_{DateTimeOffset.UtcNow.ToUnixTimeSeconds()}.wav");

            // Cue playhead to clip start
            PlayheadMs = _activeClip.StartMs;
            _recordingEngine.StartRecording(takePath);
            IsRecording = true;
            StatusMessage = $"Recording Take {takeNum} for Clip {_activeClip.ClipIndex}...";
        }
    }

    public void SeekTo(long positionMs)
    {
        PlayheadMs = Math.Max(0, positionMs);
        if (IsPlaying)
        {
            TogglePlayPause();
            TogglePlayPause();
        }
    }

    public void SeekBy(long deltaMs)
    {
        SeekTo(PlayheadMs + deltaMs);
    }

    public void SelectNextClip()
    {
        if (Clips.Count == 0) return;
        int currentIdx = _activeClip != null ? Clips.IndexOf(_activeClip) : -1;
        int nextIdx = Math.Min(currentIdx + 1, Clips.Count - 1);
        ActiveClip = Clips[nextIdx];
        SeekTo(ActiveClip.StartMs);
    }

    public void SelectPreviousClip()
    {
        if (Clips.Count == 0) return;
        int currentIdx = _activeClip != null ? Clips.IndexOf(_activeClip) : 0;
        int prevIdx = Math.Max(currentIdx - 1, 0);
        ActiveClip = Clips[prevIdx];
        SeekTo(ActiveClip.StartMs);
    }

    public void ToggleMuteOriginalVocals()
    {
        AuditionMode = AuditionMode == StudioAuditionMode.MuteOriginalVocals
            ? StudioAuditionMode.FullDubMix
            : StudioAuditionMode.MuteOriginalVocals;

        StatusMessage = AuditionMode == StudioAuditionMode.MuteOriginalVocals
            ? "Original Vocals Muted (Karaoke Dub Mode)"
            : "Full Dubbed Mix (Original Vocals Enabled)";

        if (IsPlaying)
        {
            TogglePlayPause();
            TogglePlayPause();
        }
    }

    public async Task DeleteActiveTakeAsync()
    {
        if (_activeTake == null || _activeClip == null) return;
        var takeToDelete = _activeTake;

        await _repository.DeleteTakeAsync(takeToDelete.Id);
        Takes.Remove(takeToDelete);
        if (File.Exists(takeToDelete.AudioFilePath))
        {
            try { File.Delete(takeToDelete.AudioFilePath); } catch { }
        }

        ActiveTake = Takes.LastOrDefault();
        StatusMessage = "Take deleted.";
    }

    #endregion

    #region AI & Pipeline Workflows

    public async Task CreateNewProjectFromVideoAsync(string videoPath)
    {
        if (!File.Exists(videoPath)) return;

        var projId = Guid.NewGuid().ToString();
        var projDir = _repository.GetProjectDirectory(projId);
        var projTitle = Path.GetFileNameWithoutExtension(videoPath);

        var project = new ProjectEntity
        {
            Id = projId,
            Title = projTitle,
            VideoPath = videoPath,
            Status = ProjectEntity.StatusCreated
        };

        await _repository.SaveProjectAsync(project);
        await LoadProjectAsync(project);

        // Auto extract audio
        await ExtractAudioAsync();
    }

    public async Task LoadProjectAsync(ProjectEntity project)
    {
        ActiveProject = project;
        Clips.Clear();
        Takes.Clear();

        var loadedClips = await _repository.GetClipsForProjectAsync(project.Id);
        foreach (var c in loadedClips) Clips.Add(c);
        ActiveClip = Clips.FirstOrDefault();

        StatusMessage = $"Project loaded: {project.Title}";
    }

    public async Task SaveCurrentProjectAsync()
    {
        if (_activeProject == null) return;
        await _repository.SaveProjectAsync(_activeProject);
        await _repository.ReplaceClipsForProjectAsync(_activeProject.Id, Clips);
        StatusMessage = "Project saved.";
    }

    public async Task LoadTakesForClipAsync(ClipEntity? clip)
    {
        Takes.Clear();
        if (clip == null) return;

        var loaded = await _repository.GetTakesForClipAsync(clip.Id);
        foreach (var t in loaded) Takes.Add(t);

        ActiveTake = Takes.FirstOrDefault(t => t.Id == clip.ActiveTakeId) ?? Takes.LastOrDefault();
    }

    public async Task ExtractAudioAsync()
    {
        if (_activeProject == null || string.IsNullOrEmpty(_activeProject.VideoPath)) return;

        try
        {
            IsExtracting = true;
            StatusMessage = "Extracting audio from video stream (44.1kHz stereo)...";

            var projDir = _repository.GetProjectDirectory(_activeProject.Id);
            var outWav = Path.Combine(projDir, "original.wav");

            var progress = new Progress<int>(pct =>
            {
                StatusMessage = $"Extracting audio: {pct}%";
            });

            await _extractionEngine.ExtractAudioToWavAsync(_activeProject.VideoPath, outWav, progress);

            _activeProject.OriginalWavPath = outWav;
            _activeProject.Status = ProjectEntity.StatusAudioExtracted;
            await _repository.SaveProjectAsync(_activeProject);

            StatusMessage = "Audio extraction complete. Ready for Stem Separation.";
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Audio extraction failed: {ex.Message}";
        }
        finally
        {
            IsExtracting = false;
        }
    }

    public async Task SeparateStemsAsync()
    {
        if (_activeProject == null || string.IsNullOrEmpty(_activeProject.OriginalWavPath))
        {
            StatusMessage = "Please extract audio from video first.";
            return;
        }

        var status = _modelManager.CheckModelStatus(_selectedModelPreset);
        if (status is not ModelStatus.Ready readyModel)
        {
            StatusMessage = "Model not ready. Please download or sideload HT-Demucs model weights first.";
            return;
        }

        try
        {
            IsSeparating = true;
            StatusMessage = "Starting Demucs Neural Stem Separation...";

            var projDir = _repository.GetProjectDirectory(_activeProject.Id);
            var vocalsWav = Path.Combine(projDir, "vocals.wav");
            var backingWav = Path.Combine(projDir, "backing.wav");

            var progress = new Progress<SeparationProgress>(p =>
            {
                SeparationProgress = p;
                StatusMessage = $"{p.Stage} ({p.Percent}%)";
            });

            var result = await _separationEngine.SeparateAsync(
                _activeProject.OriginalWavPath,
                readyModel.ModelPath,
                vocalsWav,
                backingWav,
                progress
            );

            _activeProject.VocalsWavPath = result.VocalsWavPath;
            _activeProject.BackingWavPath = result.BackingWavPath;
            _activeProject.VideoDurationMs = result.DurationMs;
            _activeProject.Status = ProjectEntity.StatusSeparated;
            await _repository.SaveProjectAsync(_activeProject);

            VocalPeaks = result.VocalPeaks;
            BackingPeaks = result.BackingPeaks;

            StatusMessage = "Separation complete! Stems ready. Detecting dialogue...";
            await DetectDialogueClipsAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Stem separation failed: {ex.Message}";
        }
        finally
        {
            IsSeparating = false;
            SeparationProgress = null;
        }
    }

    public async Task DetectDialogueClipsAsync()
    {
        if (_activeProject == null || string.IsNullOrEmpty(_activeProject.VocalsWavPath))
        {
            StatusMessage = "Vocal stem not found. Run separation first.";
            return;
        }

        try
        {
            StatusMessage = "Running acoustic VAD & turn detection...";
            var detected = await _vadEngine.DetectDialogueClipsAsync(
                _activeProject.Id,
                _activeProject.VocalsWavPath,
                _vadSensitivity
            );

            Clips.Clear();
            foreach (var c in detected) Clips.Add(c);
            await _repository.ReplaceClipsForProjectAsync(_activeProject.Id, Clips);

            ActiveClip = Clips.FirstOrDefault();
            StatusMessage = $"VAD complete: Detected {Clips.Count} dialogue clips.";
        }
        catch (Exception ex)
        {
            ErrorMessage = $"VAD failed: {ex.Message}";
        }
    }

    public async Task ExportMasterAsync()
    {
        if (_activeProject == null) return;

        try
        {
            IsExporting = true;
            StatusMessage = "Rendering Dubbed Master MP4 & Subtitles...";

            var exportsDir = _repository.GetExportsDirectory(_activeProject.Id);
            var cleanTitle = string.Join("_", _activeProject.Title.Split(Path.GetInvalidFileNameChars()));
            var masterWav = Path.Combine(exportsDir, $"DubStage_{cleanTitle}_master.wav");
            var outSrt = Path.Combine(exportsDir, $"DubStage_{cleanTitle}.srt");
            var outVtt = Path.Combine(exportsDir, $"DubStage_{cleanTitle}.vtt");

            var mixTracks = new List<MixTakeTrack>();
            foreach (var clip in Clips)
            {
                if (clip.IsMuted) continue;
                if (!string.IsNullOrEmpty(clip.ActiveTakeId))
                {
                    var take = await _repository.GetTakesForClipAsync(clip.Id);
                    var active = take.FirstOrDefault(t => t.Id == clip.ActiveTakeId);
                    if (active != null)
                    {
                        mixTracks.Add(new MixTakeTrack
                        {
                            TakeId = active.Id,
                            AudioFilePath = active.AudioFilePath,
                            StartMs = clip.StartMs,
                            DurationMs = active.DurationMs,
                            GainDb = active.GainDb,
                            TimeOffsetMs = active.TimeOffsetMs
                        });
                    }
                }
            }

            var progress = new Progress<ExportProgress>(p =>
            {
                ExportProgress = p;
                StatusMessage = $"{p.Stage} ({p.Percent}%)";
            });

            await _muxer.ExportMasterAudioWavAsync(
                _activeProject.BackingWavPath,
                _activeProject.VocalsWavPath,
                mixTracks,
                _activeProject.VideoDurationMs,
                masterWav,
                progress
            );

            await _muxer.ExportSrtSubtitlesAsync(Clips.ToList(), outSrt);
            await _muxer.ExportVttSubtitlesAsync(Clips.ToList(), outVtt);

            StatusMessage = $"Master exported successfully to {exportsDir}";
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Export failed: {ex.Message}";
        }
        finally
        {
            IsExporting = false;
            ExportProgress = null;
        }
    }

    public async Task DownloadModelAsync()
    {
        await _modelManager.DownloadModelAsync(_selectedModelPreset);
    }

    public async Task SideloadModelAsync(string path)
    {
        await _modelManager.SideloadModelAsync(_selectedModelPreset, path);
    }

    #endregion
}
