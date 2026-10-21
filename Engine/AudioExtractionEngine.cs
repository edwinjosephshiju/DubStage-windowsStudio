using NAudio.Wave;
using DubStage.Models;

namespace DubStage.Engine;

public class AudioExtractionEngine
{
    public const int TargetSampleRate = 44100;
    public const int TargetChannels = 2;

    public async Task<string> ExtractAudioToWavAsync(
        string sourceVideoPath,
        string outputWavPath,
        IProgress<int>? progress = null,
        CancellationToken ct = default)
    {
        return await Task.Run(() =>
        {
            if (File.Exists(outputWavPath)) File.Delete(outputWavPath);

            using var reader = new MediaFoundationReader(sourceVideoPath);
            var targetFormat = new WaveFormat(TargetSampleRate, 16, TargetChannels);

            using var resampler = new MediaFoundationResampler(reader, targetFormat)
            {
                ResamplerQuality = 60
            };

            var totalBytes = reader.Length;
            using var writer = new WaveFileWriter(outputWavPath, targetFormat);

            var buffer = new byte[65536];
            long bytesProcessed = 0;
            int read;

            while ((read = resampler.Read(buffer, 0, buffer.Length)) > 0)
            {
                ct.ThrowIfCancellationRequested();
                writer.Write(buffer, 0, read);
                bytesProcessed += read;

                if (totalBytes > 0)
                {
                    var pct = (int)Math.Clamp((bytesProcessed * 100.0) / totalBytes, 0, 100);
                    progress?.Report(pct);
                }
            }

            writer.Flush();
            return outputWavPath;
        }, ct);
    }
}
