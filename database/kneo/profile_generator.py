import json
from datetime import datetime
import random
from util.logging import logger
from database import get_connection
from util.permissions import add_superuser_permissions

# Environment profiles data
environments = {
    "care_center": {
        "description": "Focus on nostalgia, gentle volume, cognitive stimulation.",
        "allowed_genres": ["oldies", "classical", "jazz", "folk"],
        "announcement_frequency": "low",
        "volume_level": "low",
        "explicit_content": False,
        "language": "POR"
    },
    "hospital": {
        "description": "Calming selections, limited announcement volume, wellness themes.",
        "allowed_genres": ["ambient", "classical", "light jazz", "new age"],
        "announcement_frequency": "very_low",
        "volume_level": "very_low",
        "explicit_content": False
    },
    "school": {
        "description": "Age-appropriate content, educational ties, energy management.",
        "allowed_genres": ["pop", "educational", "children", "instrumental"],
        "announcement_frequency": "medium",
        "volume_level": "medium",
        "explicit_content": False
    },
    "car_workshop": {
        "description": "Upbeat tempo, industry-appropriate language, ambient volume.",
        "allowed_genres": ["rock", "classic rock", "country", "pop"],
        "announcement_frequency": "medium",
        "volume_level": "medium_high",
        "explicit_content": False
    },
    "mall": {
        "description": "Family-friendly content, shopping-compatible tempo, promotional integration.",
        "allowed_genres": ["pop", "easy listening", "soft rock", "ambient"],
        "announcement_frequency": "high",
        "volume_level": "medium",
        "explicit_content": False
    },
    "office": {
        "description": "Work-appropriate selections, productivity focus, time-aware programming.",
        "allowed_genres": ["ambient", "instrumental", "jazz", "classical", "lo-fi"],
        "announcement_frequency": "low",
        "volume_level": "low",
        "explicit_content": False
    },
    "family_event": {
        "description": "Occasion-specific content, all-ages appropriate, celebration themes.",
        "allowed_genres": ["pop", "dance", "party", "classics", "contemporary"],
        "announcement_frequency": "medium_high",
        "volume_level": "high",
        "explicit_content": False
    },
    "student_dorms": {
        "description": "Contemporary selections, social connection themes, study-time awareness.",
        "allowed_genres": ["pop", "electronic", "hip-hop", "rock", "indie"],
        "announcement_frequency": "medium",
        "volume_level": "medium_high",
        "explicit_content": False
    }
}


def generate_profiles():
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()

    profile_ids = {}

    # Create profiles
    for name, profile_data in environments.items():
        try:
            language = profile_data.get("language", None)
            cursor.execute("""
                INSERT INTO kneobroadcaster__profiles 
                (author, reg_date, last_mod_user, last_mod_date, name, description, 
                allowed_genres, announcement_frequency, volume_level, explicit_content, language)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                0, now, 0, now,
                name,
                profile_data["description"],
                json.dumps(profile_data["allowed_genres"]),
                profile_data["announcement_frequency"],
                profile_data["volume_level"],
                profile_data["explicit_content"],
                language
            ))
            profile_id = cursor.fetchone()[0]
            profile_ids[name] = profile_id

            # Add superuser permissions
            add_superuser_permissions(cursor, profile_id, "kneobroadcaster__profile_readers")

            logger.info(f"Profile created: {name}")
        except Exception as e:
            logger.error(f"Error creating profile {name}: {e}")

    # Assign profiles to brands randomly
    try:
        cursor.execute("SELECT id FROM kneobroadcaster__brands")
        brands = cursor.fetchall()

        for brand in brands:
            brand_id = brand[0]
            # Choose a random profile
            random_profile_name = random.choice(list(profile_ids.keys()))
            profile_id = profile_ids[random_profile_name]

            cursor.execute("""
                UPDATE kneobroadcaster__brands
                SET profile_id = %s
                WHERE id = %s
            """, (profile_id, brand_id))

            logger.info(f"Brand {brand_id} assigned profile: {random_profile_name}")
    except Exception as e:
        logger.error(f"Error assigning profiles to brands: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished generating profiles and assigning to brands.")


if __name__ == "__main__":
    generate_profiles()