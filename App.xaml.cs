using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;

namespace DubStage;

public partial class App : Application
{
    public static MainWindow CurrentMainWindow { get; set; } = null!;
    public static DispatcherQueue DispatcherQueue { get; private set; } = null!;

    public App()
    {
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        DispatcherQueue = DispatcherQueue.GetForCurrentThread();
        CurrentMainWindow = new MainWindow();
        CurrentMainWindow.Activate();
    }
}
