import json
from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name  # Import the centralized language constants and helper function

# Predefined modules with loc_name and loc_descr translated into ENG, POR, KAZ
modules = [
    {
        "identifier": "core",
        "loc_name": generate_loc_name("Core Module", "Módulo Central", "Негізгі модуль"),
        "loc_descr": generate_loc_name("Core system functionalities", "Funcionalidades centrais do sistema", "Жүйенің негізгі функциялары")
    },
    {
        "identifier": "officeframe",
        "loc_name": generate_loc_name("Office Framework", "Estrutura de Escritório", "Кеңсе негізі"),
        "loc_descr": generate_loc_name("Framework for office-related features", "Estrutura para funcionalidades de escritório", "Кеңсеге байланысты мүмкіндіктер негізі")
    },
    {
        "identifier": "projects",
        "loc_name": generate_loc_name("Projects Module", "Módulo de Projetos", "Жобалар модулі"),
        "loc_descr": generate_loc_name("Manage projects and tasks", "Gerenciar projetos e tarefas", "Жобалар мен тапсырмаларды басқару")
    }
]

def generate_modules():
    conn = get_connection()
    cursor = conn.cursor()

    # Insert predefined modules into the database
    for module in modules:
        try:
            cursor.execute("""
                INSERT INTO _modules (author, last_mod_user, identifier, loc_name, loc_descr, reg_date, last_mod_date)
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                0,  # author set to 0
                0,  # last_mod_user set to 0
                module["identifier"],
                json.dumps(module["loc_name"]),  # Convert loc_name dict to JSON
                json.dumps(module["loc_descr"])  # Convert loc_descr dict to JSON
            ))
            logger.info(f"Module '{module['identifier']}' inserted with translations.")
        except Exception as e:
            logger.error(f"Error inserting module '{module['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting modules.")
