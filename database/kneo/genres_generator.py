import json
from datetime import datetime
from database import get_connection
from util.logging import logger

genre_options_data = [
    {
        "label": "Alternative Rock", "value": "Alternative Rock",
        "translations": {
            "ENG": "Alternative Rock",
            "POR": "Rock Alternativo",
            "KAZ": "Альтернативті рок",
            "RUS": "Альтернативный рок"
        }
    },
    {
        "label": "Ambient", "value": "Ambient",
        "translations": {
            "ENG": "Ambient",
            "POR": "Música Ambiente",
            "KAZ": "Эмбиент",
            "RUS": "Эмбиент"
        }
    },
    {
        "label": "Blues", "value": "Blues",
        "translations": {
            "ENG": "Blues",
            "POR": "Blues",
            "KAZ": "Блюз",
            "RUS": "Блюз"
        }
    },
    {
        "label": "Chillout", "value": "Chillout",
        "translations": {
            "ENG": "Chillout",
            "POR": "Chillout",
            "KAZ": "Чиллаут",
            "RUS": "Чиллаут"
        }
    },
    {
        "label": "Classical", "value": "Classical",
        "translations": {
            "ENG": "Classical",
            "POR": "Música Clássica",
            "KAZ": "Классикалық музыка",
            "RUS": "Классическая музыка"
        }
    },
    {
        "label": "Country", "value": "Country",
        "translations": {
            "ENG": "Country",
            "POR": "Country",
            "KAZ": "Кантри",
            "RUS": "Кантри"
        }
    },
    {
        "label": "Crowd Rock", "value": "Crowd Rock",
        "translations": {
            "ENG": "Crowd Rock",
            "POR": "Rock de Estádio",
            "KAZ": "Стадиондық рок",
            "RUS": "Стадионный рок"
        }
    },
    {
        "label": "Dance", "value": "Dance",
        "translations": {
            "ENG": "Dance",
            "POR": "Dance Music",
            "KAZ": "Би музыкасы",
            "RUS": "Танцевальная музыка"
        }
    },
    {
        "label": "Dark Synth", "value": "Dark Synth",
        "translations": {
            "ENG": "Dark Synth",
            "POR": "Dark Synth",
            "KAZ": "Dark Synth",
            "RUS": "Дарк-синт"
        }
    },
    {
        "label": "Downtempo", "value": "Downtempo",
        "translations": {
            "ENG": "Downtempo",
            "POR": "Downtempo",
            "KAZ": "Даунтемпо",
            "RUS": "Даунтемпо"
        }
    },
    {
        "label": "Drum and Bass", "value": "Drum and Bass",
        "translations": {
            "ENG": "Drum and Bass",
            "POR": "Drum and Bass",
            "KAZ": "Драм-н-бэйс",
            "RUS": "Драм-н-бэйс"
        }
    },
    {
        "label": "Dubstep", "value": "Dubstep",
        "translations": {
            "ENG": "Dubstep",
            "POR": "Dubstep",
            "KAZ": "Дабстеп",
            "RUS": "Дабстеп"
        }
    },
    {
        "label": "EBM", "value": "EBM",
        "translations": {
            "ENG": "EBM",
            "POR": "EBM",
            "KAZ": "EBM",
            "RUS": "EBM"
        }
    },
    {
        "label": "Electronic", "value": "Electronic",
        "translations": {
            "ENG": "Electronic",
            "POR": "Música Eletrónica",
            "KAZ": "Электрондық музыка",
            "RUS": "Электронная музыка"
        }
    },
    {
        "label": "Electropop", "value": "Electropop",
        "translations": {
            "ENG": "Electropop",
            "POR": "Electropop",
            "KAZ": "Электропоп",
            "RUS": "Электропоп"
        }
    },
    {
        "label": "Experimental", "value": "Experimental",
        "translations": {
            "ENG": "Experimental",
            "POR": "Música Experimental",
            "KAZ": "Эксперименттік музыка",
            "RUS": "Экспериментальная музыка"
        }
    },
    {
        "label": "Folk", "value": "Folk",
        "translations": {
            "ENG": "Folk",
            "POR": "Música Folclórica",
            "KAZ": "Фолк",
            "RUS": "Фолк"
        }
    },
    {
        "label": "Funk", "value": "Funk",
        "translations": {
            "ENG": "Funk",
            "POR": "Funk",
            "KAZ": "Фанк",
            "RUS": "Фанк"
        }
    },
    {
        "label": "Futurepop", "value": "Futurepop",
        "translations": {
            "ENG": "Futurepop",
            "POR": "Futurepop",
            "KAZ": "Futurepop",
            "RUS": "Futurepop"
        }
    },
    {
        "label": "Garage Rock", "value": "Garage Rock",
        "translations": {
            "ENG": "Garage Rock",
            "POR": "Garage Rock",
            "KAZ": "Гараж рок",
            "RUS": "Гаражный рок"
        }
    },
    {
        "label": "Gospel", "value": "Gospel",
        "translations": {
            "ENG": "Gospel",
            "POR": "Gospel",
            "KAZ": "Госпел",
            "RUS": "Госпел"
        }
    },
    {
        "label": "Goth Rock", "value": "Goth Rock",
        "translations": {
            "ENG": "Goth Rock",
            "POR": "Rock Gótico",
            "KAZ": "Готикалық рок",
            "RUS": "Готик-рок"
        }
    },
    {
        "label": "Grunge", "value": "Grunge",
        "translations": {
            "ENG": "Grunge",
            "POR": "Grunge",
            "KAZ": "Гранж",
            "RUS": "Гранж"
        }
    },
    {
        "label": "Hard Rock", "value": "Hard Rock",
        "translations": {
            "ENG": "Hard Rock",
            "POR": "Hard Rock",
            "KAZ": "Хард-рок",
            "RUS": "Хард-рок"
        }
    },
    {
        "label": "Hip Hop", "value": "Hip Hop",
        "translations": {
            "ENG": "Hip Hop",
            "POR": "Hip Hop",
            "KAZ": "Хип-хоп",
            "RUS": "Хип-хоп"
        }
    },
    {
        "label": "House", "value": "House",
        "translations": {
            "ENG": "House",
            "POR": "House Music",
            "KAZ": "Хаус",
            "RUS": "Хаус"
        }
    },
    {
        "label": "IDM", "value": "IDM",
        "translations": {
            "ENG": "IDM",
            "POR": "IDM",
            "KAZ": "IDM",
            "RUS": "IDM"
        }
    },
    {
        "label": "Indie Pop", "value": "Indie Pop",
        "translations": {
            "ENG": "Indie Pop",
            "POR": "Indie Pop",
            "KAZ": "Инди-поп",
            "RUS": "Инди-поп"
        }
    },
    {
        "label": "Indie Rock", "value": "Indie Rock",
        "translations": {
            "ENG": "Indie Rock",
            "POR": "Indie Rock",
            "KAZ": "Инди-рок",
            "RUS": "Инди-рок"
        }
    },
    {
        "label": "Industrial", "value": "Industrial",
        "translations": {
            "ENG": "Industrial",
            "POR": "Industrial",
            "KAZ": "Индастриал",
            "RUS": "Индастриал"
        }
    },
    {
        "label": "Industrial Metal", "value": "Industrial Metal",
        "translations": {
            "ENG": "Industrial Metal",
            "POR": "Metal Industrial",
            "KAZ": "Индастриал-метал",
            "RUS": "Индастриал-метал"
        }
    },
    {
        "label": "Instrumental", "value": "Instrumental",
        "translations": {
            "ENG": "Instrumental",
            "POR": "Instrumental",
            "KAZ": "Инструменталды",
            "RUS": "Инструментальная"
        }
    },
    {
        "label": "Jazz", "value": "Jazz",
        "translations": {
            "ENG": "Jazz",
            "POR": "Jazz",
            "KAZ": "Джаз",
            "RUS": "Джаз"
        }
    },
    {
        "label": "Latin", "value": "Latin",
        "translations": {
            "ENG": "Latin",
            "POR": "Música Latina",
            "KAZ": "Латын музыкасы",
            "RUS": "Латинская музыка"
        }
    },
    {
        "label": "Lo-fi", "value": "Lo-fi",
        "translations": {
            "ENG": "Lo-fi",
            "POR": "Lo-fi",
            "KAZ": "Lo-fi",
            "RUS": "Lo-fi"
        }
    },
    {
        "label": "Metal", "value": "Metal",
        "translations": {
            "ENG": "Metal",
            "POR": "Metal",
            "KAZ": "Метал",
            "RUS": "Метал"
        }
    },
    {
        "label": "Minimal Synth", "value": "Minimal Synth",
        "translations": {
            "ENG": "Minimal Synth",
            "POR": "Minimal Synth",
            "KAZ": "Minimal Synth",
            "RUS": "Минимал-синт"
        }
    },
    {
        "label": "New Wave", "value": "New Wave",
        "translations": {
            "ENG": "New Wave",
            "POR": "New Wave",
            "KAZ": "Нью-вейв",
            "RUS": "Нью-вейв"
        }
    },
    {
        "label": "Noise", "value": "Noise",
        "translations": {
            "ENG": "Noise",
            "POR": "Noise",
            "KAZ": "Нойз",
            "RUS": "Нойз"
        }
    },
    {
        "label": "Other", "value": "Other",
        "translations": {
            "ENG": "Other",
            "POR": "Outro",
            "KAZ": "Басқа",
            "RUS": "Другое"
        }
    },
    {
        "label": "Pop", "value": "Pop",
        "translations": {
            "ENG": "Pop",
            "POR": "Pop",
            "KAZ": "Поп",
            "RUS": "Поп"
        }
    },
    {
        "label": "Post-Punk", "value": "Post-Punk",
        "translations": {
            "ENG": "Post-Punk",
            "POR": "Pós-Punk",
            "KAZ": "Пост-панк",
            "RUS": "Пост-панк"
        }
    },
    {
        "label": "Progressive Rock", "value": "Progressive Rock",
        "translations": {
            "ENG": "Progressive Rock",
            "POR": "Rock Progressivo",
            "KAZ": "Прогрессивті рок",
            "RUS": "Прогрессивный рок"
        }
    },
    {
        "label": "Psychedelic Rock", "value": "Psychedelic Rock",
        "translations": {
            "ENG": "Psychedelic Rock",
            "POR": "Rock Psicadélico",
            "KAZ": "Психоделикалық рок",
            "RUS": "Психоделический рок"
        }
    },
    {
        "label": "Punk Rock", "value": "Punk Rock",
        "translations": {
            "ENG": "Punk Rock",
            "POR": "Punk Rock",
            "KAZ": "Панк-рок",
            "RUS": "Панк-рок"
        }
    },
    {
        "label": "R&B", "value": "R&B",
        "translations": {
            "ENG": "R&B",
            "POR": "R&B",
            "KAZ": "R&B",
            "RUS": "R&B"
        }
    },
    {
        "label": "Reggae", "value": "Reggae",
        "translations": {
            "ENG": "Reggae",
            "POR": "Reggae",
            "KAZ": "Регги",
            "RUS": "Регги"
        }
    },
    {
        "label": "Rock", "value": "Rock",
        "translations": {
            "ENG": "Rock",
            "POR": "Rock",
            "KAZ": "Рок",
            "RUS": "Рок"
        }
    },
    {
        "label": "Shoegaze", "value": "Shoegaze",
        "translations": {
            "ENG": "Shoegaze",
            "POR": "Shoegaze",
            "KAZ": "Шугейз",
            "RUS": "Шугейз"
        }
    },
    {
        "label": "Ska", "value": "Ska",
        "translations": {
            "ENG": "Ska",
            "POR": "Ska",
            "KAZ": "Ска",
            "RUS": "Ска"
        }
    },
    {
        "label": "Soul", "value": "Soul",
        "translations": {
            "ENG": "Soul",
            "POR": "Soul",
            "KAZ": "Соул",
            "RUS": "Соул"
        }
    },
    {
        "label": "Soundtrack", "value": "Soundtrack",
        "translations": {
            "ENG": "Soundtrack",
            "POR": "Trilha Sonora",
            "KAZ": "Саундтрек",
            "RUS": "Саундтрек"
        }
    },
    {
        "label": "Spoken Word", "value": "Spoken Word",
        "translations": {
            "ENG": "Spoken Word",
            "POR": "Palavra Falada",
            "KAZ": "Spoken Word",
            "RUS": "Разговорный жанр"
        }
    },
    {
        "label": "Synthwave", "value": "Synthwave",
        "translations": {
            "ENG": "Synthwave",
            "POR": "Synthwave",
            "KAZ": "Synthwave",
            "RUS": "Синтвейв"
        }
    },
    {
        "label": "Techno", "value": "Techno",
        "translations": {
            "ENG": "Techno",
            "POR": "Techno",
            "KAZ": "Техно",
            "RUS": "Техно"
        }
    },
    {
        "label": "Trance", "value": "Trance",
        "translations": {
            "ENG": "Trance",
            "POR": "Trance",
            "KAZ": "Транс",
            "RUS": "Транс"
        }
    },
    {
        "label": "Trip Hop", "value": "Trip Hop",
        "translations": {
            "ENG": "Trip Hop",
            "POR": "Trip Hop",
            "KAZ": "Трип-хоп",
            "RUS": "Трип-хоп"
        }
    },
    {
        "label": "Vaporwave", "value": "Vaporwave",
        "translations": {
            "ENG": "Vaporwave",
            "POR": "Vaporwave",
            "KAZ": "Vaporwave",
            "RUS": "Vaporwave"
        }
    },
    {
        "label": "World Music", "value": "World Music",
        "translations": {
            "ENG": "World Music",
            "POR": "World Music",
            "KAZ": "Әлем музыкасы",
            "RUS": "Этническая музыка"
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