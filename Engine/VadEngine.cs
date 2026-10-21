using NAudio.Wave;
using DubStage.Models;

namespace DubStage.Engine;

public class VadEngine
{
    public const int SampleRate = 44100;
    public const int FrameDurationMs = 25;
    public const int FrameSamples = (SampleRate * FrameDurationMs) / 1000; // 1102 samples

    public async Task<List<ClipEntity>> DetectDialogueClipsAsync(
        string projectId,
        string vocalsWavPath,
        float sensitivity = 0.6f,
        CancellationToken ct = default)
    {
        return await Task.Run(() =>
        {
            var clips = new List<ClipEntity>();
            if (!File.Exists(vocalsWavPath)) return clips;

            using var reader = new WaveFileReader(vocalsWavPath);
            var sampleProvider = reader.ToSampleProvider();

            var frameBuffer = new float[FrameSamples * 2]; // Stereo frame
            var frameRmsList = new List<float>();
            var framePitchList = new List<float>();
            int frameIndex = 0;

            int read;
            while ((read = sampleProvider.Read(frameBuffer, 0, frameBuffer.Length)) > 0)
            {
                ct.ThrowIfCancellationRequested();

                double sumSq = 0;
                int monoCount = read / 2;
                var monoSamples = new float[monoCount];

                for (int i = 0; i < monoCount; i++)
                {
                    float l = frameBuffer[i * 2];
                    float r = (i * 2 + 1 < read) ? frameBuffer[i * 2 + 1] : l;
                    float mono = (l + r) * 0.5f;
                    monoSamples[i] = mono;
                    sumSq += mono * mono;
                }

                float rms = (float)Math.Sqrt(sumSq / Math.Max(1, monoCount));
                frameRmsList.Add(rms);

                // Autocorrelation pitch proxy (F0 range: 80Hz - 400Hz)
                float pitch = EstimatePitch(monoSamples, SampleRate);
                framePitchList.Add(pitch);

                frameIndex++;
            }

            if (frameRmsList.Count == 0) return clips;

            // Adaptive energy threshold based on vocal energy distribution and sensitivity
            var sortedRms = frameRmsList.OrderBy(x => x).ToList();
            float noiseFloor = sortedRms[(int)(sortedRms.Count * 0.20)];
            float peakFloor = sortedRms[(int)(sortedRms.Count * 0.90)];
            float dynRange = Math.Max(1e-4f, peakFloor - noiseFloor);

            // Higher sensitivity -> lower threshold
            float thresholdFactor = 0.35f * (1.1f - Math.Clamp(sensitivity, 0.1f, 0.95f));
            float speechThreshold = noiseFloor + dynRange * thresholdFactor;

            // Classify frames
            var isSpeech = new bool[frameRmsList.Count];
            for (int i = 0; i < frameRmsList.Count; i++)
            {
                isSpeech[i] = frameRmsList[i] >= speechThreshold;
            }

            // Group speech frames into contiguous segments
            var rawSpans = new List<(int startFrame, int endFrame)>();
            int inSpanStart = -1;

            for (int i = 0; i < isSpeech.Length; i++)
            {
                if (isSpeech[i])
                {
                    if (inSpanStart == -1) inSpanStart = i;
                }
                else
                {
                    if (inSpanStart != -1)
                    {
                        rawSpans.Add((inSpanStart, i));
                        inSpanStart = -1;
                    }
                }
            }
            if (inSpanStart != -1)
            {
                rawSpans.Add((inSpanStart, isSpeech.Length));
            }

            // Merge brief pauses (< 300ms = 12 frames) and filter short clicks (< 150ms = 6 frames)
            int minSpanFrames = 6;
            int maxPauseFrames = 12;

            var mergedSpans = new List<(int startFrame, int endFrame)>();
            foreach (var span in rawSpans)
            {
                if ((span.endFrame - span.startFrame) < minSpanFrames) continue;

                if (mergedSpans.Count > 0)
                {
                    var last = mergedSpans[^1];
                    int gap = span.startFrame - last.endFrame;
                    if (gap <= maxPauseFrames)
                    {
                        mergedSpans[^1] = (last.startFrame, span.endFrame);
                        continue;
                    }
                }
                mergedSpans.Add(span);
            }

            // Convert frame ranges to millisecond ClipEntities with speaker classification
            int clipIdx = 1;
            foreach (var span in mergedSpans)
            {
                long startMs = span.startFrame * (long)FrameDurationMs;
                long endMs = span.endFrame * (long)FrameDurationMs;

                // Estimate median pitch in this span to differentiate speakers
                var spanPitches = new List<float>();
                for (int f = span.startFrame; f < Math.Min(span.endFrame, framePitchList.Count); f++)
                {
                    if (framePitchList[f] > 0) spanPitches.Add(framePitchList[f]);
                }

                string speaker = "Speaker 1";
                if (spanPitches.Count > 0)
                {
                    spanPitches.Sort();
                    float medianPitch = spanPitches[spanPitches.Count / 2];
                    if (medianPitch > 210f) speaker = "Speaker 2"; // Higher formant/pitch range
                }

                clips.Add(new ClipEntity
                {
                    Id = Guid.NewGuid().ToString(),
                    ProjectId = projectId,
                    ClipIndex = clipIdx++,
                    StartMs = startMs,
                    EndMs = endMs,
                    SpeakerName = speaker,
                    ScriptText = $"Dialogue line {clipIdx - 1}"
                });
            }

            return clips;
        }, ct);
    }

    private static float EstimatePitch(float[] mono, int sampleRate)
    {
        int minLag = sampleRate / 400; // ~400 Hz
        int maxLag = sampleRate / 80;  // ~80 Hz
        if (mono.Length <= maxLag) return 0f;

        float bestCorr = 0f;
        int bestLag = -1;

        for (int lag = minLag; lag < maxLag; lag++)
        {
            float sum = 0f;
            int count = mono.Length - lag;
            for (int i = 0; i < count; i++)
            {
                sum += mono[i] * mono[i + lag];
            }
            if (sum > bestCorr)
            {
                bestCorr = sum;
                bestLag = lag;
            }
        }

        return (bestLag > 0 && bestCorr > 0.05f) ? (float)sampleRate / bestLag : 0f;
    }
}
