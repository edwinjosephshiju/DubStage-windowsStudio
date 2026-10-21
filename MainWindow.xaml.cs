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
                // Desktop DAW standard resolution: 1400x900
                appWindow.Resize(new SizeInt32(1400, 900));

                // Center window on primary monitor
                var displayArea = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary);
                if (displayArea != null)
                {
                    var workArea = displayArea.WorkArea;
                    int x = (workArea.Width - 1400) / 2;
                    int y = (workArea.Height - 900) / 2;
                    appWindow.Move(new PointInt32(Math.Max(0, x), Math.Max(0, y)));
                }

                // Set title
                appWindow.Title = "DubStage - AI Audio Dubbing & ADR Studio";
            }
        }
        catch (Exception ex)
        {
            App.LogCrash("MainWindow.ConfigureWindow", ex);
        }
    }
}
