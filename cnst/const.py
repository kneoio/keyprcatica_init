# cnst/const.py

# Language constants for translations
LANGUAGES = {
    "ENG": "English",
    "POR": "Portuguese",
    "KAZ": "Kazakh"
}

# Utility function to generate loc_name using language codes
def generate_loc_name(eng_value, por_value, kaz_value):
    return {
        "ENG": eng_value,
        "POR": por_value,
        "KAZ": kaz_value
    }

