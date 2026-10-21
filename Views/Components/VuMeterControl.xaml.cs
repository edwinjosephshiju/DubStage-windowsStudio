using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace DubStage.Views.Components;

public sealed partial class VuMeterControl : UserControl
{
    public static readonly DependencyProperty LeftLevelDbProperty =
        DependencyProperty.Register(nameof(LeftLevelDb), typeof(float), typeof(VuMeterControl),
            new PropertyMetadata(-60.0f, (d, e) => ((VuMeterControl)d).UpdateLevels()));

    public static readonly DependencyProperty RightLevelDbProperty =
        DependencyProperty.Register(nameof(RightLevelDb), typeof(float), typeof(VuMeterControl),
            new PropertyMetadata(-60.0f, (d, e) => ((VuMeterControl)d).UpdateLevels()));

    public float LeftLevelDb
    {
        get => (float)GetValue(LeftLevelDbProperty);
        set => SetValue(LeftLevelDbProperty, value);
    }

    public float RightLevelDb
    {
        get => (float)GetValue(RightLevelDbProperty);
        set => SetValue(RightLevelDbProperty, value);
    }

    public VuMeterControl()
    {
        InitializeComponent();
    }

    private void UpdateLevels()
    {
        LeftProgressBar.Value = Math.Clamp(LeftLevelDb, -60, 0);
        RightProgressBar.Value = Math.Clamp(RightLevelDb, -60, 0);
    }
}
