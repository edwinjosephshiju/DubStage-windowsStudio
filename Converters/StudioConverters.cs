using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Data;
using Microsoft.UI.Xaml.Media;
using Windows.UI;

namespace DubStage.Converters;

public class PlayPauseIconConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        bool isPlaying = value is bool b && b;
        return isPlaying ? "\uE769" : "\uE768"; // Pause vs Play Segoe Fluent Icons
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class ClipCountConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        int count = value is int c ? c : 0;
        return $"{count} cues";
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class MsToTimecodeConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        long ms = value switch
        {
            long l => l,
            int i => i,
            _ => 0L
        };
        var ts = TimeSpan.FromMilliseconds(ms);
        return $"{ts.Minutes:D2}:{ts.Seconds:D2}.{ts.Milliseconds / 100:D1}";
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class RecordingButtonColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        bool isRecording = value is bool b && b;
        return isRecording
            ? new SolidColorBrush(Color.FromArgb(255, 255, 51, 75))  // Crimson #FF334B
            : new SolidColorBrush(Color.FromArgb(255, 33, 36, 44));   // Slate #21242C
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class RecordingIconConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        bool isRecording = value is bool b && b;
        return isRecording ? "\uE71A" : "\uE720"; // Stop square vs Mic glyph
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class Tab0BrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        int idx = value is int i ? i : 0;
        return idx == 0
            ? new SolidColorBrush(Color.FromArgb(255, 79, 128, 255)) // Studio Accent
            : new SolidColorBrush(Color.FromArgb(255, 22, 24, 29));   // Container
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class Tab1BrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        int idx = value is int i ? i : 0;
        return idx == 1
            ? new SolidColorBrush(Color.FromArgb(255, 79, 128, 255)) // Studio Accent
            : new SolidColorBrush(Color.FromArgb(255, 22, 24, 29));   // Container
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class Tab0VisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        int idx = value is int i ? i : 0;
        return idx == 0 ? Visibility.Visible : Visibility.Collapsed;
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}

public class Tab1VisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        int idx = value is int i ? i : 0;
        return idx == 1 ? Visibility.Visible : Visibility.Collapsed;
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language) => throw new NotImplementedException();
}
