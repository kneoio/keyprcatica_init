# cnst/const.py

LANGUAGES = {
    "eng": "English",
    "por": "Portuguese",
    "kaz": "Kazakh"
}

def generate_loc_name(eng_value, por_value, kaz_value):
    return {
        "eng": eng_value,
        "por": por_value,
        "kaz": kaz_value
    }

