namespace DubStage.Models;

public class TakeEntity
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string ClipId { get; set; } = string.Empty;
    public int TakeNumber { get; set; } = 1;
    public string AudioFilePath { get; set; } = string.Empty;
    public long DurationMs { get; set; } = 0;
    public float GainDb { get; set; } = 0.0f;
    public long TimeOffsetMs { get; set; } = 0L;
    public float NoiseGateThresholdDb { get; set; } = -60.0f;
    public long RecordedAt { get; set; } = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
}
