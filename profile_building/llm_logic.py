from openai_client import OpenAIClient
from datetime import datetime, timedelta

today = datetime.now()

def get_user_inputs(uid: str):
    return [
        {
            "date": today - timedelta(days=1),
            "current_feeling": 8,  # 1-10 scale
            "activity_done": ["running", "meditation", "reading"],
            "sleep": 7.5,
            "major_events": ["job interview"],
            "additional_info": "Had a great interview today, feeling optimistic!"
        },
        # Two days ago (average day)
        {
            "date": today - timedelta(days=2),
            "current_feeling": 5,
            "activity_done": ["walking", "cooking"],
            "sleep": 6,
            "major_events": [],
            "additional_info": "Regular day, nothing special happened."
        },
        # Three days ago (bad day)
        {
            "date": today - timedelta(days=3),
            "current_feeling": 3,
            "activity_done": ["watching TV"],
            "sleep": 4.5,
            "major_events": ["missed deadline"],
            "additional_info": "Couldn't sleep well, feeling anxious about work."
        },
        # Four days ago (weekend)
        {
            "date": today - timedelta(days=4),
            "current_feeling": 9,
            "activity_done": ["hiking", "barbecue", "movie night"],
            "sleep": 9,
            "major_events": ["family gathering"],
            "additional_info": "Great day with family, lots of fun activities!"
        },
        # Five days ago (sick day)
        {
            "date": today - timedelta(days=5),
            "current_feeling": 2,
            "activity_done": ["resting"],
            "sleep": 12,
            "major_events": ["sick day"],
            "additional_info": "Caught a cold, spent the whole day in bed."
        }
    ]

def generate_wellness_scores(uid: str, llm_client: OpenAIClient) -> dict:
    """
    Generate wellness scores based on user inputs using an LLM.
    
    Args:
        uid: User ID to fetch inputs for
        llm_client: Initialized OpenAIClient instance
        
    Returns:
        dict: Dictionary containing wellness scores
    """
    user_inputs = get_user_inputs(uid)
    
    system_prompt = """You are a wellness analysis assistant. Analyze the user's daily inputs and provide 
    scores on different wellness dimensions. The scores should be on a scale of 0-10, where 0 is the 
    lowest and 10 is the highest. Consider the following in your analysis:
    - Energy: Overall energy level and vitality
    - Stress: Current stress level (lower is better)
    - Social Battery: Desire and capacity for social interaction
    - Recovery Need: Need for rest and recovery
    - Novelty Appetite: Desire for new experiences and variety
    
    Return ONLY a JSON object with the scores, no other text or explanation.
    """
    
    user_prompt = f"""Please analyze the following user inputs and provide wellness scores.
    
    User's recent inputs:
    {user_inputs}
    
    Return the scores in this exact JSON format:
    {{
        "energy": 0-10,
        "stress": 0-10,
        "social_battery": 0-10,
        "recovery_need": 0-10,
        "novelty_appetite": 0-10
    }}
    """
    
    try:
        # Get the response from the LLM
        response = llm_client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent scoring
            max_tokens=200
        )
        
        # Parse the JSON response
        import json
        scores = json.loads(response.strip())
        
        # Validate the scores
        for key in ["energy", "stress", "social_battery", "recovery_need", "novelty_appetite"]:
            if key not in scores:
                raise ValueError(f"Missing score for {key}")
            if not (0 <= scores[key] <= 10):
                raise ValueError(f"Score for {key} must be between 0 and 10")
        
        return scores
        
    except Exception as e:
        print(f"Error generating wellness scores: {str(e)}")
        # Return neutral scores in case of error
        return {
            "energy": 5,
            "stress": 5,
            "social_battery": 5,
            "recovery_need": 5,
            "novelty_appetite": 5
        }