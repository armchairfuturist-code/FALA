#!/usr/bin/env python3
"""fala — European Portuguese language tutor CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from conversation import ConversationEngine

console = Console()

try:
    from audio import extract_speech_text, get_tts_provider_info, listen, speak

    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

    # ponytail: fallback duplicate of audio.extract_speech_text so the CLI can
    # still strip the ---SAY--- marker when the openai/audio deps are missing;
    # keep in sync with audio.py (upgrade path: extract to a dep-free module).
    def extract_speech_text(response: str) -> tuple[str, str | None]:  # type: ignore[misc]
        marker = "---SAY---"
        if marker in response:
            display, _, speech = response.partition(marker)
            return display.strip(), speech.strip()
        return response, None


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

        if stripped == "/review":
            drill = engine.get_review_drill()
            if not drill:
                console.print("[dim]Nothing due for review. Continue chatting![/dim]")
                continue
            right = 0
            for item in drill:
                ans = Prompt.ask(f"[bold blue]Diz em português[/bold blue] ({item['english']})")
                if engine.submit_review_answer(item["word"], ans):
                    right += 1
                    console.print("[green]Boa![/green]")
                else:
                    console.print(f"[yellow]Quase — {item['word']}[/yellow]")
            console.print(f"[dim]Review: {right}/{len(drill)} right.[/dim]")
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
    # ---SAY--- contract: the panel shows the display text only, and speech
    # synthesizes just the speech part (speak() re-applies the same contract
    # defensively, so both paths stay correct if either is changed alone).
    display, speech = extract_speech_text(text)
    console.print()
    console.print(Panel(display, title="[bold blue]tutor[/bold blue]", border_style="blue"))
    if speak_audio and AUDIO_AVAILABLE:
        ok = speak(speech if speech is not None else display)
        if not ok:
            console.print(
                "[dim](audio playback failed — is mpv, ffplay, or aplay installed?)[/dim]"
            )
    console.print()


if __name__ == "__main__":
    main()
