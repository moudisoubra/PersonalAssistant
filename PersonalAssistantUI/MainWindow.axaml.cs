using Avalonia.Controls;
using Avalonia.Input;
using PersonalAssistantUI.ViewModels;

namespace PersonalAssistantUI;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        
        // This links the UI to our Python-running ViewModel
        DataContext = new MainViewModel();
    }

    private void Window_PointerPressed(object sender, PointerPressedEventArgs e)
    {
        // Allow the user to drag the window by clicking anywhere on the background
        if (e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
        {
            BeginMoveDrag(e);
        }
    }

    private void HelpButton_Click(object sender, Avalonia.Interactivity.RoutedEventArgs e)
    {
        var helpWindow = new HelpWindow();
        helpWindow.ShowDialog(this);
    }
}