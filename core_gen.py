from database.user_generator import generate_users
from database.module_generator import generate_modules
from database.role_generator import generate_roles
from database.lang_generator import generate_langs
from database.relations_filler import fill_user_modules_relations, fill_user_roles_relations

if __name__ == "__main__":
    generate_users()
    generate_modules()
    generate_roles()
    generate_langs()
    fill_user_modules_relations()
    fill_user_roles_relations()
