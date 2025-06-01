from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv
import os
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class RecipeSearchQuery(BaseModel):
    description: str = Field(description="What the user wants to cook")
    ingredients: List[str] = Field(description="Available ingredients")
    dietary_restrictions: List[str] = Field(default_factory=list, description="Dietary restrictions or preferences")


class RecipeOption(BaseModel):
    title: str
    description: str
    prep_time: str
    cook_time: str
    servings: int
    difficulty: str
    ingredients: List[str]
    missing_ingredients: List[str]
    match_score: float = Field(description="How well this matches user's request (0-1)")


class RecipeSearchResult(BaseModel):
    recipes: List[RecipeOption]
    session_id: str


search_agent = Agent(
    'openai:gpt-4o',
    api_key=OPENAI_API_KEY,
    output_type=RecipeSearchResult,
    system_prompt="""You are a helpful recipe search assistant. Search for recipes based on user's description and available ingredients.
    
    For each recipe, provide:
    - A clear title and description
    - Realistic prep and cook times
    - Number of servings
    - Difficulty level (Easy, Medium, Hard)
    - Complete ingredient list
    - List of ingredients the user doesn't have
    - A match score (0-1) based on how well it fits their request
    
    Always return exactly 3 recipe options, ordered by match score (highest first).
    Consider dietary restrictions and preferences.
    """
)


async def search_recipes(query: RecipeSearchQuery) -> RecipeSearchResult:
    """Search for recipes based on user query and available ingredients."""
    prompt = f"""Find recipes for: {query.description}
    
    Available ingredients: {', '.join(query.ingredients)}
    Dietary restrictions: {', '.join(query.dietary_restrictions) if query.dietary_restrictions else 'None'}
    
    Search the internet for recipes that match these criteria and return 3 options.
    """
    
    result = await search_agent.run(prompt)
    return result.output