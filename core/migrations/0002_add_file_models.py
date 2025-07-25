# Generated manually for file models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hash', models.CharField(db_index=True, max_length=64, unique=True)),
                ('size', models.BigIntegerField(db_index=True)),
                ('storage_path', models.TextField()),
                ('mime_type', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'files',
                'indexes': [
                    models.Index(fields=['hash'], name='core_file_hash_idx'),
                    models.Index(fields=['size'], name='core_file_size_idx'),
                    models.Index(fields=['mime_type'], name='core_file_mime_type_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='UserFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_filename', models.CharField(max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_associations', to='core.file')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_files', to='core.user')),
            ],
            options={
                'db_table': 'user_files',
                'indexes': [
                    models.Index(fields=['user', 'deleted'], name='core_userfile_user_deleted_idx'),
                    models.Index(fields=['uploaded_at'], name='core_userfile_uploaded_at_idx'),
                    models.Index(fields=['original_filename'], name='core_userfile_original_filename_idx'),
                    models.Index(fields=['deleted'], name='core_userfile_deleted_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='userfile',
            constraint=models.UniqueConstraint(fields=('user', 'file', 'original_filename'), name='unique_user_file_name'),
        ),
    ] 