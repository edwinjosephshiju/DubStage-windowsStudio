using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using DubStage.ViewModels;

namespace DubStage.Views;

public sealed partial class DubStageView : UserControl
{
    public static readonly DependencyProperty ViewModelProperty =
        DependencyProperty.Register(nameof(ViewModel), typeof(MainViewModel), typeof(DubStageView),
            new PropertyMetadata(null));

    public MainViewModel? ViewModel
    {
        get => (MainViewModel?)GetValue(ViewModelProperty);
        set => SetValue(ViewModelProperty, value);
    }

    public DubStageView()
    {
        InitializeComponent();
    }

    private void OnWaveformSeekRequested(long targetMs)
    {
        ViewModel?.SeekTo(targetMs);
    }

    private async void OnExportMasterClick(object sender, RoutedEventArgs e)
    {
        if (ViewModel != null)
        {
            await ViewModel.ExportMasterAsync();
        }
    }
}
