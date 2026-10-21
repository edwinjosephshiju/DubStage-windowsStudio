using System.Text;
using NAudio.Wave;
using NAudio.Wave.SampleProviders;
using DubStage.Models;

namespace DubStage.Engine;

public class Mp4ExportMuxer
{
    public const int SampleRate = 44100;
    public const int Channels = 2;

    public async Task<string> ExportMasterAudioWavAsync(
        string? backingWavPath,
        string? originalVocalsWavPath,
        IReadOnlyList<MixTakeTrack> takes,
        long totalDurationMs,
        string outputWavPath,
        IProgress<ExportProgress>? progress = null,
        CancellationToken ct = default)
    {
        return await Task.Run(() =>
        {
            if (File.Exists(outputWavPath)) File.Delete(outputWavPath);

            var sampleFormat = WaveFormat.CreateIeeeFloatWaveFormat(SampleRate, Channels);
            var mixer = new MixingSampleProvider(sampleFormat)
            {
                ReadFully = true
            };

            // 1. Backing track
            if (!string.IsNullOrEmpty(backingWavPath) && File.Exists(backingWavPath))
            {
                var backingReader = new AudioFileReader(backingWavPath);
                mixer.AddMixerInput(backingReader);
            }

            // 2. Original Vocal track for dialogue spans without active user takes
            if (!string.IsNullOrEmpty(originalVocalsWavPath) && File.Exists(originalVocalsWavPath))
            {
                var vocalReader = new AudioFileReader(originalVocalsWavPath);
                mixer.AddMixerInput(vocalReader);
            }

            // 3. User Recorded Takes
            foreach (var take in takes)
            {
                if (!File.Exists(take.AudioFilePath)) continue;
                var takeReader = new AudioFileReader(take.AudioFilePath);
                takeReader.Volume = (float)Math.Pow(10, take.GainDb / 20.0);

                long startMs = Math.Max(0, take.StartMs + take.TimeOffsetMs);
                var delayed = new OffsetSampleProvider(takeReader)
                {
                    DelayBy = TimeSpan.FromMilliseconds(startMs)
                };
                mixer.AddMixerInput(delayed);
            }

            // Render mixed audio to 16-bit PCM WAV
            var targetFormat = new WaveFormat(SampleRate, 16, Channels);
            using var writer = new WaveFileWriter(outputWavPath, targetFormat);

            long totalSamples = (totalDurationMs * SampleRate * Channels) / 1000;
            if (totalSamples <= 0) totalSamples = SampleRate * Channels * 60; // Default 1 min if unspecified

            var floatBuffer = new float[8192];
            var byteBuffer = new byte[8192 * 2];
            long samplesWritten = 0;

            while (samplesWritten < totalSamples)
            {
                ct.ThrowIfCancellationRequested();

                int toRead = (int)Math.Min(floatBuffer.Length, totalSamples - samplesWritten);
                int samplesRead = mixer.Read(floatBuffer, 0, toRead);
                if (samplesRead == 0) break;

                int byteIndex = 0;
                for (int i = 0; i < samplesRead; i++)
                {
                    short s = (short)Math.Clamp(floatBuffer[i] * 32767f, -32768f, 32767f);
                    byteBuffer[byteIndex++] = (byte)(s & 0xFF);
                    byteBuffer[byteIndex++] = (byte)((s >> 8) & 0xFF);
                }

                writer.Write(byteBuffer, 0, byteIndex);
                samplesWritten += samplesRead;

                int pct = (int)Math.Clamp((samplesWritten * 100.0) / totalSamples, 0, 100);
                progress?.Report(new ExportProgress("Mastering Audio Stems...", pct, samplesWritten, totalSamples));
            }

            writer.Flush();
            return outputWavPath;
        }, ct);
    }

    public async Task ExportSrtSubtitlesAsync(IReadOnlyList<ClipEntity> clips, string outputSrtPath)
    {
        await Task.Run(() =>
        {
            var sb = new StringBuilder();
            int index = 1;

            foreach (var clip in clips.OrderBy(c => c.StartMs))
            {
                if (string.IsNullOrWhiteSpace(clip.ScriptText)) continue;

                sb.AppendLine(index.ToString());
                sb.AppendLine($"{FormatSrtTime(clip.StartMs)} --> {FormatSrtTime(clip.EndMs)}");
                sb.AppendLine($"[{clip.SpeakerName}] {clip.ScriptText.Trim()}");
                sb.AppendLine();
                index++;
            }

            File.WriteAllText(outputSrtPath, sb.ToString(), Encoding.UTF8);
        });
    }

    public async Task ExportVttSubtitlesAsync(IReadOnlyList<ClipEntity> clips, string outputVttPath)
    {
        await Task.Run(() =>
        {
            var sb = new StringBuilder();
            sb.AppendLine("WEBVTT - DubStage Studio Subtitle Export");
            sb.AppendLine();

            foreach (var clip in clips.OrderBy(c => c.StartMs))
            {
                if (string.IsNullOrWhiteSpace(clip.ScriptText)) continue;

                sb.AppendLine($"{FormatVttTime(clip.StartMs)} --> {FormatVttTime(clip.EndMs)}");
                sb.AppendLine($"<v {clip.SpeakerName}>{clip.ScriptText.Trim()}");
                sb.AppendLine();
            }

            File.WriteAllText(outputVttPath, sb.ToString(), Encoding.UTF8);
        });
    }

    private static string FormatSrtTime(long ms)
    {
        var ts = TimeSpan.FromMilliseconds(ms);
        return $"{ts.Hours:D2}:{ts.Minutes:D2}:{ts.Seconds:D2},{ts.Milliseconds:D3}";
    }

    private static string FormatVttTime(long ms)
    {
        var ts = TimeSpan.FromMilliseconds(ms);
        return $"{ts.Hours:D2}:{ts.Minutes:D2}:{ts.Seconds:D2}.{ts.Milliseconds:D3}";
    }
}
