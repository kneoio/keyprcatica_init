import json
from database import get_connection
from util.logging import logger

# Predefined roles with loc_name and loc_descr translated into ENG, POR, KAZ
roles = [
    {
        "identifier": "manager",
        "loc_name": {
            "ENG": "Manager",
            "POR": "Gerente",
            "KAZ": "Менеджер"
        },
        "loc_descr": {
            "ENG": "Manages teams and projects",
            "POR": "Gerencia equipes e projetos",
            "KAZ": "Топтар мен жобаларды басқару"
        }
    },
    {
        "identifier": "admin",
        "loc_name": {
            "ENG": "Administrator",
            "POR": "Administrador",
            "KAZ": "Администратор"
        },
        "loc_descr": {
            "ENG": "System administrator with full permissions",
            "POR": "Administrador do sistema com permissões totais",
            "KAZ": "Толық рұқсаттары бар жүйе әкімшісі"
        }
    },
    {
        "identifier": "coder",
        "loc_name": {
            "ENG": "Coder",
            "POR": "Programador",
            "KAZ": "Бағдарламашы"
        },
        "loc_descr": {
            "ENG": "Writes and maintains the codebase",
            "POR": "Escreve e mantém a base de código",
            "KAZ": "Код базасын жазу және қолдау"
        }
    },
    {
        "identifier": "tester",
        "loc_name": {
            "ENG": "Tester",
            "POR": "Testador",
            "KAZ": "Тестер"
        },
        "loc_descr": {
            "ENG": "Tests code for bugs and quality assurance",
            "POR": "Testa o código para bugs e controle de qualidade",
            "KAZ": "Кодты қателер мен сапаға тексереді"
        }
    },
    {
        "identifier": "dev",
        "loc_name": {
            "ENG": "Developer",
            "POR": "Desenvolvedor",
            "KAZ": "Әзірлеуші"
        },
        "loc_descr": {
            "ENG": "Develops and implements new features",
            "POR": "Desenvolve e implementa novas funcionalidades",
            "KAZ": "Жаңа мүмкіндіктерді әзірлеу және енгізу"
        }
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
                0,  # author set to 0
                0,  # last_mod_user set to 0
                role["identifier"],
                json.dumps(role["loc_name"]),  # Convert loc_name dict to JSON
                json.dumps(role["loc_descr"])  # Convert loc_descr dict to JSON
            ))
            logger.info(f"Role '{role['identifier']}' inserted with translations.")
        except Exception as e:
            logger.error(f"Error inserting role '{role['identifier']}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Finished inserting roles.")
