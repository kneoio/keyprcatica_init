from faker import Faker
from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the helper function
import json

fake = Faker()


def generate_organizations(count=10):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            # Generate a random organization name
            organization_name = fake.company()

            # Use generate_loc_name to create loc_name with translations
            loc_name = generate_loc_name(organization_name, organization_name, organization_name)

            cursor.execute("""
                INSERT INTO __organizations (author, last_mod_user, identifier, org_category_id, biz_id, rank, loc_name)
                VALUES (%s, %s, %s, (SELECT id FROM __org_categories ORDER BY RANDOM() LIMIT 1), %s, %s, %s)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                organization_name,  # identifier
                fake.unique.ean8(),  # biz_id
                fake.random_int(min=1, max=10),  # rank
                json.dumps(loc_name),  # loc_name as a JSON map with translations
            ))
            logger.info(f"Organization {i + 1}/{count} inserted with name: {organization_name}")
        except Exception as e:
            logger.error(f"Error inserting organization {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting organizations.")
