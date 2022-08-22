-- ALTER TABLE quests ADD COLUMN rank text;
-- ALTER TABLE weapons ADD COLUMN parent_id integer default null;
--
-- ALTER TABLE weapons ADD COLUMN  `element` text DEFAULT NULL;
-- ALTER TABLE weapons ADD COLUMN  `element_attack` integer DEFAULT NULL;
-- ALTER TABLE weapons ADD COLUMN  `element_2` text DEFAULT NULL;
-- ALTER TABLE weapons ADD COLUMN  `element_2_attack` integer DEFAULT NULL;
-- ALTER TABLE weapons ADD COLUMN  `awaken` text DEFAULT NULL;
-- ALTER TABLE weapons ADD COLUMN  `awaken_attack` integer DEFAULT NULL;

CREATE TABLE 'horn_melodies' (
  '_id' integer primary key autoincrement,
  'notes' text NOT NULL,
  'song' text NOT NULL,
  'effect1' text NOT NULL,
  'effect2' text NOT NULL,
  'duration' text NOT NULL,
  'extension' text NOT NULL
)
