using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;

namespace PersonalAssistantUI.ViewModels;

public partial class MainViewModel : ViewModelBase
{
    [ObservableProperty]
    public partial string UserText { get; set; } = "...";

    [ObservableProperty]
    public partial string AssistantText { get; set; } = "Initializing...";

    [ObservableProperty]
    public partial string StatusText { get; set; } = "Booting up...";

    [ObservableProperty]
    public partial bool IsThinking { get; set; }

    [ObservableProperty]
    public partial bool IsTalking { get; set; }

    [ObservableProperty]
    public partial bool IsListening { get; set; }

    private void SetState(bool listening = false, bool thinking = false, bool talking = false)
    {
        Dispatcher.UIThread.Post(() =>
        {
            IsListening = listening;
            IsThinking = thinking;
            IsTalking = talking;
        });
    }

    public MainViewModel()
    {
        LoadMemory();
        UpdateSharedState();
        StartAgent();
    }

    [ObservableProperty]
    public partial string WakeWord { get; set; } = "BOB";

    private void LoadMemory()
    {
        try
        {
            var workingDir = Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, ".."));
            var memPath = Path.Combine(workingDir, "memory.json");
            if (File.Exists(memPath))
            {
                var text = File.ReadAllText(memPath);
                var match = System.Text.RegularExpressions.Regex.Match(text, "\"wake_word\"\\s*:\\s*\"([^\"]+)\"");
                if (match.Success) WakeWord = match.Groups[1].Value.ToUpper();
            }
        }
        catch { }
    }

    [ObservableProperty]
    public partial bool IsMuted { get; set; }

    [ObservableProperty]
    public partial double Volume { get; set; } = 1.0;

    partial void OnIsMutedChanged(bool value)
    {
        UpdateSharedState();
    }

    partial void OnVolumeChanged(double value)
    {
        UpdateSharedState();
    }

    private void UpdateSharedState()
    {
        try
        {
            var workingDir = Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, ".."));
            var statePath = Path.Combine(workingDir, "shared_state.json");
            var json = $"{{\"mute\": {IsMuted.ToString().ToLower()}, \"volume\": {Volume.ToString(System.Globalization.CultureInfo.InvariantCulture)}}}";
            File.WriteAllText(statePath, json);
        }
        catch { }
    }

    private CancellationTokenSource? _assistantTypingCts;
    private CancellationTokenSource? _userTypingCts;

    private async Task TypeAssistantTextAsync(string text)
    {
        _assistantTypingCts?.Cancel();
        _assistantTypingCts = new CancellationTokenSource();
        var token = _assistantTypingCts.Token;

        var current = "";
        foreach (var c in text)
        {
            if (token.IsCancellationRequested) return;
            current += c;
            Dispatcher.UIThread.Post(() => AssistantText = current);
            try { await Task.Delay(25, token).ConfigureAwait(false); } catch { return; }
        }

        if (!token.IsCancellationRequested)
        {
            SetState();
            Dispatcher.UIThread.Post(() => StatusText = "Idle");
        }
    }

    private async Task TypeUserTextAsync(string text)
    {
        _userTypingCts?.Cancel();
        _userTypingCts = new CancellationTokenSource();
        var token = _userTypingCts.Token;

        var current = "";
        foreach (var c in text)
        {
            if (token.IsCancellationRequested) return;
            current += c;
            Dispatcher.UIThread.Post(() => UserText = current);
            try { await Task.Delay(20, token).ConfigureAwait(false); } catch { return; }
        }
    }

    private void StartAgent()
    {
        Task.Run(() =>
        {
            try
            {
                var workingDir = Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, ".."));
                var pythonPath = Path.Combine(workingDir, ".venv", "Scripts", "python.exe");
                var scriptPath = Path.Combine(workingDir, "main.py");

                // Start the python backend without popping up a terminal
                var processStartInfo = new ProcessStartInfo
                {
                    FileName = pythonPath,
                    Arguments = $"\"{scriptPath}\"",
                    WorkingDirectory = workingDir,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                
                // CRITICAL: Force python to not buffer output so the UI receives it instantly
                processStartInfo.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";

                using var process = Process.Start(processStartInfo);
                if (process == null) return;

                while (!process.StandardOutput.EndOfStream)
                {
                    var line = process.StandardOutput.ReadLine();
                    if (string.IsNullOrEmpty(line)) continue;

                    if (line.StartsWith("UI_WAKE_WORD_CHANGED:"))
                    {
                        var newWord = line.Substring(21).Trim();
                        Dispatcher.UIThread.Post(() => WakeWord = newWord);
                    }
                    else if (line.StartsWith("Assistant:"))
                    {
                        var text = line.Substring(10).Trim();
                        _ = TypeAssistantTextAsync(text);
                        Dispatcher.UIThread.Post(() => StatusText = "Talking...");
                        SetState(talking: true);
                    }
                    else if (line.StartsWith("You said:"))
                    {
                        var text = line.Substring(9).Trim().Trim('\'');
                        _ = TypeUserTextAsync(text);
                    }
                    else
                    {
                        Dispatcher.UIThread.Post(() =>
                        {
                            if (line.Contains("Speech detected!"))
                            {
                                StatusText = "Listening...";
                                SetState(listening: true);
                            }
                            else if (line.Contains("Thinking..."))
                            {
                                StatusText = "Thinking...";
                                SetState(thinking: true);
                            }
                            else if (line.Contains("Waiting for wake word"))
                            {
                                StatusText = "Waiting for wake word...";
                                SetState();
                            }
                            else if (line.Contains("Wake word"))
                            {
                                StatusText = "Waking up...";
                                SetState();
                            }
                            else if (line.Contains("System Online!"))
                            {
                                _ = TypeAssistantTextAsync($"I am ready. Say '{WakeWord}' to wake me up.");
                                StatusText = "Online";
                                SetState();
                            }
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                Dispatcher.UIThread.Post(() =>
                {
                    AssistantText = $"Error: {ex.Message}";
                });
            }
        });
    }
}
