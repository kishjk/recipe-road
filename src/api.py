from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import logging
import websockets
import queue

from .agents.search import search_recipes, RecipeSearchQuery, RecipeSearchResult
from .agents.creator import create_detailed_recipe, DetailedRecipe
from .agents.assistant import RecipeAssistant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Recipe Road API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecipeSearchRequest(BaseModel):
    description: str
    ingredients: List[str]
    dietary_restrictions: Optional[List[str]] = None


class RecipeSelectionRequest(BaseModel):
    recipe_index: int
    search_results: RecipeSearchResult
    full_recipe_text: str


class RecipeSession:
    def __init__(self):
        self.search_results: Optional[RecipeSearchResult] = None
        self.selected_recipe: Optional[DetailedRecipe] = None
        self.assistant: Optional[RecipeAssistant] = None


sessions: Dict[str, RecipeSession] = {}


@app.get("/")
async def root():
    return {"message": "Recipe Road API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "api": "Recipe Road"}


@app.post("/search", response_model=RecipeSearchResult)
async def search_recipes_endpoint(request: RecipeSearchRequest):
    """Search for recipes based on user description and ingredients."""
    try:
        query = RecipeSearchQuery(
            description=request.description,
            ingredients=request.ingredients,
            dietary_restrictions=request.dietary_restrictions or []
        )
        
        results = await search_recipes(query)
        
        # Store results in session (simple implementation)
        session_id = f"session_{len(sessions)}"
        session = RecipeSession()
        session.search_results = results
        sessions[session_id] = session
        
        # Update results with session_id
        results.session_id = session_id
        return results
        
    except Exception as e:
        logger.error(f"Error searching recipes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/select/{session_id}", response_model=DetailedRecipe)
async def select_recipe_endpoint(session_id: str, request: RecipeSelectionRequest):
    """Select a recipe and get detailed instructions."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = sessions[session_id]
    
    if request.recipe_index >= len(request.search_results.recipes):
        raise HTTPException(status_code=400, detail="Invalid recipe index")
        
    try:
        selected_recipe = request.search_results.recipes[request.recipe_index]
        detailed_recipe = await create_detailed_recipe(selected_recipe, request.full_recipe_text)
        
        session.selected_recipe = detailed_recipe
        
        return detailed_recipe
        
    except Exception as e:
        logger.error(f"Error creating detailed recipe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/assistant/{session_id}")
async def recipe_assistant_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time recipe assistant."""
    await websocket.accept()
    
    if session_id not in sessions or not sessions[session_id].selected_recipe:
        await websocket.send_json({"error": "No recipe selected"})
        await websocket.close()
        return
        
    session = sessions[session_id]
    assistant = RecipeAssistant()
    session.assistant = assistant
    
    try:
        # Connect to OpenAI
        logger.info(f"Connecting to OpenAI for session {session_id}")
        print(f"Connecting to OpenAI for session {session_id}")
        await assistant.connect()
        
        # Verify connection
        if not assistant.ws:
            raise Exception("Failed to establish WebSocket connection with OpenAI")
        
        # Initialize with recipe
        recipe_data = session.selected_recipe.model_dump()
        logger.info(f"Initializing assistant with recipe: {recipe_data['title']}")
        await assistant.initialize_session(recipe_data)
        
        # Small delay to ensure initialization is complete
        await asyncio.sleep(0.5)
        
        # Start conversation
        logger.info("Starting conversation")
        await assistant.start_conversation(websocket)
        
        # Handle bidirectional communication
        async def receive_from_openai():
            try:
                logger.info("Starting to receive from OpenAI")
                while True:
                    try:
                        # Get message from queue with timeout
                        try:
                            result = assistant.message_queue.get_nowait()
                        except queue.Empty:
                            await asyncio.sleep(0.1)
                            continue
                            
                        if result.get("type") == "audio":
                            # Send audio data to client
                            await websocket.send_bytes(result["data"])
                            
                        elif result.get("type") in ["step_completed", "timer_requested"]:
                            # Send control messages to client
                            await websocket.send_json(result)
                            
                        elif result.get("type") in ["session_created", "session_updated", "event"]:
                            # Log informational messages
                            logger.info(f"Received: {result.get('type')}")
                            
                        elif result.get("type") == "error":
                            logger.error(f"Error from assistant: {result.get('message')}")
                            
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error processing OpenAI message: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error receiving from OpenAI: {e}")
                raise
                    
        async def receive_from_client():
            try:
                logger.info("Starting to receive from client")
                async for data in websocket.iter_bytes():
                    # Forward audio from client to OpenAI
                    logger.debug(f"Received audio from client: {len(data)} bytes")
                    await assistant.send_audio(data)
            except Exception as e:
                logger.error(f"Error receiving from client: {e}")
                raise
                
        # Run both tasks concurrently
        await asyncio.gather(
            receive_from_openai(),
            receive_from_client()
        )
        
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in assistant WebSocket: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass  # WebSocket might already be closed
        
    finally:
        if assistant and assistant.ws:
            await assistant.close()
        await websocket.close()


@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    """End a recipe session."""
    if session_id in sessions:
        session = sessions[session_id]
        if session.assistant and session.assistant.ws:
            await session.assistant.close()
        del sessions[session_id]
        return {"message": "Session ended"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)