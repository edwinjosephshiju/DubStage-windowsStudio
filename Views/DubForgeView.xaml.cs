using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.Media.Core;
using Windows.Storage.Pickers;
using DubStage.Models;
using DubStage.ViewModels;

namespace DubStage.Views;

public sealed partial class DubForgeView : UserControl
{
    public MainViewModel ViewModel => (MainViewModel)DataContext;
    public IReadOnlyList<DemucsModelPreset> AvailablePresets => DemucsModelPreset.All;

    public DubForgeView()
    {
        InitializeComponent();
        DataContextChanged += OnDataContextChanged;
    }

    private void OnDataContextChanged(FrameworkElement sender, DataContextChangedEventArgs args)
    {
        if (ViewModel != null)
        {
            ViewModel.PropertyChanged += (s, e) =>
            {
                if (e.PropertyName == nameof(MainViewModel.ActiveProject))
                {
                    UpdateVideoSource();
                }
            };
        }
    }

    private void UpdateVideoSource()
    {
        if (ViewModel.ActiveProject != null && !string.IsNullOrEmpty(ViewModel.ActiveProject.VideoPath) && File.Exists(ViewModel.ActiveProject.VideoPath))
        {
            try
            {
                var uri = new Uri(ViewModel.ActiveProject.VideoPath);
                PlayerElement.Source = MediaSource.CreateFromUri(uri);
            }
            catch { }
        }
    }

    private async void OnDownloadModelClick(object sender, RoutedEventArgs e)
    {
        await ViewModel.DownloadModelAsync();
    }

    private async void OnSideloadModelClick(object sender, RoutedEventArgs e)
    {
        var picker = new FileOpenPicker();
        picker.FileTypeFilter.Add(".onnx");

        var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(App.CurrentMainWindow);
        WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd);

        var file = await picker.PickSingleFileAsync();
        if (file != null)
        {
            await ViewModel.SideloadModelAsync(file.Path);
        }
    }

    private async void OnExtractAudioClick(object sender, RoutedEventArgs e)
    {
        await ViewModel.ExtractAudioAsync();
    }

    private async void OnSeparateStemsClick(object sender, RoutedEventArgs e)
    {
        await ViewModel.SeparateStemsAsync();
    }

    private async void OnDetectDialogueClick(object sender, RoutedEventArgs e)
    {
        await ViewModel.DetectDialogueClipsAsync();
    }

    private void OnSwitchToStageClick(object sender, RoutedEventArgs e)
    {
        ViewModel.SelectedTabIndex = 1; // Switch to DubStage tab
    }
}
