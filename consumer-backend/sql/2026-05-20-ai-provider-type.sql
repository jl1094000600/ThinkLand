USE think_land;

SET @provider_type_exists := (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'user_ai_configs'
    AND COLUMN_NAME = 'provider_type'
);

SET @provider_type_sql := IF(
  @provider_type_exists = 0,
  'ALTER TABLE user_ai_configs ADD COLUMN provider_type VARCHAR(32) NOT NULL DEFAULT ''custom'' AFTER user_id',
  'SELECT 1'
);

PREPARE provider_type_stmt FROM @provider_type_sql;
EXECUTE provider_type_stmt;
DEALLOCATE PREPARE provider_type_stmt;
