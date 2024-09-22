from database.officeframe.org_category_generator import generate_org_categories
from database.officeframe.organization_generator import generate_organizations
from database.officeframe.department_generator import generate_departments
from database.officeframe.position_generator import generate_positions
from database.officeframe.employee_generator import generate_employees
from database.officeframe.label_generator import generate_labels
from database.officeframe.task_type_generator import generate_task_types

if __name__ == "__main__":
    generate_task_types()          # Task types first
    generate_org_categories()      # Then org categories
    generate_organizations()       # Then organizations
    generate_departments()         # Then departments (which rely on task types and organizations)
    generate_positions()           # Then positions
    generate_employees()           # Then employees (which rely on departments, positions, and organizations)
    generate_labels()              # Finally, generate labels
