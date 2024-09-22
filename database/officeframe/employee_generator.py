from faker import Faker
from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the helper function
import json

fake = Faker()

def generate_employees(count=25):
    conn = get_connection()
    cursor = conn.cursor()

    for i in range(count):
        try:
            # Select random department, organization, and position
            cursor.execute("SELECT id FROM __departments ORDER BY RANDOM() LIMIT 1")
            department_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM __organizations ORDER BY RANDOM() LIMIT 1")
            organization_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM __positions ORDER BY RANDOM() LIMIT 1")
            position_id = cursor.fetchone()[0]

            # Select a random user ID from _users table
            cursor.execute("SELECT id FROM _users ORDER BY RANDOM() LIMIT 1")
            user_id = cursor.fetchone()[0]

            # Generate loc_name for employee
            loc_name = generate_loc_name(fake.name(), fake.name(), fake.name())

            # Generate a random status (e.g., 1 for active, 0 for inactive)
            status = fake.random_int(min=0, max=1)

            cursor.execute("""
                INSERT INTO __employees (author, last_mod_user, department_id, organization_id, position_id, user_id, status, loc_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                department_id,  # Selected department ID
                organization_id,  # Selected organization ID
                position_id,  # Selected position ID
                user_id,  # Selected user ID
                status,  # Random status (active/inactive)
                json.dumps(loc_name)  # loc_name as JSON with translations
            ))
            logger.info(f"Employee {i + 1}/{count} inserted.")
        except Exception as e:
            logger.error(f"Error inserting employee {i + 1}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting employees.")
