#!/usr/bin/env python3
"""
Recipe Road CLI - Interactive command-line interface for recipe search and voice assistance
"""

import asyncio
import aiohttp
import websockets
import websockets.exceptions
import sys
import os
from typing import Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import json
import pyaudio
import queue

console = Console()

# Audio configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000

class RecipeRoadCLI:
    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.session_id: Optional[str] = None
        self.search_results: Optional[Dict[str, Any]] = None
        self.selected_recipe: Optional[Dict[str, Any]] = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        
    async def search_recipes(self):
        """Interactive recipe search"""
        console.print("\n[bold cyan]🔍 Recipe Search[/bold cyan]\n")
        
        # Get user input
        description = Prompt.ask("What would you like to cook?", default="pasta dinner")
        
        ingredients_input = Prompt.ask(
            "What ingredients do you have? (comma-separated)",
            default="pasta, tomatoes, garlic, olive oil"
        )
        ingredients = [i.strip() for i in ingredients_input.split(",")]
        
        dietary = Prompt.ask(
            "Any dietary restrictions? (comma-separated, or press Enter for none)",
            default=""
        )
        dietary_restrictions = [d.strip() for d in dietary.split(",")] if dietary else []
        
        # Search with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Searching for recipes...", total=None)
            
            async with aiohttp.ClientSession() as session:
                data = {
                    "description": description,
                    "ingredients": ingredients,
                    "dietary_restrictions": dietary_restrictions
                }
                
                try:
                    async with session.post(f"{self.api_url}/search", json=data) as resp:
                        if resp.status == 200:
                            self.search_results = await resp.json()
                            self.session_id = self.search_results.get("session_id")
                        else:
                            console.print(f"[red]Error: {resp.status} - {await resp.text()}[/red]")
                            return False
                except Exception as e:
                    console.print(f"[red]Connection error: {e}[/red]")
                    return False
        
        # Display results
        self._display_search_results()
        return True
        
    def _display_search_results(self):
        """Display search results in a formatted table"""
        if not self.search_results or "recipes" not in self.search_results:
            return
            
        console.print("\n[bold green]✨ Found Recipes:[/bold green]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Recipe", style="cyan")
        table.add_column("Time", style="yellow")
        table.add_column("Difficulty", style="green")
        table.add_column("Match", style="blue")
        
        for i, recipe in enumerate(self.search_results["recipes"], 1):
            total_time = f"{recipe['prep_time']} + {recipe['cook_time']}"
            match_score = f"{recipe['match_score']:.0%}"
            
            table.add_row(
                str(i),
                f"[bold]{recipe['title']}[/bold]\n{recipe['description']}",
                total_time,
                recipe['difficulty'],
                match_score
            )
            
            if recipe.get('missing_ingredients'):
                console.print(f"   [dim]Missing: {', '.join(recipe['missing_ingredients'])}[/dim]")
        
        console.print(table)
        
    async def select_recipe(self):
        """Select a recipe and get detailed instructions"""
        if not self.search_results:
            console.print("[red]No search results available. Please search first.[/red]")
            return False
            
        # Get user selection
        max_recipes = len(self.search_results["recipes"])
        selection = IntPrompt.ask(
            f"\nWhich recipe would you like to select? (1-{max_recipes})",
            choices=[str(i) for i in range(1, max_recipes + 1)]
        )
        
        recipe_index = selection - 1
        selected = self.search_results["recipes"][recipe_index]
        
        console.print(f"\n[bold green]✅ Selected: {selected['title']}[/bold green]")
        
        # Get detailed recipe
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Getting detailed instructions...", total=None)
            
            async with aiohttp.ClientSession() as session:
                data = {
                    "recipe_index": recipe_index,
                    "search_results": self.search_results,
                    "full_recipe_text": "Please create detailed step-by-step instructions."
                }
                
                try:
                    async with session.post(
                        f"{self.api_url}/select/{self.session_id}", 
                        json=data
                    ) as resp:
                        if resp.status == 200:
                            self.selected_recipe = await resp.json()
                        else:
                            console.print(f"[red]Error: {resp.status} - {await resp.text()}[/red]")
                            return False
                except Exception as e:
                    console.print(f"[red]Connection error: {e}[/red]")
                    return False
        
        # Display recipe details
        self._display_recipe_details()
        return True
        
    def _display_recipe_details(self):
        """Display detailed recipe instructions"""
        if not self.selected_recipe:
            return
            
        recipe = self.selected_recipe
        
        console.print("\n" + "="*60 + "\n")
        
        # Recipe header
        panel = Panel(
            f"[bold]{recipe['title']}[/bold]\n\n"
            f"[yellow]⏱️  Total Time:[/yellow] {recipe['total_time']}\n"
            f"[yellow]🍽️  Servings:[/yellow] {recipe['servings']}",
            title="[bold cyan]Recipe Details[/bold cyan]",
            expand=False
        )
        console.print(panel)
        
        # Ingredients
        console.print("\n[bold yellow]📝 Ingredients:[/bold yellow]")
        for ingredient in recipe['ingredients']:
            console.print(f"  • {ingredient}")
            
        # Equipment
        if recipe.get('equipment'):
            console.print("\n[bold yellow]🔧 Equipment:[/bold yellow]")
            for item in recipe['equipment']:
                console.print(f"  • {item}")
        
        # Phases and steps
        console.print("\n[bold yellow]👨‍🍳 Instructions:[/bold yellow]\n")
        
        for phase in recipe['phases']:
            console.print(f"[bold cyan]{phase['phase_name']}[/bold cyan] ({phase['total_time']})")
            console.print(f"[dim]{phase['description']}[/dim]\n")
            
            for step in phase['steps']:
                console.print(f"  {step['step_number']}. {step['instruction']}")
                
                if step.get('estimated_time'):
                    console.print(f"     [dim]Time: {step['estimated_time']}[/dim]")
                    
                if step.get('timer_needed') and step.get('timer_duration'):
                    console.print(f"     [yellow]⏱️  Timer: {step['timer_duration']}s[/yellow]")
                    
                if step.get('tips'):
                    console.print(f"     [green]💡 Tip: {step['tips']}[/green]")
                    
                console.print()
        
    async def start_voice_assistant(self):
        """Start the voice assistant session"""
        if not self.selected_recipe:
            console.print("[red]No recipe selected. Please select a recipe first.[/red]")
            return
            
        console.print("\n[bold cyan]🎙️  Starting Voice Assistant[/bold cyan]")
        console.print("[dim]Connecting to voice assistant...[/dim]\n")
        
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Audio input stream
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        # Audio output stream
        output_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK
        )
        
        try:
            # Connect to WebSocket
            ws_url = f"ws://localhost:8001/assistant/{self.session_id}"
            
            try:
                websocket = await websockets.connect(ws_url)
            except Exception as e:
                console.print(f"[red]Failed to connect to voice assistant: {e}[/red]")
                console.print("[yellow]Make sure the API server is running[/yellow]")
                return
                
            console.print("[green]✅ Connected to voice assistant![/green]")
            console.print("[dim]Speak to interact with the assistant. Press Ctrl+C to exit.[/dim]\n")
            
            # Start recording
            self.is_recording = True
                
            try:
                async def send_audio():
                    """Send microphone audio to server"""
                    while self.is_recording:
                        print("Sending audio")
                        try:
                            data = stream.read(CHUNK, exception_on_overflow=False)
                            print(f"Sending audio data: {len(data)}")
                            await websocket.send(message=data, text=False)
                            await asyncio.sleep(0.01)
                        except websockets.exceptions.ConnectionClosed:
                            # Normal connection close
                            break
                        except Exception as e:
                            if self.is_recording and not isinstance(e, asyncio.CancelledError):
                                console.print(f"[red]Audio send error: {e}[/red]")
                            break
                
                async def receive_messages():
                    """Receive and handle messages from server"""
                    try:
                        async for message in websocket:
                            await websocket.ping()
                            print("Ping sent")
                            if isinstance(message, bytes):
                                # Audio data - play it
                                output_stream.write(message)
                            else:
                                # Control message
                                try:
                                    data = json.loads(message)
                                    await self._handle_control_message(data)
                                except json.JSONDecodeError:
                                    pass
                    except websockets.exceptions.ConnectionClosed:
                        console.print("\n[yellow]Connection closed by server[/yellow]")
                    except Exception as e:
                        console.print(f"\n[red]Receive error: {e}[/red]")
                
                # Run both tasks
                try:
                    await asyncio.gather(
                        send_audio(),
                        receive_messages()
                    )
                except asyncio.CancelledError:
                    # Normal cancellation during shutdown
                    pass
                    
            finally:
                await websocket.close()
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping voice assistant...[/yellow]")
        except Exception as e:
            console.print(f"[red]Voice assistant error: {e}[/red]")
        finally:
            self.is_recording = False
            stream.stop_stream()
            stream.close()
            output_stream.stop_stream()
            output_stream.close()
            p.terminate()
            
    async def _handle_control_message(self, data: Dict[str, Any]):
        """Handle control messages from the assistant"""
        msg_type = data.get("type")
        
        if msg_type == "step_completed":
            step_num = data.get("step_number")
            console.print(f"[green]✅ Step {step_num} completed![/green]")
            
        elif msg_type == "timer_requested":
            duration = data.get("duration")
            label = data.get("label")
            console.print(f"[yellow]⏱️  Timer requested: {label} ({duration}s)[/yellow]")
            
            # Could start an actual timer here
            if Confirm.ask("Start timer?"):
                asyncio.create_task(self._run_timer(duration, label))
                
        elif msg_type == "error":
            console.print(f"[red]Error: {data.get('message', 'Unknown error')}[/red]")
            
    async def _run_timer(self, duration: int, label: str):
        """Run a cooking timer"""
        console.print(f"[green]Timer started: {label}[/green]")
        await asyncio.sleep(duration)
        console.print(f"\n[bold yellow]⏰ TIMER DONE: {label}![/bold yellow]\n")
        
    async def run(self):
        """Main CLI loop"""
        console.print(Panel.fit(
            "[bold cyan]Recipe Road[/bold cyan] 🍳\n"
            "AI-powered voice-guided cooking assistant",
            border_style="cyan"
        ))
        
        while True:
            console.print("\n[bold]Main Menu:[/bold]")
            console.print("1. Search for recipes")
            console.print("2. Select a recipe")
            console.print("3. Start voice assistant")
            console.print("4. Exit")
            
            choice = Prompt.ask("\nWhat would you like to do?", choices=["1", "2", "3", "4"])
            
            if choice == "1":
                await self.search_recipes()
                
            elif choice == "2":
                await self.select_recipe()
                
            elif choice == "3":
                await self.start_voice_assistant()
                
            elif choice == "4":
                console.print("[yellow]Goodbye! Happy cooking! 👋[/yellow]")
                break
                
async def main():
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]Error: OPENAI_API_KEY environment variable not set[/red]")
        console.print("Please set it with: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
        
    cli = RecipeRoadCLI()
    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)