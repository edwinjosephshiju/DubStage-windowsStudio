using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Windows.Graphics;

namespace DubStage;

public sealed partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        App.CurrentMainWindow = this;
        ConfigureWindow();
    }

    private void ConfigureWindow()
    {
        try
        {
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            if (hwnd == IntPtr.Zero) return;

            var windowId = Win32Interop.GetWindowIdFromWindow(hwnd);
            var appWindow = AppWindow.GetFromWindowId(windowId);

            if (appWindow != null)
            {
                appWindow.Title = "DubStage - AI Audio Dubbing & ADR Studio";

                var displayArea = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary);
                if (displayArea != null)
                {
                    var workArea = displayArea.WorkArea;
                    int targetW = Math.Min(1400, Math.Max(800, workArea.Width - 60));
                    int targetH = Math.Min(900, Math.Max(500, workArea.Height - 60));
                    appWindow.Resize(new SizeInt32(targetW, targetH));

                    int x = Math.Max(0, (workArea.Width - targetW) / 2);
                    int y = Math.Max(0, (workArea.Height - targetH) / 2);
                    appWindow.Move(new PointInt32(x, y));
                }
            }
        }
        catch (Exception ex)
        {
            App.LogCrash("MainWindow.ConfigureWindow", ex);
        }
    }
}
