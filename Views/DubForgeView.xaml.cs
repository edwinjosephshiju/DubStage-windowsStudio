using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.Media.Core;
using Windows.Storage.Pickers;
using DubStage.Models;
using DubStage.ViewModels;

namespace DubStage.Views;

public sealed partial class DubForgeView : UserControl
{
    public static readonly DependencyProperty ViewModelProperty =
        DependencyProperty.Register(nameof(ViewModel), typeof(MainViewModel), typeof(DubForgeView),
            new PropertyMetadata(null, (d, e) => ((DubForgeView)d).OnViewModelChanged((MainViewModel?)e.NewValue)));

    public MainViewModel? ViewModel
    {
        get => (MainViewModel?)GetValue(ViewModelProperty);
        set => SetValue(ViewModelProperty, value);
    }

    public IReadOnlyList<DemucsModelPreset> AvailablePresets => DemucsModelPreset.All;

    public DubForgeView()
    {
        InitializeComponent();
    }

    private void OnViewModelChanged(MainViewModel? newVm)
    {
        if (newVm != null)
        {
            newVm.PropertyChanged += (s, e) =>
            {
                if (e.PropertyName == nameof(MainViewModel.ActiveProject))
                {
                    UpdateVideoSource();
                }
            };
            UpdateVideoSource();
        }
    }

    private void UpdateVideoSource()
    {
        if (ViewModel?.ActiveProject != null && !string.IsNullOrEmpty(ViewModel.ActiveProject.VideoPath) && File.Exists(ViewModel.ActiveProject.VideoPath))
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
        if (ViewModel != null)
        {
            await ViewModel.DownloadModelAsync();
        }
    }

    private async void OnSideloadModelClick(object sender, RoutedEventArgs e)
    {
        if (ViewModel == null) return;
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
        if (ViewModel != null)
        {
            await ViewModel.ExtractAudioAsync();
        }
    }

    private async void OnSeparateStemsClick(object sender, RoutedEventArgs e)
    {
        if (ViewModel != null)
        {
            await ViewModel.SeparateStemsAsync();
        }
    }

    private async void OnDetectDialogueClick(object sender, RoutedEventArgs e)
    {
        if (ViewModel != null)
        {
            await ViewModel.DetectDialogueClipsAsync();
        }
    }

    private void OnSwitchToStageClick(object sender, RoutedEventArgs e)
    {
        if (ViewModel != null)
        {
            ViewModel.SelectedTabIndex = 1;
        }
    }
}
