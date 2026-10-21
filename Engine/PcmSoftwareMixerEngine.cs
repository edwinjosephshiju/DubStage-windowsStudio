using NAudio.Wave;
using NAudio.Wave.SampleProviders;
using DubStage.Models;

namespace DubStage.Engine;

public class PcmSoftwareMixerEngine : IDisposable
{
    private WaveOutEvent? _waveOut;
    private MixingSampleProvider? _mixer;
    private System.Threading.Timer? _playheadTimer;
    private long _currentPositionMs = 0;
    private long _totalDurationMs = 0;
    private bool _isPlaying = false;
    private readonly object _lock = new();

    public event Action<long>? PlayheadUpdated;
    public event Action? PlaybackFinished;
    public bool IsPlaying => _isPlaying;

    public const int SampleRate = 44100;
    public const int Channels = 2;

    public void PlayMix(
        string? backingWavPath,
        string? originalVocalsWavPath,
        IReadOnlyList<MixTakeTrack> takes,
        long startPositionMs,
        StudioAuditionMode auditionMode,
        string? activeTakeId,
        float backingGainDb = 0.0f)
    {
        lock (_lock)
        {
            Stop();

            _currentPositionMs = startPositionMs;
            var sampleFormat = WaveFormat.CreateIeeeFloatWaveFormat(SampleRate, Channels);
            _mixer = new MixingSampleProvider(sampleFormat)
            {
                ReadFully = false
            };

            long maxDurationMs = 0;

            // 1. Backing track
            if (auditionMode != StudioAuditionMode.SoloActiveTake &&
                !string.IsNullOrEmpty(backingWavPath) && File.Exists(backingWavPath))
            {
                var backingReader = new AudioFileReader(backingWavPath);
                var backingDuration = (long)backingReader.TotalTime.TotalMilliseconds;
                if (backingDuration > maxDurationMs) maxDurationMs = backingDuration;

                if (startPositionMs < backingDuration)
                {
                    backingReader.CurrentTime = TimeSpan.FromMilliseconds(startPositionMs);
                    backingReader.Volume = (float)Math.Pow(10, backingGainDb / 20.0);
                    _mixer.AddMixerInput(backingReader);
                }
            }

            // 2. Original Vocal track
            if ((auditionMode == StudioAuditionMode.FullDubMix || auditionMode == StudioAuditionMode.OriginalOnly) &&
                !string.IsNullOrEmpty(originalVocalsWavPath) && File.Exists(originalVocalsWavPath))
            {
                var vocalReader = new AudioFileReader(originalVocalsWavPath);
                var vocalDuration = (long)vocalReader.TotalTime.TotalMilliseconds;
                if (vocalDuration > maxDurationMs) maxDurationMs = vocalDuration;

                if (startPositionMs < vocalDuration)
                {
                    vocalReader.CurrentTime = TimeSpan.FromMilliseconds(startPositionMs);
                    // In FullDubMix, if a user take is active, duck or mute original vocals during that take span
                    _mixer.AddMixerInput(vocalReader);
                }
            }

            // 3. User Recorded Takes
            if (auditionMode != StudioAuditionMode.OriginalOnly)
            {
                foreach (var take in takes)
                {
                    if (auditionMode == StudioAuditionMode.SoloActiveTake && take.TakeId != activeTakeId)
                    {
                        continue;
                    }

                    if (!File.Exists(take.AudioFilePath)) continue;

                    long takeAbsoluteStartMs = take.StartMs + take.TimeOffsetMs;
                    long takeAbsoluteEndMs = takeAbsoluteStartMs + take.DurationMs;
                    if (takeAbsoluteEndMs > maxDurationMs) maxDurationMs = takeAbsoluteEndMs;

                    if (startPositionMs < takeAbsoluteEndMs)
                    {
                        var takeReader = new AudioFileReader(take.AudioFilePath);
                        takeReader.Volume = (float)Math.Pow(10, take.GainDb / 20.0);

                        long offsetFromStart = startPositionMs - takeAbsoluteStartMs;
                        if (offsetFromStart > 0)
                        {
                            takeReader.CurrentTime = TimeSpan.FromMilliseconds(offsetFromStart);
                            _mixer.AddMixerInput(takeReader);
                        }
                        else
                        {
                            // Take begins in the future relative to current playhead
                            var delayMs = (int)Math.Abs(offsetFromStart);
                            var delayedProvider = new OffsetSampleProvider(takeReader)
                            {
                                DelayBy = TimeSpan.FromMilliseconds(delayMs)
                            };
                            _mixer.AddMixerInput(delayedProvider);
                        }
                    }
                }
            }

            _totalDurationMs = maxDurationMs;

            _waveOut = new WaveOutEvent
            {
                DesiredLatency = 100
            };
            _waveOut.Init(_mixer);
            _waveOut.PlaybackStopped += OnPlaybackStopped;

            _isPlaying = true;
            _waveOut.Play();

            _playheadTimer = new System.Threading.Timer(OnPlayheadTick, null, 0, 40);
        }
    }

    private void OnPlayheadTick(object? state)
    {
        lock (_lock)
        {
            if (!_isPlaying) return;
            _currentPositionMs += 40;

            if (_totalDurationMs > 0 && _currentPositionMs >= _totalDurationMs)
            {
                Stop();
                PlaybackFinished?.Invoke();
                return;
            }

            PlayheadUpdated?.Invoke(_currentPositionMs);
        }
    }

    private void OnPlaybackStopped(object? sender, StoppedEventArgs e)
    {
        lock (_lock)
        {
            _isPlaying = false;
            _playheadTimer?.Dispose();
            _playheadTimer = null;
        }
        PlaybackFinished?.Invoke();
    }

    public void Stop()
    {
        lock (_lock)
        {
            _isPlaying = false;
            _playheadTimer?.Dispose();
            _playheadTimer = null;

            if (_waveOut != null)
            {
                _waveOut.PlaybackStopped -= OnPlaybackStopped;
                try
                {
                    _waveOut.Stop();
                }
                catch { }
                _waveOut.Dispose();
                _waveOut = null;
            }
            _mixer = null;
        }
    }

    public void Dispose()
    {
        Stop();
    }
}
