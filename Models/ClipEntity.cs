namespace DubStage.Models;

public class ClipEntity
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string ProjectId { get; set; } = string.Empty;
    public int ClipIndex { get; set; } = 0;
    public long StartMs { get; set; } = 0;
    public long EndMs { get; set; } = 0;
    public string SpeakerName { get; set; } = "Speaker 1";
    public string ScriptText { get; set; } = string.Empty;
    public string? ActiveTakeId { get; set; }
    public bool IsMuted { get; set; } = false;
    public long CreatedAt { get; set; } = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

    public long DurationMs => Math.Max(0, EndMs - StartMs);
}
