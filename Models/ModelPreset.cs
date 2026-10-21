namespace DubStage.Models;

public enum DemucsPresetId
{
    HtDemucsFtVocals,
    HtDemucs4Stem
}

public class DemucsModelPreset
{
    public DemucsPresetId Id { get; set; }
    public string DisplayName { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public string DownloadUrl { get; set; } = string.Empty;
    public string ExpectedSha256 { get; set; } = string.Empty;
    public long FileSizeBytes { get; set; } = 165612636L;

    public static readonly DemucsModelPreset VocalsSpecialist = new()
    {
        Id = DemucsPresetId.HtDemucsFtVocals,
        DisplayName = "HT-Demucs FT Vocals Specialist",
        Description = "Fine-tuned vocal specialist with phase-perfect residual backing.",
        FileName = "htdemucs_ft_vocals.onnx",
        DownloadUrl = "https://huggingface.co/StemSplitio/htdemucs-ft-vocals-onnx/resolve/main/htdemucs_ft.onnx?download=true",
        ExpectedSha256 = "",
        FileSizeBytes = 165612636L
    };

    public static readonly DemucsModelPreset FourStemAllTrained = new()
    {
        Id = DemucsPresetId.HtDemucs4Stem,
        DisplayName = "HT-Demucs 4-Stem All-Trained",
        Description = "4-stem model (Drums, Bass, Other, Vocals) for neural sum backing.",
        FileName = "htdemucs_4stem.onnx",
        DownloadUrl = "https://huggingface.co/StemSplitio/htdemucs-onnx/resolve/main/htdemucs.onnx?download=true",
        ExpectedSha256 = "",
        FileSizeBytes = 165612636L
    };

    public static readonly IReadOnlyList<DemucsModelPreset> All = new[]
    {
        VocalsSpecialist,
        FourStemAllTrained
    };
}

public abstract record ModelStatus
{
    public record NotDownloaded(DemucsModelPreset Preset) : ModelStatus;
    public record Downloading(DemucsModelPreset Preset, long BytesRead, long TotalBytes, long SpeedBytesPerSec, int Percent, string Message) : ModelStatus;
    public record Ready(DemucsModelPreset Preset, string ModelPath, long FileSizeBytes, string Sha256Hex) : ModelStatus;
    public record Error(DemucsModelPreset Preset, string ErrorMessage) : ModelStatus;
}

public record SeparationProgress(string Stage, int Percent, long CurrentFrame, long TotalFrames);
public record ExportProgress(string Stage, int Percent, long CurrentSample, long TotalSamples);
