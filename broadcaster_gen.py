from database.kneo.ai_agent_generator import populate_ai_agents
from database.kneo.brand_generator import generate_brands
from database.kneo.genres_generator import generate_genres
from database.kneo.listener_generator import generate_listeners
from database.kneo.memory_generator import populate_brand_memories
from database.kneo.music_label_generator import generate_labels
from database.kneo.soundfragment_generator import generate_sound_fragments
from database.kneo.profile_generator import generate_profiles

if __name__ == "__main__":
    generate_labels()
    populate_ai_agents()
    generate_brands()
    generate_listeners()
    generate_profiles()
    populate_brand_memories()
    generate_genres()
    generate_sound_fragments()
