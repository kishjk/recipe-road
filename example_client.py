#!/usr/bin/env python3
"""
Example client for Recipe Road API
"""

import asyncio
import aiohttp


async def search_recipes(description: str, ingredients: list):
    """Search for recipes."""
    async with aiohttp.ClientSession() as session:
        data = {
            "description": description,
            "ingredients": ingredients,
            "dietary_restrictions": []
        }
        
        async with session.post("http://localhost:8000/search", json=data) as resp:
            result = await resp.json()
            return result


async def select_recipe(session_id: str, recipe_index: int, search_results: dict):
    """Select a recipe and get detailed instructions."""
    async with aiohttp.ClientSession() as session:
        data = {
            "recipe_index": recipe_index,
            "search_results": search_results,
            "full_recipe_text": "Please create detailed instructions for this recipe."
        }
        
        async with session.post(f"http://localhost:8000/select/{session_id}", json=data) as resp:
            result = await resp.json()
            return result


async def main():
    print("Recipe Road Example Client")
    print("-" * 50)
    
    # Example search
    description = "pasta dinner"
    ingredients = ["pasta", "tomatoes", "garlic", "olive oil", "basil"]
    
    print(f"Searching for: {description}")
    print(f"Available ingredients: {', '.join(ingredients)}")
    print()
    
    # Search for recipes
    search_results = await search_recipes(description, ingredients)
    session_id = search_results.get("session_id")
    
    print("Found recipes:")
    for i, recipe in enumerate(search_results["recipes"]):
        print(f"\n{i+1}. {recipe['title']}")
        print(f"   {recipe['description']}")
        print(f"   Prep: {recipe['prep_time']} | Cook: {recipe['cook_time']}")
        print(f"   Match score: {recipe['match_score']:.0%}")
        if recipe['missing_ingredients']:
            print(f"   Missing: {', '.join(recipe['missing_ingredients'])}")
    
    # Select first recipe
    print("\n" + "-" * 50)
    print("Selecting recipe #1...")
    
    detailed_recipe = await select_recipe(session_id, 0, search_results)
    
    print(f"\nDetailed Recipe: {detailed_recipe['title']}")
    print(f"Total time: {detailed_recipe['total_time']}")
    print(f"Servings: {detailed_recipe['servings']}")
    
    print("\nPhases:")
    for phase in detailed_recipe['phases']:
        print(f"\n{phase['phase_name']} ({phase['total_time']})")
        print(f"{phase['description']}")
        for step in phase['steps']:
            print(f"  {step['step_number']}. {step['instruction']}")
            if step['timer_needed']:
                print(f"     ⏱️  Timer: {step['timer_duration']}s")
            if step['tips']:
                print(f"     💡 Tip: {step['tips']}")
    
    print("\n" + "-" * 50)
    print("To start the voice assistant, connect a WebSocket client to:")
    print(f"ws://localhost:8000/assistant/{session_id}")


if __name__ == "__main__":
    asyncio.run(main())