import os
import json
import asyncio
import websockets
import websocket
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from dotenv import load_dotenv
import threading
import time
import queue
import base64
load_dotenv()

logger = logging.getLogger(__name__)


class AssistantState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"


@dataclass
class RecipeContext:
    recipe_title: str
    current_phase: int
    current_step: int
    completed_steps: set
    active_timers: Dict[str, float]


class RecipeAssistant:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        self.ws = None
        self.state = AssistantState.IDLE
        self.recipe_context: Optional[RecipeContext] = None
        self.session_id: Optional[str] = None
        self.client_websocket = None
        self.message_queue = queue.Queue()
        
    async def connect(self):
        """Connect to OpenAI Realtime API."""
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        try:
            def on_open(ws):
                print("Connected to server.")

            def on_message(ws, message):
                try:
                    result = self.handle_message(message)
                    # Store the result to be processed by the main loop
                    if hasattr(self, 'message_queue'):
                        self.message_queue.put(result)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

            def on_error(ws, error):
                print(error)
                
            def on_close(ws, close_status_code, close_msg):
                print("Closed connection.")

            self.ws = websocket.WebSocketApp(self.url, header=headers, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()

            conn_timeout = 5
            while not self.ws.sock.connected and conn_timeout:
                time.sleep(1)
                conn_timeout -= 1

            logger.info("Connected to OpenAI Realtime API")
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            raise
        
    async def initialize_session(self, recipe_data: Dict[str, Any]):
        """Initialize the assistant session with recipe context."""
        self.recipe_context = RecipeContext(
            recipe_title=recipe_data['title'],
            current_phase=0,
            current_step=0,
            completed_steps=set(),
            active_timers={}
        )
        
        # Store full recipe data for reference
        self.recipe_data = recipe_data
        
        # Configure session
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": f"""You are a cooking assistant helping the user prepare: {recipe_data['title']}.
                
                Guide them through each step clearly and patiently.
                - Speak naturally and conversationally
                - Ask if they're ready before moving to the next step
                - Offer to set timers when needed
                - Answer any questions about the recipe
                - Be encouraging and helpful
                
                Current recipe has {len(recipe_data.get('phases', []))} phases.
                
                Recipe overview:
                {json.dumps(recipe_data, indent=2)}
                """,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "temperature": 0.8,
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad"
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "mark_step_complete",
                        "description": "Mark a step as completed",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "step_number": {"type": "integer"}
                            },
                            "required": ["step_number"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "set_timer",
                        "description": "Set a cooking timer",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "duration_seconds": {"type": "integer"},
                                "label": {"type": "string"}
                            },
                            "required": ["duration_seconds", "label"]
                        }
                    }
                ]
            }
        }
        
        self.send_event(session_config)
        
        # Wait for session to be ready
        logger.info("Waiting for session to be ready...")
        await asyncio.sleep(1.0)
        
    def send_event(self, event: Dict[str, Any]):
        """Send an event to the WebSocket."""
        if self.ws:
            try:
                self.ws.send(json.dumps(event))
                logger.debug(f"Sent event: {event['type']}")
            except Exception as e:
                logger.error(f"Error sending event: {e}")
                raise
            
    async def send_audio(self, audio_data: bytes):
        """Send audio data to the assistant."""
        print(f"Sending audio data: {len(audio_data)}")
        event = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(audio_data).decode('utf-8')
        }
        self.send_event(event)
        
    def handle_message(self, message: str) -> Dict[str, Any]:
        """Handle incoming WebSocket messages."""
        data = json.loads(message)
        event_type = data.get("type")
        
        if event_type == "error":
            logger.error(f"Error from API: {data}")
            
        elif event_type == "session.created":
            self.session_id = data["session"]["id"]
            logger.info(f"Session created: {self.session_id}")
            return {"type": "session_created", "session_id": self.session_id}
            
        elif event_type == "session.updated":
            logger.info("Session updated successfully")
            return {"type": "session_updated"}
            
        elif event_type == "conversation.item.created":
            if data.get("item", {}).get("role") == "assistant":
                self.state = AssistantState.SPEAKING
                
        elif event_type == "response.audio.delta":
            # Return audio delta for streaming
            try:
                audio_data = data.get("delta")
                if audio_data:
                    return {
                        "type": "audio",
                        "data": base64.b64decode(audio_data)
                    }
            except ValueError as e:
                logger.error(f"Invalid audio data format: {e}")
                return {"type": "error", "message": "Invalid audio data"}
            
        elif event_type == "response.done":
            self.state = AssistantState.LISTENING
            
        elif event_type == "response.function_call_arguments.done":
            # Handle function calls
            function_name = data.get("name")
            if not function_name:
                return {"type": "event", "data": data}
            arguments = json.loads(data.get("arguments", "{}"))
            
            if function_name == "mark_step_complete":
                step_num = arguments["step_number"]
                self.recipe_context.completed_steps.add(step_num)
                return {
                    "type": "step_completed",
                    "step_number": step_num
                }
                
            elif function_name == "set_timer":
                return {
                    "type": "timer_requested",
                    "duration": arguments["duration_seconds"],
                    "label": arguments["label"]
                }
                
        return {"type": "event", "data": data}
        
    async def start_conversation(self, client_websocket):
        """Start the conversation flow."""
        try:
            self.client_websocket = client_websocket
            
            # Create initial user message
            event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Hello! I'm ready to start cooking. Please guide me through the first step."
                        }
                    ]
                }
            }
            self.send_event(event)
            
            # Small delay to ensure message is processed
            await asyncio.sleep(0.1)
            
            # Trigger response
            self.send_event({"type": "response.create"})
            
        except Exception as e:
            logger.error(f"Error starting conversation: {e}")
            raise
        
    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            self.ws.close()
            logger.info("Disconnected from OpenAI Realtime API")
