from faker import Faker
from database import get_connection
from util.logging import logger

fake = Faker()

def generate_org_categories(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            cursor.execute("""
                INSERT INTO __org_categories (author, last_mod_user, identifier, loc_name)
                VALUES (%s, %s, %s, %s)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                fake.unique.word(),  # identifier
                fake.json(),  # loc_name can be random JSON
            ))
            logger.info(f"Org Category {i + 1}/{count} inserted.")
        except Exception as e:
            logger.error(f"Error inserting org category {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting org categories.")
