import json
from datetime import datetime
from database import get_connection
from util.logging import logger

genre_options_data = [
    {
        "label": "Alternative Rock", "value": "Alternative Rock",
        "translations": {
            "eng": "Alternative Rock",
            "por": "Rock Alternativo",
            "kaz": "Альтернативті рок",
            "rus": "Альтернативный рок"
        }
    },
    {
        "label": "Ambient", "value": "Ambient",
        "translations": {
            "eng": "Ambient",
            "por": "Música Ambiente",
            "kaz": "Эмбиент",
            "rus": "Эмбиент"
        }
    },
    {
        "label": "Blues", "value": "Blues",
        "translations": {
            "eng": "Blues",
            "por": "Blues",
            "kaz": "Блюз",
            "rus": "Блюз"
        }
    },
    {
        "label": "Chillout", "value": "Chillout",
        "translations": {
            "eng": "Chillout",
            "por": "Chillout",
            "kaz": "Чиллаут",
            "rus": "Чиллаут"
        }
    },
    {
        "label": "Classical", "value": "Classical",
        "translations": {
            "eng": "Classical",
            "por": "Música Clássica",
            "kaz": "Классикалық музыка",
            "rus": "Классическая музыка"
        }
    },
    {
        "label": "Country", "value": "Country",
        "translations": {
            "eng": "Country",
            "por": "Country",
            "kaz": "Кантри",
            "rus": "Кантри"
        }
    },
    {
        "label": "Crowd Rock", "value": "Crowd Rock",
        "translations": {
            "eng": "Crowd Rock",
            "por": "Rock de Estádio",
            "kaz": "Стадиондық рок",
            "rus": "Стадионный рок"
        }
    },
    {
        "label": "Dance", "value": "Dance",
        "translations": {
            "eng": "Dance",
            "por": "Dance Music",
            "kaz": "Би музыкасы",
            "rus": "Танцевальная музыка"
        }
    },
    {
        "label": "Dark Synth", "value": "Dark Synth",
        "translations": {
            "eng": "Dark Synth",
            "por": "Dark Synth",
            "kaz": "Dark Synth",
            "rus": "Дарк-синт"
        }
    },
    {
        "label": "Downtempo", "value": "Downtempo",
        "translations": {
            "eng": "Downtempo",
            "por": "Downtempo",
            "kaz": "Даунтемпо",
            "rus": "Даунтемпо"
        }
    },
    {
        "label": "Drum and Bass", "value": "Drum and Bass",
        "translations": {
            "eng": "Drum and Bass",
            "por": "Drum and Bass",
            "kaz": "Драм-н-бэйс",
            "rus": "Драм-н-бэйс"
        }
    },
    {
        "label": "Dubstep", "value": "Dubstep",
        "translations": {
            "eng": "Dubstep",
            "por": "Dubstep",
            "kaz": "Дабстеп",
            "rus": "Дабстеп"
        }
    },
    {
        "label": "EBM", "value": "EBM",
        "translations": {
            "eng": "EBM",
            "por": "EBM",
            "kaz": "EBM",
            "rus": "EBM"
        }
    },
    {
        "label": "Electronic", "value": "Electronic",
        "translations": {
            "eng": "Electronic",
            "por": "Música Eletrónica",
            "kaz": "Электрондық музыка",
            "rus": "Электронная музыка"
        }
    },
    {
        "label": "Electropop", "value": "Electropop",
        "translations": {
            "eng": "Electropop",
            "por": "Electropop",
            "kaz": "Электропоп",
            "rus": "Электропоп"
        }
    },
    {
        "label": "Experimental", "value": "Experimental",
        "translations": {
            "eng": "Experimental",
            "por": "Música Experimental",
            "kaz": "Эксперименттік музыка",
            "rus": "Экспериментальная музыка"
        }
    },
    {
        "label": "Folk", "value": "Folk",
        "translations": {
            "eng": "Folk",
            "por": "Música Folclórica",
            "kaz": "Фолк",
            "rus": "Фолк"
        }
    },
    {
        "label": "Funk", "value": "Funk",
        "translations": {
            "eng": "Funk",
            "por": "Funk",
            "kaz": "Фанк",
            "rus": "Фанк"
        }
    },
    {
        "label": "Futurepop", "value": "Futurepop",
        "translations": {
            "eng": "Futurepop",
            "por": "Futurepop",
            "kaz": "Futurepop",
            "rus": "Futurepop"
        }
    },
    {
        "label": "Garage Rock", "value": "Garage Rock",
        "translations": {
            "eng": "Garage Rock",
            "por": "Garage Rock",
            "kaz": "Гараж рок",
            "rus": "Гаражный рок"
        }
    },
    {
        "label": "Gospel", "value": "Gospel",
        "translations": {
            "eng": "Gospel",
            "por": "Gospel",
            "kaz": "Госпел",
            "rus": "Госпел"
        }
    },
    {
        "label": "Goth Rock", "value": "Goth Rock",
        "translations": {
            "eng": "Goth Rock",
            "por": "Rock Gótico",
            "kaz": "Готикалық рок",
            "rus": "Готик-рок"
        }
    },
    {
        "label": "Grunge", "value": "Grunge",
        "translations": {
            "eng": "Grunge",
            "por": "Grunge",
            "kaz": "Гранж",
            "rus": "Гранж"
        }
    },
    {
        "label": "Hard Rock", "value": "Hard Rock",
        "translations": {
            "eng": "Hard Rock",
            "por": "Hard Rock",
            "kaz": "Хард-рок",
            "rus": "Хард-рок"
        }
    },
    {
        "label": "Hip Hop", "value": "Hip Hop",
        "translations": {
            "eng": "Hip Hop",
            "por": "Hip Hop",
            "kaz": "Хип-хоп",
            "rus": "Хип-хоп"
        }
    },
    {
        "label": "House", "value": "House",
        "translations": {
            "eng": "House",
            "por": "House Music",
            "kaz": "Хаус",
            "rus": "Хаус"
        }
    },
    {
        "label": "IDM", "value": "IDM",
        "translations": {
            "eng": "IDM",
            "por": "IDM",
            "kaz": "IDM",
            "rus": "IDM"
        }
    },
    {
        "label": "Indie Pop", "value": "Indie Pop",
        "translations": {
            "eng": "Indie Pop",
            "por": "Indie Pop",
            "kaz": "Инди-поп",
            "rus": "Инди-поп"
        }
    },
    {
        "label": "Indie Rock", "value": "Indie Rock",
        "translations": {
            "eng": "Indie Rock",
            "por": "Indie Rock",
            "kaz": "Инди-рок",
            "rus": "Инди-рок"
        }
    },
    {
        "label": "Industrial", "value": "Industrial",
        "translations": {
            "eng": "Industrial",
            "por": "Industrial",
            "kaz": "Индастриал",
            "rus": "Индастриал"
        }
    },
    {
        "label": "Industrial Metal", "value": "Industrial Metal",
        "translations": {
            "eng": "Industrial Metal",
            "por": "Metal Industrial",
            "kaz": "Индастриал-метал",
            "rus": "Индастриал-метал"
        }
    },
    {
        "label": "Instrumental", "value": "Instrumental",
        "translations": {
            "eng": "Instrumental",
            "por": "Instrumental",
            "kaz": "Инструменталды",
            "rus": "Инструментальная"
        }
    },
    {
        "label": "Jazz", "value": "Jazz",
        "translations": {
            "eng": "Jazz",
            "por": "Jazz",
            "kaz": "Джаз",
            "rus": "Джаз"
        }
    },
    {
        "label": "Latin", "value": "Latin",
        "translations": {
            "eng": "Latin",
            "por": "Música Latina",
            "kaz": "Латын музыкасы",
            "rus": "Латинская музыка"
        }
    },
    {
        "label": "Lo-fi", "value": "Lo-fi",
        "translations": {
            "eng": "Lo-fi",
            "por": "Lo-fi",
            "kaz": "Lo-fi",
            "rus": "Lo-fi"
        }
    },
    {
        "label": "Metal", "value": "Metal",
        "translations": {
            "eng": "Metal",
            "por": "Metal",
            "kaz": "Метал",
            "rus": "Метал"
        }
    },
    {
        "label": "Minimal Synth", "value": "Minimal Synth",
        "translations": {
            "eng": "Minimal Synth",
            "por": "Minimal Synth",
            "kaz": "Minimal Synth",
            "rus": "Минимал-синт"
        }
    },
    {
        "label": "New Wave", "value": "New Wave",
        "translations": {
            "eng": "New Wave",
            "por": "New Wave",
            "kaz": "Нью-вейв",
            "rus": "Нью-вейв"
        }
    },
    {
        "label": "Noise", "value": "Noise",
        "translations": {
            "eng": "Noise",
            "por": "Noise",
            "kaz": "Нойз",
            "rus": "Нойз"
        }
    },
    {
        "label": "Other", "value": "Other",
        "translations": {
            "eng": "Other",
            "por": "Outro",
            "kaz": "Басқа",
            "rus": "Другое"
        }
    },
    {
        "label": "Pop", "value": "Pop",
        "translations": {
            "eng": "Pop",
            "por": "Pop",
            "kaz": "Поп",
            "rus": "Поп"
        }
    },
    {
        "label": "Post-Punk", "value": "Post-Punk",
        "translations": {
            "eng": "Post-Punk",
            "por": "Pós-Punk",
            "kaz": "Пост-панк",
            "rus": "Пост-панк"
        }
    },
    {
        "label": "Progressive Rock", "value": "Progressive Rock",
        "translations": {
            "eng": "Progressive Rock",
            "por": "Rock Progressivo",
            "kaz": "Прогрессивті рок",
            "rus": "Прогрессивный рок"
        }
    },
    {
        "label": "Psychedelic Rock", "value": "Psychedelic Rock",
        "translations": {
            "eng": "Psychedelic Rock",
            "por": "Rock Psicadélico",
            "kaz": "Психоделикалық рок",
            "rus": "Психоделический рок"
        }
    },
    {
        "label": "Punk Rock", "value": "Punk Rock",
        "translations": {
            "eng": "Punk Rock",
            "por": "Punk Rock",
            "kaz": "Панк-рок",
            "rus": "Панк-рок"
        }
    },
    {
        "label": "R&B", "value": "R&B",
        "translations": {
            "eng": "R&B",
            "por": "R&B",
            "kaz": "R&B",
            "rus": "R&B"
        }
    },
    {
        "label": "Reggae", "value": "Reggae",
        "translations": {
            "eng": "Reggae",
            "por": "Reggae",
            "kaz": "Регги",
            "rus": "Регги"
        }
    },
    {
        "label": "Rock", "value": "Rock",
        "translations": {
            "eng": "Rock",
            "por": "Rock",
            "kaz": "Рок",
            "rus": "Рок"
        }
    },
    {
        "label": "Shoegaze", "value": "Shoegaze",
        "translations": {
            "eng": "Shoegaze",
            "por": "Shoegaze",
            "kaz": "Шугейз",
            "rus": "Шугейз"
        }
    },
    {
        "label": "Ska", "value": "Ska",
        "translations": {
            "eng": "Ska",
            "por": "Ska",
            "kaz": "Ска",
            "rus": "Ска"
        }
    },
    {
        "label": "Soul", "value": "Soul",
        "translations": {
            "eng": "Soul",
            "por": "Soul",
            "kaz": "Соул",
            "rus": "Соул"
        }
    },
    {
        "label": "Soundtrack", "value": "Soundtrack",
        "translations": {
            "eng": "Soundtrack",
            "por": "Trilha Sonora",
            "kaz": "Саундтрек",
            "rus": "Саундтрек"
        }
    },
    {
        "label": "Spoken Word", "value": "Spoken Word",
        "translations": {
            "eng": "Spoken Word",
            "por": "Palavra Falada",
            "kaz": "Spoken Word",
            "rus": "Разговорный жанр"
        }
    },
    {
        "label": "Synthwave", "value": "Synthwave",
        "translations": {
            "eng": "Synthwave",
            "por": "Synthwave",
            "kaz": "Synthwave",
            "rus": "Синтвейв"
        }
    },
    {
        "label": "Techno", "value": "Techno",
        "translations": {
            "eng": "Techno",
            "por": "Techno",
            "kaz": "Техно",
            "rus": "Техно"
        }
    },
    {
        "label": "Trance", "value": "Trance",
        "translations": {
            "eng": "Trance",
            "por": "Trance",
            "kaz": "Транс",
            "rus": "Транс"
        }
    },
    {
        "label": "Trip Hop", "value": "Trip Hop",
        "translations": {
            "eng": "Trip Hop",
            "por": "Trip Hop",
            "kaz": "Трип-хоп",
            "rus": "Трип-хоп"
        }
    },
    {
        "label": "Vaporwave", "value": "Vaporwave",
        "translations": {
            "eng": "Vaporwave",
            "por": "Vaporwave",
            "kaz": "Vaporwave",
            "rus": "Vaporwave"
        }
    },
    {
        "label": "World Music", "value": "World Music",
        "translations": {
            "eng": "World Music",
            "por": "World Music",
            "kaz": "Әлем музыкасы",
            "rus": "Этническая музыка"
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