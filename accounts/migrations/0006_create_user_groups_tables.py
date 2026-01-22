# Generated manually to create missing many-to-many tables
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_customuser_is_blocked'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            # Create the groups and permissions many-to-many tables
            sql="""
            CREATE TABLE IF NOT EXISTS accounts_customuser_groups (
                id BIGSERIAL PRIMARY KEY,
                customuser_id BIGINT NOT NULL REFERENCES accounts_customuser(id) ON DELETE CASCADE,
                group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
                UNIQUE (customuser_id, group_id)
            );
            
            CREATE TABLE IF NOT EXISTS accounts_customuser_user_permissions (
                id BIGSERIAL PRIMARY KEY,
                customuser_id BIGINT NOT NULL REFERENCES accounts_customuser(id) ON DELETE CASCADE,
                permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
                UNIQUE (customuser_id, permission_id)
            );
            
            CREATE INDEX IF NOT EXISTS accounts_customuser_groups_customuser_id_idx 
                ON accounts_customuser_groups(customuser_id);
            CREATE INDEX IF NOT EXISTS accounts_customuser_groups_group_id_idx 
                ON accounts_customuser_groups(group_id);
            CREATE INDEX IF NOT EXISTS accounts_customuser_user_permissions_customuser_id_idx 
                ON accounts_customuser_user_permissions(customuser_id);
            CREATE INDEX IF NOT EXISTS accounts_customuser_user_permissions_permission_id_idx 
                ON accounts_customuser_user_permissions(permission_id);
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS accounts_customuser_groups CASCADE;
            DROP TABLE IF EXISTS accounts_customuser_user_permissions CASCADE;
            """
        ),
    ]
