namespace DubStage.Models;

public class ProjectEntity
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Title { get; set; } = "Untitled Studio Project";
    public string VideoPath { get; set; } = string.Empty;
    public long VideoDurationMs { get; set; } = 0;
    public int VideoWidth { get; set; } = 1920;
    public int VideoHeight { get; set; } = 1080;
    public int SampleRate { get; set; } = 44100;
    public int Channels { get; set; } = 2;
    public string? OriginalWavPath { get; set; }
    public string? VocalsWavPath { get; set; }
    public string? BackingWavPath { get; set; }
    public string? ModelChecksum { get; set; }
    public string Status { get; set; } = StatusCreated;
    public long CreatedAt { get; set; } = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
    public long UpdatedAt { get; set; } = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

    public const string StatusCreated = "CREATED";
    public const string StatusAudioExtracting = "AUDIO_EXTRACTING";
    public const string StatusAudioExtracted = "AUDIO_EXTRACTED";
    public const string StatusSeparating = "SEPARATING";
    public const string StatusSeparated = "SEPARATED";
    public const string StatusReady = "READY";
}
