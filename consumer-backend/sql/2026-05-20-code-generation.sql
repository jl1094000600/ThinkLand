USE think_land;

CREATE TABLE IF NOT EXISTS code_generation_jobs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  conversation_id BIGINT UNSIGNED NULL,
  title VARCHAR(191) NOT NULL,
  target_description TEXT NOT NULL,
  stack_json JSON NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'planning',
  provider_type VARCHAR(32) NOT NULL DEFAULT 'custom',
  estimated_tokens INT NOT NULL DEFAULT 0,
  estimated_points INT NOT NULL DEFAULT 0,
  actual_tokens INT NOT NULL DEFAULT 0,
  actual_points INT NOT NULL DEFAULT 0,
  github_repo VARCHAR(255) NULL,
  github_branch VARCHAR(255) NULL,
  github_url VARCHAR(512) NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_code_generation_jobs_user_created (user_id, created_at),
  KEY idx_code_generation_jobs_status_created (status, created_at),
  CONSTRAINT fk_code_generation_jobs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_code_generation_jobs_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS code_generation_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  title VARCHAR(191) NOT NULL,
  payload_json JSON NULL,
  sequence_index INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_code_generation_events_sequence (job_id, sequence_index),
  CONSTRAINT fk_code_generation_events_job FOREIGN KEY (job_id) REFERENCES code_generation_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS code_generation_files (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  path VARCHAR(512) NOT NULL,
  language VARCHAR(64) NOT NULL,
  content LONGTEXT NOT NULL,
  explanation TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'generated',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_code_generation_files_job_path (job_id, path),
  CONSTRAINT fk_code_generation_files_job FOREIGN KEY (job_id) REFERENCES code_generation_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS code_graph_nodes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  node_key VARCHAR(128) NOT NULL,
  node_type VARCHAR(64) NOT NULL,
  label VARCHAR(191) NOT NULL,
  description TEXT NOT NULL,
  file_path VARCHAR(512) NULL,
  position_json JSON NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'generated',
  PRIMARY KEY (id),
  KEY idx_code_graph_nodes_job_key (job_id, node_key),
  CONSTRAINT fk_code_graph_nodes_job FOREIGN KEY (job_id) REFERENCES code_generation_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS code_graph_edges (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  source_key VARCHAR(128) NOT NULL,
  target_key VARCHAR(128) NOT NULL,
  edge_type VARCHAR(64) NOT NULL,
  label VARCHAR(191) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_code_graph_edges_job (job_id),
  CONSTRAINT fk_code_graph_edges_job FOREIGN KEY (job_id) REFERENCES code_generation_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_github_configs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  encrypted_token TEXT NOT NULL,
  default_repo VARCHAR(255) NULL,
  default_branch VARCHAR(128) NOT NULL DEFAULT 'main',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_user_github_configs_user_id (user_id),
  CONSTRAINT fk_user_github_configs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
