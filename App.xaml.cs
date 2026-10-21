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

        UnhandledException += (sender, e) =>
        {
            LogCrash("App.UnhandledException", e.Exception);
            // Mark handled if possible so Windows doesn't immediately fail-fast if recoverable
            e.Handled = true;
        };

        AppDomain.CurrentDomain.UnhandledException += (sender, e) =>
        {
            if (e.ExceptionObject is Exception ex)
            {
                LogCrash("AppDomain.UnhandledException", ex);
            }
        };

        TaskScheduler.UnobservedTaskException += (sender, e) =>
        {
            LogCrash("TaskScheduler.UnobservedTaskException", e.Exception);
            e.SetObserved();
        };
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        try
        {
            DispatcherQueue = DispatcherQueue.GetForCurrentThread();
            CurrentMainWindow = new MainWindow();
            CurrentMainWindow.Activate();
        }
        catch (Exception ex)
        {
            LogCrash("OnLaunched", ex);
            throw;
        }
    }

    public static void LogCrash(string source, Exception? ex)
    {
        try
        {
            var logText = $"[{DateTime.UtcNow:yyyy-MM-dd HH:mm:ss}] CRASH in {source}: {ex?.GetType().FullName}: {ex?.Message}\n{ex?.StackTrace}\n\n";

            // Write to LocalApplicationData fallback
            var baseDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DubStageStudio");
            Directory.CreateDirectory(baseDir);
            File.AppendAllText(Path.Combine(baseDir, "crash.log"), logText);

            // Also try write to ApplicationData local folder
            try
            {
                var pkgDir = Windows.Storage.ApplicationData.Current.LocalFolder.Path;
                File.AppendAllText(Path.Combine(pkgDir, "crash.log"), logText);
            }
            catch { }
        }
        catch { }
    }
}
