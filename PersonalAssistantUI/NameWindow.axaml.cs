using System;
using System.IO;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;

namespace PersonalAssistantUI;

public partial class NameWindow : Window
{
    public NameWindow()
    {
        InitializeComponent();
    }

    private void Window_PointerPressed(object sender, PointerPressedEventArgs e)
    {
        if (e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
        {
            BeginMoveDrag(e);
        }
    }

    private void TestButton_Click(object sender, RoutedEventArgs e)
    {
        var phoneticBox = this.FindControl<TextBox>("PhoneticNameInput");
        var phoneticName = phoneticBox?.Text?.Trim();
        if (string.IsNullOrEmpty(phoneticName)) return;

        try
        {
            var workingDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
            var cmdPath = Path.Combine(workingDir, "command.txt");
            File.WriteAllText(cmdPath, $"TEST_NAME:{phoneticName}");
        }
        catch { }
    }

    private void SaveButton_Click(object sender, RoutedEventArgs e)
    {
        var phoneticBox = this.FindControl<TextBox>("PhoneticNameInput");
        var actualBox = this.FindControl<TextBox>("ActualNameInput");
        var phoneticName = phoneticBox?.Text?.Trim();
        var actualName = actualBox?.Text?.Trim();
        if (string.IsNullOrEmpty(phoneticName) || string.IsNullOrEmpty(actualName)) return;

        try
        {
            var workingDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
            var memPath = Path.Combine(workingDir, "memory.json");
            string text = "{}";
            if (File.Exists(memPath)) text = File.ReadAllText(memPath);
            
            using var doc = System.Text.Json.JsonDocument.Parse(text);
            var root = doc.RootElement;
            var dict = new System.Collections.Generic.Dictionary<string, string>();
            foreach (var prop in root.EnumerateObject())
            {
                dict[prop.Name] = prop.Value.GetString() ?? "";
            }
            dict["user_name_phonetic"] = phoneticName;
            dict["user_name"] = actualName;
            
            var json = System.Text.Json.JsonSerializer.Serialize(dict);
            File.WriteAllText(memPath, json);
        }
        catch { }
        
        Close();
    }
}
