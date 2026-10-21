using Microsoft.UI;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Shapes;
using Windows.UI;

namespace DubStage.Views.Components;

public sealed partial class DualWaveformControl : UserControl
{
    public static readonly DependencyProperty VocalPeaksProperty =
        DependencyProperty.Register(nameof(VocalPeaks), typeof(float[]), typeof(DualWaveformControl),
            new PropertyMetadata(Array.Empty<float>(), (d, e) => ((DualWaveformControl)d).RedrawWaveforms()));

    public static readonly DependencyProperty TakePeaksProperty =
        DependencyProperty.Register(nameof(TakePeaks), typeof(float[]), typeof(DualWaveformControl),
            new PropertyMetadata(Array.Empty<float>(), (d, e) => ((DualWaveformControl)d).RedrawWaveforms()));

    public static readonly DependencyProperty PlayheadMsProperty =
        DependencyProperty.Register(nameof(PlayheadMs), typeof(long), typeof(DualWaveformControl),
            new PropertyMetadata(0L, (d, e) => ((DualWaveformControl)d).UpdatePlayhead()));

    public static readonly DependencyProperty DurationMsProperty =
        DependencyProperty.Register(nameof(DurationMs), typeof(long), typeof(DualWaveformControl),
            new PropertyMetadata(1000L, (d, e) => ((DualWaveformControl)d).RedrawWaveforms()));

    public float[] VocalPeaks
    {
        get => (float[])GetValue(VocalPeaksProperty);
        set => SetValue(VocalPeaksProperty, value);
    }

    public float[] TakePeaks
    {
        get => (float[])GetValue(TakePeaksProperty);
        set => SetValue(TakePeaksProperty, value);
    }

    public long PlayheadMs
    {
        get => (long)GetValue(PlayheadMsProperty);
        set => SetValue(PlayheadMsProperty, value);
    }

    public long DurationMs
    {
        get => (long)GetValue(DurationMsProperty);
        set => SetValue(DurationMsProperty, value);
    }

    public event Action<long>? SeekRequested;

    private Line? _vocalPlayheadLine;
    private Line? _takePlayheadLine;

    public DualWaveformControl()
    {
        InitializeComponent();
        SizeChanged += (s, e) => RedrawWaveforms();
    }

    private void RedrawWaveforms()
    {
        DrawCanvasWaveform(VocalWaveformCanvas, VocalPeaks, Color.FromArgb(255, 255, 83, 118), ref _vocalPlayheadLine);
        DrawCanvasWaveform(TakeWaveformCanvas, TakePeaks, Color.FromArgb(255, 0, 229, 163), ref _takePlayheadLine);
        UpdatePlayhead();
    }

    private void DrawCanvasWaveform(Canvas? canvas, float[]? peaks, Color color, ref Line? playhead)
    {
        if (canvas == null) return;
        canvas.Children.Clear();
        double w = canvas.ActualWidth;
        double h = canvas.ActualHeight;
        if (w <= 0 || h <= 0) return;

        double midY = h / 2.0;

        // Draw center reference line
        var centerLine = new Line
        {
            X1 = 0,
            Y1 = midY,
            X2 = w,
            Y2 = midY,
            Stroke = new SolidColorBrush(Color.FromArgb(60, 255, 255, 255)),
            StrokeThickness = 1
        };
        canvas.Children.Add(centerLine);

        if (peaks != null && peaks.Length > 0)
        {
            var brush = new SolidColorBrush(color);
            int barCount = (int)(w / 3.0);
            if (barCount <= 0) barCount = 1;

            for (int i = 0; i < barCount; i++)
            {
                int peakIdx = (int)((i * (long)peaks.Length) / barCount);
                if (peakIdx >= peaks.Length) break;

                float amp = Math.Clamp(peaks[peakIdx], 0.05f, 1.0f);
                double barH = amp * (midY - 4);
                double x = i * 3.0;

                var line = new Line
                {
                    X1 = x,
                    Y1 = midY - barH,
                    X2 = x,
                    Y2 = midY + barH,
                    Stroke = brush,
                    StrokeThickness = 2
                };
                canvas.Children.Add(line);
            }
        }

        // Add playhead line
        playhead = new Line
        {
            X1 = 0,
            Y1 = 0,
            X2 = 0,
            Y2 = h,
            Stroke = new SolidColorBrush(Color.FromArgb(255, 79, 128, 255)),
            StrokeThickness = 2
        };
        canvas.Children.Add(playhead);
    }

    private void UpdatePlayhead()
    {
        if (VocalWaveformCanvas == null) return;
        double w = VocalWaveformCanvas.ActualWidth;
        if (w <= 0 || DurationMs <= 0) return;

        double x = (PlayheadMs / (double)DurationMs) * w;
        x = Math.Clamp(x, 0, w);

        if (_vocalPlayheadLine != null)
        {
            _vocalPlayheadLine.X1 = x;
            _vocalPlayheadLine.X2 = x;
        }
        if (_takePlayheadLine != null)
        {
            _takePlayheadLine.X1 = x;
            _takePlayheadLine.X2 = x;
        }
    }

    private void OnCanvasPointerPressed(object sender, PointerRoutedEventArgs e)
    {
        if (sender is Canvas canvas && DurationMs > 0)
        {
            var point = e.GetCurrentPoint(canvas);
            double w = canvas.ActualWidth;
            if (w > 0)
            {
                long targetMs = (long)((point.Position.X / w) * DurationMs);
                SeekRequested?.Invoke(Math.Clamp(targetMs, 0, DurationMs));
            }
        }
    }
}
