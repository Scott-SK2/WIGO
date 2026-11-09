from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.contrib.postgres.operations import CreateExtension
from django.db import migrations

# Configuration de recherche plein texte insensible aux accents et à la casse (§5.1).
CREATE_TS_CONFIG = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'wigo_simple') THEN
    CREATE TEXT SEARCH CONFIGURATION wigo_simple (COPY = simple);
    ALTER TEXT SEARCH CONFIGURATION wigo_simple
      ALTER MAPPING FOR hword, hword_part, word, asciiword, asciihword, hword_asciipart
      WITH unaccent, simple;
  END IF;
END
$$;
"""
DROP_TS_CONFIG = "DROP TEXT SEARCH CONFIGURATION IF EXISTS wigo_simple;"


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        CreateExtension("postgis"),
        UnaccentExtension(),
        TrigramExtension(),
        migrations.RunSQL(CREATE_TS_CONFIG, DROP_TS_CONFIG),
    ]
