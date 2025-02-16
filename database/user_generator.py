from faker import Faker
from database import get_connection
from util.logging import logger

fake = Faker()

def generate_users(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            login = fake.user_name()
            cursor.execute("""
                INSERT INTO _users (author, last_mod_user, login, email, default_lang, status, reg_date, last_mod_date, 
                                    whatsapp_name, telegram_name, slack_name)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s, %s)
                """, (
                0,
                0,
                login,
                fake.email(),
                fake.random_int(min=1, max=5),
                fake.random_int(min=0, max=1),
                f"{login}_whatsapp",
                f"{login}_telegram",
                f"{login}_slack",
            ))
            logger.info(f"User {i + 1}/{count} inserted.")
        except Exception as e:
            logger.error(f"Error inserting user {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting users.")
