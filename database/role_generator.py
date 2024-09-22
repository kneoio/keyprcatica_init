import json
from database import get_connection
from util.logging import logger
from cnst.const import generate_loc_name

roles = [
    {
        "identifier": "manager",
        "loc_name": generate_loc_name("Manager", "Gerente", "Менеджер"),
        "loc_descr": generate_loc_name("Manages teams and projects", "Gerencia equipes e projetos", "Топтар мен жобаларды басқару")
    },
    {
        "identifier": "admin",
        "loc_name": generate_loc_name("Administrator", "Administrador", "Администратор"),
        "loc_descr": generate_loc_name("System administrator with full permissions", "Administrador do sistema com permissões totais", "Толық рұқсаттары бар жүйе әкімшісі")
    },
    {
        "identifier": "coder",
        "loc_name": generate_loc_name("Coder", "Programador", "Бағдарламашы"),
        "loc_descr": generate_loc_name("Writes and maintains the codebase", "Escreve e mantém a base de código", "Код базасын жазу және қолдау")
    },
    {
        "identifier": "tester",
        "loc_name": generate_loc_name("Tester", "Testador", "Тестер"),
        "loc_descr": generate_loc_name("Tests code for bugs and quality assurance", "Testa o código para bugs e controle de qualidade", "Кодты қателер мен сапаға тексереді")
    },
    {
        "identifier": "dev",
        "loc_name": generate_loc_name("Developer", "Desenvolvedor", "Әзірлеуші"),
        "loc_descr": generate_loc_name("Develops and implements new features", "Desenvolve e implementa novas funcionalidades", "Жаңа мүмкіндіктерді әзірлеу және енгізу")
    }
]

def generate_roles():
    conn = get_connection()
    cursor = conn.cursor()

    # Insert predefined roles into the database
    for role in roles:
        try:
            cursor.execute("""
                INSERT INTO _roles (author, last_mod_user, identifier, loc_name, loc_descr, reg_date, last_mod_date)
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                0,
                0,
                role["identifier"],
                json.dumps(role["loc_name"]),
                json.dumps(role["loc_descr"])
            ))
            logger.info(f"Role '{role['identifier']}' inserted with translations.")
        except Exception as e:
            logger.error(f"Error inserting role '{role['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting roles.")
