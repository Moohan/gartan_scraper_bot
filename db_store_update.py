import sys

with open('db_store.py', 'r') as f:
    lines = f.readlines()

new_lines = []
inserted_user_table = False
inserted_init_db_change = False

for line in lines:
    new_lines.append(line)
    if 'APPLIANCE_TABLE = """' in line and not inserted_user_table:
        # Find the end of APPLIANCE_TABLE
        pass # We'll insert after the block
    if 'FOREIGN KEY (appliance_id) REFERENCES appliance(id)' in line and not inserted_user_table:
        new_lines.append(');\n')
        new_lines.append('"""\n\n')
        new_lines.append('USERS_TABLE = """\n')
        new_lines.append('CREATE TABLE IF NOT EXISTS users (\n')
        new_lines.append('    id INTEGER PRIMARY KEY AUTOINCREMENT,\n')
        new_lines.append('    username TEXT NOT NULL UNIQUE,\n')
        new_lines.append('    password_hash TEXT NOT NULL,\n')
        new_lines.append('    must_change_password INTEGER DEFAULT 1\n')
        new_lines.append(');\n')
        new_lines.append('"""\n')
        inserted_user_table = True
        # Skip the original closing of APPLIANCE_TABLE if we already added it
        # Wait, the way I'm doing this is messy. Let's use a better approach.
