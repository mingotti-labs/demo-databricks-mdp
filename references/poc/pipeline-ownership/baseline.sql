SELECT 'prices_raw' t, count(*) n, count(DISTINCT source_file_path) files FROM mdp_dev.bronze_yahoo.prices_raw
UNION ALL SELECT 'events_raw', count(*), count(DISTINCT source_file_path) FROM mdp_dev.bronze_yahoo.events_raw
UNION ALL SELECT 'calendar_raw', count(*), count(DISTINCT source_file_path) FROM mdp_dev.bronze_yahoo.calendar_raw
UNION ALL SELECT 'options_raw', count(*), count(DISTINCT source_file_path) FROM mdp_dev.bronze_yahoo.options_raw
UNION ALL SELECT 'prices_scd1', count(*), NULL FROM mdp_dev.bronze_yahoo_publish.prices_scd1
UNION ALL SELECT 'events_scd1', count(*), NULL FROM mdp_dev.bronze_yahoo_publish.events_scd1
UNION ALL SELECT 'options_scd1', count(*), NULL FROM mdp_dev.bronze_yahoo_publish.options_scd1
UNION ALL SELECT 'calendar_scd2', count(*), count_if(__END_AT IS NOT NULL) FROM mdp_dev.bronze_yahoo_publish.calendar_scd2
