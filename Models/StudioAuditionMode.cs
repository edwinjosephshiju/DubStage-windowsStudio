namespace DubStage.Models;

public enum StudioAuditionMode
{
    FullDubMix,         // Backing + active user takes (vocal replaced where takes exist)
    MuteOriginalVocals,  // Backing + user takes only (pure karaoke / vocal isolation)
    SoloActiveTake,     // Only the selected take without backing or original vocal
    OriginalOnly        // Pure original video audio track
}

public class MixTakeTrack
{
    public string TakeId { get; set; } = string.Empty;
    public string AudioFilePath { get; set; } = string.Empty;
    public long StartMs { get; set; }
    public long DurationMs { get; set; }
    public float GainDb { get; set; }
    public long TimeOffsetMs { get; set; }
}
