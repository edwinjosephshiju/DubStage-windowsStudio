using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using Windows.Storage.Pickers;
using DubStage.ViewModels;

namespace DubStage.Views;

public sealed partial class MainPageView : UserControl
{
    public MainViewModel ViewModel { get; }

    public MainPageView()
    {
        ViewModel = new MainViewModel();
        InitializeComponent();
        Loaded += async (s, e) =>
        {
            try
            {
                await ViewModel.InitializeAsync();
            }
            catch (Exception ex)
            {
                App.LogCrash("ViewModel.InitializeAsync", ex);
            }
        };
    }

    #region Tab Navigation

    private void OnDubForgeTabClick(object sender, RoutedEventArgs e)
    {
        ViewModel.SelectedTabIndex = 0;
    }

    private void OnDubStageTabClick(object sender, RoutedEventArgs e)
    {
        ViewModel.SelectedTabIndex = 1;
    }

    #endregion

    #region Actions & File Dialogs

    public async void OnOpenVideoClick(object sender, RoutedEventArgs e)
    {
        var picker = new FileOpenPicker();
        picker.SuggestedStartLocation = PickerLocationId.VideosLibrary;
        picker.FileTypeFilter.Add(".mp4");
        picker.FileTypeFilter.Add(".mkv");
        picker.FileTypeFilter.Add(".mov");
        picker.FileTypeFilter.Add(".avi");
        picker.FileTypeFilter.Add(".webm");

        var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(App.CurrentMainWindow);
        WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd);

        var file = await picker.PickSingleFileAsync();
        if (file != null)
        {
            await ViewModel.CreateNewProjectFromVideoAsync(file.Path);
        }
    }

    public async void OnExportClick(object sender, RoutedEventArgs e)
    {
        await ViewModel.ExportMasterAsync();
    }

    #endregion

    #region Keyboard Accelerators

    private void OnSpaceAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.TogglePlayPause();
        args.Handled = true;
    }

    private void OnRecordAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.ToggleRecord();
        args.Handled = true;
    }

    private void OnUpAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.SelectPreviousClip();
        args.Handled = true;
    }

    private void OnDownAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.SelectNextClip();
        args.Handled = true;
    }

    private void OnLeftAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.SeekBy(-1000);
        args.Handled = true;
    }

    private void OnRightAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.SeekBy(1000);
        args.Handled = true;
    }

    private void OnOpenAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        OnOpenVideoClick(this, new RoutedEventArgs());
        args.Handled = true;
    }

    private void OnExportAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        OnExportClick(this, new RoutedEventArgs());
        args.Handled = true;
    }

    private void OnSaveAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.SaveProjectCommand.Execute(null);
        args.Handled = true;
    }

    private void OnMuteAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.ToggleMuteOriginalVocals();
        args.Handled = true;
    }

    private void OnDeleteAcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.DeleteActiveTakeCommand.Execute(null);
        args.Handled = true;
    }

    private void OnTab1AcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.SelectedTabIndex = 0;
        args.Handled = true;
    }

    private void OnTab2AcceleratorInvoked(KeyboardAccelerator sender, KeyboardAcceleratorInvokedEventArgs args)
    {
        ViewModel.SelectedTabIndex = 1;
        args.Handled = true;
    }

    #endregion
}
