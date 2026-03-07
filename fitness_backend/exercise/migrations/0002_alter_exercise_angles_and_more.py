import json
from django.db import migrations
from django.contrib.postgres.fields import ArrayField
from django.db import models


def populate_temp_fields(apps, schema_editor):
    Exercise = apps.get_model('exercise', 'Exercise')
    fields_to_convert = ['angles', 'concentric_times', 'eccentric_times', 'forces']

    with schema_editor.connection.cursor() as cursor:
        for field in fields_to_convert:
            temp_field = f"{field}_temp"
            cursor.execute(f'SELECT id, {field} FROM exercise_exercise')
            for record in cursor.fetchall():
                exercise_id, jsonb_data = record
                if jsonb_data:
                    array_data = json.loads(jsonb_data)
                    cursor.execute(
                        f'UPDATE exercise_exercise SET {temp_field} = %s WHERE id = %s',
                        [array_data, exercise_id]
                    )


class Migration(migrations.Migration):
    dependencies = [
        ('exercise', '0001_initial'),
    ]

    operations = [
        # Step 1: Add new temporary fields
        migrations.AddField(
            model_name='exercise',
            name='angles_temp',
            field=ArrayField(models.FloatField(blank=True, null=True), null=True, blank=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='concentric_times_temp',
            field=ArrayField(models.FloatField(blank=True, null=True), null=True, blank=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='eccentric_times_temp',
            field=ArrayField(models.FloatField(blank=True, null=True), null=True, blank=True),
        ),
        migrations.AddField(
            model_name='exercise',
            name='forces_temp',
            field=ArrayField(models.FloatField(blank=True, null=True), null=True, blank=True),
        ),

        # Step 2: Populate temporary fields with converted data
        migrations.RunPython(populate_temp_fields),

        # Step 3: Remove old fields
        migrations.RemoveField(
            model_name='exercise',
            name='angles',
        ),
        migrations.RemoveField(
            model_name='exercise',
            name='concentric_times',
        ),
        migrations.RemoveField(
            model_name='exercise',
            name='eccentric_times',
        ),
        migrations.RemoveField(
            model_name='exercise',
            name='forces',
        ),

        # Step 4: Rename temporary fields to replace old ones
        migrations.RenameField(
            model_name='exercise',
            old_name='angles_temp',
            new_name='angles',
        ),
        migrations.RenameField(
            model_name='exercise',
            old_name='concentric_times_temp',
            new_name='concentric_times',
        ),
        migrations.RenameField(
            model_name='exercise',
            old_name='eccentric_times_temp',
            new_name='eccentric_times',
        ),
        migrations.RenameField(
            model_name='exercise',
            old_name='forces_temp',
            new_name='forces',
        ),
    ]
