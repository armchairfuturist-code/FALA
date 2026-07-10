#!/usr/bin/env python3
"""fala — European Portuguese language tutor CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from conversation import ConversationEngine

console = Console()

try:
    from audio import get_tts_provider_info, listen, speak

    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


def main():
    try:
        engine = ConversationEngine()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return
    voice_mode = False

    console.print()
    subtitle = "A1→B1 | Type 'quit' to exit"
    if AUDIO_AVAILABLE:
        subtitle += " | /voice to toggle voice input"
    console.print(
        Panel.fit(
            "[bold cyan]fala[/bold cyan] — European Portuguese Tutor",
            subtitle=subtitle,
        )
    )
    console.print()

    status = engine.get_status_report()
    console.print(f"[dim]{status}[/dim]")
    console.print()

    if AUDIO_AVAILABLE:
        tts_info = get_tts_provider_info()
        console.print(f"[dim]{tts_info} | /voice to toggle voice input[/dim]")
    else:
        console.print("[dim]Audio: install openai package for TTS support[/dim]")
    console.print()

    console.print("[bold]Starting warm-up...[/bold]")
    console.print()
    warmup = engine.start_warmup()
    print_tutor(warmup, speak_audio=True)

    while True:
        try:
            if voice_mode and AUDIO_AVAILABLE:
                console.print("[dim]Listening... (speak now, or press Enter to type)[/dim]")
                voice_text = listen()
                if voice_text:
                    console.print(f"[dim]heard: {voice_text}[/dim]")
                    user_input = voice_text
                else:
                    prompt = "[bold green]you[/bold green] "
                    prompt += "[dim](voice failed, type instead)[/dim]"
                    user_input = Prompt.ask(prompt)
            else:
                user_input = Prompt.ask("[bold green]you[/bold green]")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        stripped = user_input.strip()

        if stripped.lower() in ("quit", "exit", "sair"):
            break

        if stripped == "/voice":
            voice_mode = not voice_mode
            mode = "ON" if voice_mode else "OFF"
            console.print(f"[dim]Voice input: {mode}[/dim]")
            continue

        if stripped == "/stats":
            stats = engine.get_stats()
            console.print(Panel(stats, title="[bold]Stats[/bold]", border_style="green"))
            continue

        if not stripped:
            continue

        is_voice = voice_mode and AUDIO_AVAILABLE
        response = engine.user_message(stripped, is_voice=is_voice)
        print_tutor(response, speak_audio=True)

    console.print()
    result = engine.end_session()
    console.print(f"[dim]{result}[/dim]")
    console.print("[dim]Adeus![/dim]")


def print_tutor(text: str, speak_audio: bool = False):
    console.print()
    console.print(Panel(text, title="[bold blue]tutor[/bold blue]", border_style="blue"))
    if speak_audio and AUDIO_AVAILABLE:
        ok = speak(text)
        if not ok:
            console.print(
                "[dim](audio playback failed — is mpv, ffplay, or aplay installed?)[/dim]"
            )
    console.print()


if __name__ == "__main__":
    main()
