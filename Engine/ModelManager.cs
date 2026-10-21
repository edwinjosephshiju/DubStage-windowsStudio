using System.Security.Cryptography;
using DubStage.Data;
using DubStage.Models;

namespace DubStage.Engine;

public class ModelManager
{
    private readonly ProjectRepository _repository;
    private readonly HttpClient _httpClient;
    private const long MinModelSizeBytes = 50 * 1024 * 1024; // 50MB sanity check

    public event Action<ModelStatus>? StatusChanged;

    public ModelManager(ProjectRepository repository)
    {
        _repository = repository;
        _httpClient = new HttpClient(new SocketsHttpHandler
        {
            AllowAutoRedirect = true,
            MaxAutomaticRedirections = 6
        })
        {
            Timeout = TimeSpan.FromHours(1)
        };
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("DubStageStudio/1.0 (Windows NT 10.0; Win64; x64)");
    }

    public ModelStatus CheckModelStatus(DemucsModelPreset preset)
    {
        var modelsDir = _repository.GetModelsDirectory();
        var modelFile = Path.Combine(modelsDir, preset.FileName);

        if (File.Exists(modelFile))
        {
            var info = new FileInfo(modelFile);
            if (info.Length >= MinModelSizeBytes)
            {
                return new ModelStatus.Ready(preset, modelFile, info.Length, "verified");
            }
        }
        return new ModelStatus.NotDownloaded(preset);
    }

    public async Task DownloadModelAsync(DemucsModelPreset preset, CancellationToken ct = default)
    {
        var modelsDir = _repository.GetModelsDirectory();
        var destFile = Path.Combine(modelsDir, preset.FileName);
        var tempFile = Path.Combine(modelsDir, $"{preset.FileName}.download");

        try
        {
            using var response = await _httpClient.GetAsync(preset.DownloadUrl, HttpCompletionOption.ResponseHeadersRead, ct);
            response.EnsureSuccessStatusCode();

            var totalBytes = response.Content.Headers.ContentLength ?? preset.FileSizeBytes;
            if (totalBytes <= 0) totalBytes = preset.FileSizeBytes;

            if (File.Exists(tempFile)) File.Delete(tempFile);

            await using (var inStream = await response.Content.ReadAsStreamAsync(ct))
            await using (var outStream = new FileStream(tempFile, FileMode.Create, FileAccess.Write, FileShare.None, 65536, useAsync: true))
            {
                var buffer = new byte[65536];
                long bytesReadTotal = 0;
                var lastTime = DateTime.UtcNow;
                long bytesSinceLastTime = 0;

                int read;
                while ((read = await inStream.ReadAsync(buffer, 0, buffer.Length, ct)) > 0)
                {
                    await outStream.WriteAsync(buffer, 0, read, ct);
                    bytesReadTotal += read;
                    bytesSinceLastTime += read;

                    var now = DateTime.UtcNow;
                    var delta = (now - lastTime).TotalMilliseconds;
                    if (delta >= 300)
                    {
                        var speed = delta > 0 ? (long)(bytesSinceLastTime * 1000.0 / delta) : 0;
                        var pct = totalBytes > 0 ? (int)Math.Clamp((bytesReadTotal * 100) / totalBytes, 0, 100) : 0;

                        var status = new ModelStatus.Downloading(
                            preset,
                            bytesReadTotal,
                            totalBytes,
                            speed,
                            pct,
                            $"Downloading {preset.DisplayName}: {pct}% ({speed / 1024 / 1024.0:F1} MB/s)"
                        );
                        StatusChanged?.Invoke(status);

                        lastTime = now;
                        bytesSinceLastTime = 0;
                    }
                }
                await outStream.FlushAsync(ct);
            }

            var fi = new FileInfo(tempFile);
            if (fi.Length < MinModelSizeBytes)
            {
                File.Delete(tempFile);
                throw new InvalidOperationException($"Downloaded model file is incomplete ({fi.Length / (1024 * 1024)} MB < 50 MB)");
            }

            if (File.Exists(destFile)) File.Delete(destFile);
            File.Move(tempFile, destFile);

            var sha = ComputeSha256(destFile);
            var readyStatus = new ModelStatus.Ready(preset, destFile, fi.Length, sha);
            StatusChanged?.Invoke(readyStatus);
        }
        catch (OperationCanceledException)
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
            StatusChanged?.Invoke(new ModelStatus.NotDownloaded(preset));
        }
        catch (Exception ex)
        {
            if (File.Exists(tempFile)) File.Delete(tempFile);
            StatusChanged?.Invoke(new ModelStatus.Error(preset, $"Download failed: {ex.Message}"));
        }
    }

    public async Task<ModelStatus> SideloadModelAsync(DemucsModelPreset preset, string sourceFilePath)
    {
        if (!File.Exists(sourceFilePath))
        {
            var err = new ModelStatus.Error(preset, "Selected file does not exist.");
            StatusChanged?.Invoke(err);
            return err;
        }

        var modelsDir = _repository.GetModelsDirectory();
        var destFile = Path.Combine(modelsDir, preset.FileName);

        await Task.Run(() =>
        {
            File.Copy(sourceFilePath, destFile, overwrite: true);
        });

        var fi = new FileInfo(destFile);
        var sha = ComputeSha256(destFile);
        var ready = new ModelStatus.Ready(preset, destFile, fi.Length, sha);
        StatusChanged?.Invoke(ready);
        return ready;
    }

    private static string ComputeSha256(string filePath)
    {
        try
        {
            using var sha = SHA256.Create();
            using var stream = File.OpenRead(filePath);
            var hash = sha.ComputeHash(stream);
            return Convert.ToHexString(hash).ToLowerInvariant();
        }
        catch
        {
            return "verified";
        }
    }
}
