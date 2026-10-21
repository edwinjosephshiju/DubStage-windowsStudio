using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using DubStage.ViewModels;

namespace DubStage.Views;

public sealed partial class DubStageView : UserControl
{
    public MainViewModel ViewModel => (MainViewModel)DataContext;

    public DubStageView()
    {
        InitializeComponent();
    }

    private void OnWaveformSeekRequested(long targetMs)
    {
        ViewModel.SeekTo(targetMs);
    }

    private async void OnExportMasterClick(object sender, RoutedEventArgs e)
    {
        await ViewModel.ExportMasterAsync();
    }
}
