from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from .search import RecipeOption
from dotenv import load_dotenv
import os
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class RecipeStep(BaseModel):
    step_number: int
    instruction: str
    estimated_time: Optional[str] = None
    timer_needed: bool = False
    timer_duration: Optional[int] = Field(None, description="Timer duration in seconds")
    tips: Optional[str] = None


class RecipePhase(BaseModel):
    phase_name: str
    description: str
    steps: List[RecipeStep]
    total_time: str


class DetailedRecipe(BaseModel):
    title: str
    description: str
    servings: int
    total_time: str
    ingredients: List[str]
    equipment: List[str]
    phases: List[RecipePhase]


creator_agent = Agent(
    'openai:gpt-4o',
    api_key=OPENAI_API_KEY,
    output_type=DetailedRecipe,
    system_prompt="""You are a professional recipe formatter. Convert recipe information into detailed, step-by-step instructions.
    
    Break down recipes into logical phases (e.g., Preparation, Cooking, Finishing).
    For each step:
    - Provide clear, concise instructions
    - Estimate time needed
    - Identify if a timer would be helpful
    - Add helpful tips where appropriate
    
    Make instructions suitable for voice guidance.
    """
)


async def create_detailed_recipe(recipe: RecipeOption, full_recipe_text: str) -> DetailedRecipe:
    """Convert a recipe option into detailed step-by-step instructions."""
    prompt = f"""Convert this recipe into detailed instructions:
    
    Title: {recipe.title}
    Description: {recipe.description}
    Servings: {recipe.servings}
    Ingredients: {', '.join(recipe.ingredients)}
    
    Full recipe details:
    {full_recipe_text}
    
    Break this down into clear phases and steps suitable for voice-guided cooking.
    """
    
    result = await creator_agent.run(prompt)
    return result.output