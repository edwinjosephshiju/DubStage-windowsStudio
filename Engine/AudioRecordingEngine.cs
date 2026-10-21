using NAudio.Wave;
using DubStage.Models;

namespace DubStage.Engine;

public class AudioLevelEventArgs : EventArgs
{
    public float LeftRmsDb { get; }
    public float RightRmsDb { get; }
    public float PeakDb { get; }

    public AudioLevelEventArgs(float leftRmsDb, float rightRmsDb, float peakDb)
    {
        LeftRmsDb = leftRmsDb;
        RightRmsDb = rightRmsDb;
        PeakDb = peakDb;
    }
}

public class AudioRecordingEngine : IDisposable
{
    private WaveInEvent? _waveIn;
    private WaveFileWriter? _writer;
    private string? _currentFilePath;
    private readonly object _lock = new();
    private bool _isRecording = false;

    public event EventHandler<AudioLevelEventArgs>? LevelReported;
    public bool IsRecording => _isRecording;

    public const int SampleRate = 44100;
    public const int Channels = 2;

    public void StartRecording(string outputWavPath)
    {
        lock (_lock)
        {
            if (_isRecording) StopRecording();

            _currentFilePath = outputWavPath;
            if (File.Exists(outputWavPath)) File.Delete(outputWavPath);

            var dir = Path.GetDirectoryName(outputWavPath);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

            var format = new WaveFormat(SampleRate, 16, Channels);
            _writer = new WaveFileWriter(outputWavPath, format);

            _waveIn = new WaveInEvent
            {
                WaveFormat = format,
                BufferMilliseconds = 25
            };

            _waveIn.DataAvailable += OnDataAvailable;
            _waveIn.RecordingStopped += (s, e) =>
            {
                lock (_lock)
                {
                    _writer?.Flush();
                    _writer?.Dispose();
                    _writer = null;
                }
            };

            _isRecording = true;
            _waveIn.StartRecording();
        }
    }

    public string? StopRecording()
    {
        lock (_lock)
        {
            if (!_isRecording) return _currentFilePath;

            _isRecording = false;
            try
            {
                _waveIn?.StopRecording();
            }
            catch { }

            _waveIn?.Dispose();
            _waveIn = null;

            _writer?.Flush();
            _writer?.Dispose();
            _writer = null;

            return _currentFilePath;
        }
    }

    private void OnDataAvailable(object? sender, WaveInEventArgs e)
    {
        lock (_lock)
        {
            if (!_isRecording || _writer == null) return;
            _writer.Write(e.Buffer, 0, e.BytesRecorded);

            // Compute peak and RMS for stereo levels
            double sumSqL = 0;
            double sumSqR = 0;
            float maxSample = 0f;
            int samplePairs = e.BytesRecorded / 4;

            if (samplePairs > 0)
            {
                for (int i = 0; i < e.BytesRecorded; i += 4)
                {
                    short l = (short)(e.Buffer[i] | (e.Buffer[i + 1] << 8));
                    short r = (short)(e.Buffer[i + 2] | (e.Buffer[i + 3] << 8));

                    float fl = l / 32768f;
                    float fr = r / 32768f;

                    sumSqL += fl * fl;
                    sumSqR += fr * fr;

                    float absMax = Math.Max(Math.Abs(fl), Math.Abs(fr));
                    if (absMax > maxSample) maxSample = absMax;
                }

                float rmsL = (float)Math.Sqrt(sumSqL / samplePairs);
                float rmsR = (float)Math.Sqrt(sumSqR / samplePairs);

                float dbL = rmsL > 1e-4f ? 20f * (float)Math.Log10(rmsL) : -60f;
                float dbR = rmsR > 1e-4f ? 20f * (float)Math.Log10(rmsR) : -60f;
                float peakDb = maxSample > 1e-4f ? 20f * (float)Math.Log10(maxSample) : -60f;

                LevelReported?.Invoke(this, new AudioLevelEventArgs(
                    Math.Clamp(dbL, -60f, 0f),
                    Math.Clamp(dbR, -60f, 0f),
                    Math.Clamp(peakDb, -60f, 0f)
                ));
            }
        }
    }

    public void Dispose()
    {
        StopRecording();
    }
}
