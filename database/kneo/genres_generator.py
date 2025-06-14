import json
from datetime import datetime
from database import get_connection
from util.logging import logger

genre_options_data = [
    {
        "label": "Alternative Rock", "value": "Alternative Rock",
        "translations": {
            "en": "Alternative Rock",
            "pt": "Rock Alternativo",
            "kk": "Альтернативті рок",
            "ru": "Альтернативный рок"
        }
    },
    {
        "label": "Ambient", "value": "Ambient",
        "translations": {
            "en": "Ambient",
            "pt": "Música Ambiente",
            "kk": "Эмбиент",
            "ru": "Эмбиент"
        }
    },
    {
        "label": "Blues", "value": "Blues",
        "translations": {
            "en": "Blues",
            "pt": "Blues",
            "kk": "Блюз",
            "ru": "Блюз"
        }
    },
    {
        "label": "Chillout", "value": "Chillout",
        "translations": {
            "en": "Chillout",
            "pt": "Chillout",
            "kk": "Чиллаут",
            "ru": "Чиллаут"
        }
    },
    {
        "label": "Classical", "value": "Classical",
        "translations": {
            "en": "Classical",
            "pt": "Música Clássica",
            "kk": "Классикалық музыка",
            "ru": "Классическая музыка"
        }
    },
    {
        "label": "Country", "value": "Country",
        "translations": {
            "en": "Country",
            "pt": "Country",
            "kk": "Кантри",
            "ru": "Кантри"
        }
    },
    {
        "label": "Crowd Rock", "value": "Crowd Rock",
        "translations": {
            "en": "Crowd Rock",
            "pt": "Rock de Estádio",
            "kk": "Стадиондық рок",
            "ru": "Стадионный рок"
        }
    },
    {
        "label": "Dance", "value": "Dance",
        "translations": {
            "en": "Dance",
            "pt": "Dance Music",
            "kk": "Би музыкасы",
            "ru": "Танцевальная музыка"
        }
    },
    {
        "label": "Dark Synth", "value": "Dark Synth",
        "translations": {
            "en": "Dark Synth",
            "pt": "Dark Synth",
            "kk": "Dark Synth",
            "ru": "Дарк-синт"
        }
    },
    {
        "label": "Downtempo", "value": "Downtempo",
        "translations": {
            "en": "Downtempo",
            "pt": "Downtempo",
            "kk": "Даунтемпо",
            "ru": "Даунтемпо"
        }
    },
    {
        "label": "Drum and Bass", "value": "Drum and Bass",
        "translations": {
            "en": "Drum and Bass",
            "pt": "Drum and Bass",
            "kk": "Драм-н-бэйс",
            "ru": "Драм-н-бэйс"
        }
    },
    {
        "label": "Dubstep", "value": "Dubstep",
        "translations": {
            "en": "Dubstep",
            "pt": "Dubstep",
            "kk": "Дабстеп",
            "ru": "Дабстеп"
        }
    },
    {
        "label": "EBM", "value": "EBM",
        "translations": {
            "en": "EBM",
            "pt": "EBM",
            "kk": "EBM",
            "ru": "EBM"
        }
    },
    {
        "label": "Electronic", "value": "Electronic",
        "translations": {
            "en": "Electronic",
            "pt": "Música Eletrónica",
            "kk": "Электрондық музыка",
            "ru": "Электронная музыка"
        }
    },
    {
        "label": "Electropop", "value": "Electropop",
        "translations": {
            "en": "Electropop",
            "pt": "Electropop",
            "kk": "Электропоп",
            "ru": "Электропоп"
        }
    },
    {
        "label": "Experimental", "value": "Experimental",
        "translations": {
            "en": "Experimental",
            "pt": "Música Experimental",
            "kk": "Эксперименттік музыка",
            "ru": "Экспериментальная музыка"
        }
    },
    {
        "label": "Folk", "value": "Folk",
        "translations": {
            "en": "Folk",
            "pt": "Música Folclórica",
            "kk": "Фолк",
            "ru": "Фолк"
        }
    },
    {
        "label": "Funk", "value": "Funk",
        "translations": {
            "en": "Funk",
            "pt": "Funk",
            "kk": "Фанк",
            "ru": "Фанк"
        }
    },
    {
        "label": "Futurepop", "value": "Futurepop",
        "translations": {
            "en": "Futurepop",
            "pt": "Futurepop",
            "kk": "Futurepop",
            "ru": "Futurepop"
        }
    },
    {
        "label": "Garage Rock", "value": "Garage Rock",
        "translations": {
            "en": "Garage Rock",
            "pt": "Garage Rock",
            "kk": "Гараж рок",
            "ru": "Гаражный рок"
        }
    },
    {
        "label": "Gospel", "value": "Gospel",
        "translations": {
            "en": "Gospel",
            "pt": "Gospel",
            "kk": "Госпел",
            "ru": "Госпел"
        }
    },
    {
        "label": "Goth Rock", "value": "Goth Rock",
        "translations": {
            "en": "Goth Rock",
            "pt": "Rock Gótico",
            "kk": "Готикалық рок",
            "ru": "Готик-рок"
        }
    },
    {
        "label": "Grunge", "value": "Grunge",
        "translations": {
            "en": "Grunge",
            "pt": "Grunge",
            "kk": "Гранж",
            "ru": "Гранж"
        }
    },
    {
        "label": "Hard Rock", "value": "Hard Rock",
        "translations": {
            "en": "Hard Rock",
            "pt": "Hard Rock",
            "kk": "Хард-рок",
            "ru": "Хард-рок"
        }
    },
    {
        "label": "Hip Hop", "value": "Hip Hop",
        "translations": {
            "en": "Hip Hop",
            "pt": "Hip Hop",
            "kk": "Хип-хоп",
            "ru": "Хип-хоп"
        }
    },
    {
        "label": "House", "value": "House",
        "translations": {
            "en": "House",
            "pt": "House Music",
            "kk": "Хаус",
            "ru": "Хаус"
        }
    },
    {
        "label": "IDM", "value": "IDM",
        "translations": {
            "en": "IDM",
            "pt": "IDM",
            "kk": "IDM",
            "ru": "IDM"
        }
    },
    {
        "label": "Indie Pop", "value": "Indie Pop",
        "translations": {
            "en": "Indie Pop",
            "pt": "Indie Pop",
            "kk": "Инди-поп",
            "ru": "Инди-поп"
        }
    },
    {
        "label": "Indie Rock", "value": "Indie Rock",
        "translations": {
            "en": "Indie Rock",
            "pt": "Indie Rock",
            "kk": "Инди-рок",
            "ru": "Инди-рок"
        }
    },
    {
        "label": "Industrial", "value": "Industrial",
        "translations": {
            "en": "Industrial",
            "pt": "Industrial",
            "kk": "Индастриал",
            "ru": "Индастриал"
        }
    },
    {
        "label": "Industrial Metal", "value": "Industrial Metal",
        "translations": {
            "en": "Industrial Metal",
            "pt": "Metal Industrial",
            "kk": "Индастриал-метал",
            "ru": "Индастриал-метал"
        }
    },
    {
        "label": "Instrumental", "value": "Instrumental",
        "translations": {
            "en": "Instrumental",
            "pt": "Instrumental",
            "kk": "Инструменталды",
            "ru": "Инструментальная"
        }
    },
    {
        "label": "Jazz", "value": "Jazz",
        "translations": {
            "en": "Jazz",
            "pt": "Jazz",
            "kk": "Джаз",
            "ru": "Джаз"
        }
    },
    {
        "label": "Latin", "value": "Latin",
        "translations": {
            "en": "Latin",
            "pt": "Música Latina",
            "kk": "Латын музыкасы",
            "ru": "Латинская музыка"
        }
    },
    {
        "label": "Lo-fi", "value": "Lo-fi",
        "translations": {
            "en": "Lo-fi",
            "pt": "Lo-fi",
            "kk": "Lo-fi",
            "ru": "Lo-fi"
        }
    },
    {
        "label": "Metal", "value": "Metal",
        "translations": {
            "en": "Metal",
            "pt": "Metal",
            "kk": "Метал",
            "ru": "Метал"
        }
    },
    {
        "label": "Minimal Synth", "value": "Minimal Synth",
        "translations": {
            "en": "Minimal Synth",
            "pt": "Minimal Synth",
            "kk": "Minimal Synth",
            "ru": "Минимал-синт"
        }
    },
    {
        "label": "New Wave", "value": "New Wave",
        "translations": {
            "en": "New Wave",
            "pt": "New Wave",
            "kk": "Нью-вейв",
            "ru": "Нью-вейв"
        }
    },
    {
        "label": "Noise", "value": "Noise",
        "translations": {
            "en": "Noise",
            "pt": "Noise",
            "kk": "Нойз",
            "ru": "Нойз"
        }
    },
    {
        "label": "Other", "value": "Other",
        "translations": {
            "en": "Other",
            "pt": "Outro",
            "kk": "Басқа",
            "ru": "Другое"
        }
    },
    {
        "label": "Pop", "value": "Pop",
        "translations": {
            "en": "Pop",
            "pt": "Pop",
            "kk": "Поп",
            "ru": "Поп"
        }
    },
    {
        "label": "Post-Punk", "value": "Post-Punk",
        "translations": {
            "en": "Post-Punk",
            "pt": "Pós-Punk",
            "kk": "Пост-панк",
            "ru": "Пост-панк"
        }
    },
    {
        "label": "Progressive Rock", "value": "Progressive Rock",
        "translations": {
            "en": "Progressive Rock",
            "pt": "Rock Progressivo",
            "kk": "Прогрессивті рок",
            "ru": "Прогрессивный рок"
        }
    },
    {
        "label": "Psychedelic Rock", "value": "Psychedelic Rock",
        "translations": {
            "en": "Psychedelic Rock",
            "pt": "Rock Psicadélico",
            "kk": "Психоделикалық рок",
            "ru": "Психоделический рок"
        }
    },
    {
        "label": "Punk Rock", "value": "Punk Rock",
        "translations": {
            "en": "Punk Rock",
            "pt": "Punk Rock",
            "kk": "Панк-рок",
            "ru": "Панк-рок"
        }
    },
    {
        "label": "R&B", "value": "R&B",
        "translations": {
            "en": "R&B",
            "pt": "R&B",
            "kk": "R&B",
            "ru": "R&B"
        }
    },
    {
        "label": "Reggae", "value": "Reggae",
        "translations": {
            "en": "Reggae",
            "pt": "Reggae",
            "kk": "Регги",
            "ru": "Регги"
        }
    },
    {
        "label": "Rock", "value": "Rock",
        "translations": {
            "en": "Rock",
            "pt": "Rock",
            "kk": "Рок",
            "ru": "Рок"
        }
    },
    {
        "label": "Shoegaze", "value": "Shoegaze",
        "translations": {
            "en": "Shoegaze",
            "pt": "Shoegaze",
            "kk": "Шугейз",
            "ru": "Шугейз"
        }
    },
    {
        "label": "Ska", "value": "Ska",
        "translations": {
            "en": "Ska",
            "pt": "Ska",
            "kk": "Ска",
            "ru": "Ска"
        }
    },
    {
        "label": "Soul", "value": "Soul",
        "translations": {
            "en": "Soul",
            "pt": "Soul",
            "kk": "Соул",
            "ru": "Соул"
        }
    },
    {
        "label": "Soundtrack", "value": "Soundtrack",
        "translations": {
            "en": "Soundtrack",
            "pt": "Trilha Sonora",
            "kk": "Саундтрек",
            "ru": "Саундтрек"
        }
    },
    {
        "label": "Spoken Word", "value": "Spoken Word",
        "translations": {
            "en": "Spoken Word",
            "pt": "Palavra Falada",
            "kk": "Spoken Word",
            "ru": "Разговорный жанр"
        }
    },
    {
        "label": "Synthwave", "value": "Synthwave",
        "translations": {
            "en": "Synthwave",
            "pt": "Synthwave",
            "kk": "Synthwave",
            "ru": "Синтвейв"
        }
    },
    {
        "label": "Techno", "value": "Techno",
        "translations": {
            "en": "Techno",
            "pt": "Techno",
            "kk": "Техно",
            "ru": "Техно"
        }
    },
    {
        "label": "Trance", "value": "Trance",
        "translations": {
            "en": "Trance",
            "pt": "Trance",
            "kk": "Транс",
            "ru": "Транс"
        }
    },
    {
        "label": "Trip Hop", "value": "Trip Hop",
        "translations": {
            "en": "Trip Hop",
            "pt": "Trip Hop",
            "kk": "Трип-хоп",
            "ru": "Трип-хоп"
        }
    },
    {
        "label": "Vaporwave", "value": "Vaporwave",
        "translations": {
            "en": "Vaporwave",
            "pt": "Vaporwave",
            "kk": "Vaporwave",
            "ru": "Vaporwave"
        }
    },
    {
        "label": "World Music", "value": "World Music",
        "translations": {
            "en": "World Music",
            "pt": "World Music",
            "kk": "Әлем музыкасы",
            "ru": "Этническая музыка"
        }
    }
]


def generate_genres():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if conn is None:
            logger.error("Failed to get database connection. Aborting.")
            return

        cursor = conn.cursor()
        now = datetime.now()
        default_user_id = 0
        default_rank = 999

        logger.info("Starting to generate genres...")

        for genre_data in genre_options_data:
            identifier = genre_data["value"]
            loc_name_data = genre_data["translations"]

            try:
                cursor.execute("""
                    INSERT INTO kneobroadcaster__genres
                    (author, reg_date, last_mod_user, last_mod_date, identifier, rank, loc_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    default_user_id,
                    now,
                    default_user_id,
                    now,
                    identifier,
                    default_rank,
                    json.dumps(loc_name_data)
                ))
                genre_id = cursor.fetchone()[0]
                logger.info(f"Genre created: {identifier} (ID: {genre_id}) with rank {default_rank}")

            except Exception as e:
                logger.error(f"Error creating genre {identifier}: {e}")

        conn.commit()
        logger.info(f"Successfully generated {len(genre_options_data)} genres.")

    except Exception as e:
        logger.error(f"Database connection or major transaction error: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Finished generating genres.")


if __name__ == "__main__":
    generate_genres()