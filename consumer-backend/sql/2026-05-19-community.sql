USE think_land;

CREATE TABLE IF NOT EXISTS community_items (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  owner_user_id BIGINT UNSIGNED NOT NULL,
  source_conversation_id BIGINT UNSIGNED NULL,
  item_type VARCHAR(32) NOT NULL,
  title VARCHAR(191) NOT NULL,
  summary TEXT NOT NULL,
  content_json JSON NULL,
  project_url VARCHAR(512) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'published',
  star_count INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_community_items_owner_created (owner_user_id, created_at),
  KEY idx_community_items_type_created (item_type, created_at),
  KEY idx_community_items_status_created (status, created_at),
  CONSTRAINT fk_community_items_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_community_items_conversation FOREIGN KEY (source_conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS community_stars (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  item_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_community_stars_item_user (item_id, user_id),
  KEY idx_community_stars_user_created (user_id, created_at),
  CONSTRAINT fk_community_stars_item FOREIGN KEY (item_id) REFERENCES community_items(id) ON DELETE CASCADE,
  CONSTRAINT fk_community_stars_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
