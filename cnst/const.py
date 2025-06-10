# cnst/const.py

LANGUAGES = {
    "en": "English",
    "pt": "Portuguese",
    "kk": "Kazakh"
}

def generate_loc_name(eng_value, por_value, kaz_value):
    return {
        "en": eng_value,
        "pt": por_value,
        "kk": kaz_value
    }

VALID_COUNTRY_CODES = [
    'KZ', 'LV', 'PT', 'GE'
]