from database.kneo.brand_generator import generate_brands
from database.kneo.listener_generator import generate_listeners
from database.kneo.music_label_generator import generate_labels
from database.kneo.soundfragment_generator import generate_sound_fragments
from database.kneo.profile_generator import generate_profiles

if __name__ == "__main__":
    generate_labels()
    generate_brands()
    generate_listeners()
    generate_sound_fragments()
    generate_profiles()