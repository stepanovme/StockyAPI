ALTER TABLE items
  ADD COLUMN operational_status VARCHAR(32) NOT NULL DEFAULT 'available' AFTER status;

CREATE TABLE IF NOT EXISTS repairs (
  id CHAR(36) NOT NULL PRIMARY KEY,
  item_id CHAR(36) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'in_progress',
  issue_description TEXT NOT NULL,
  service_provider VARCHAR(255) NOT NULL DEFAULT '',
  cost DECIMAL(12,2) NULL,
  started_at DATETIME NOT NULL,
  expected_return_at DATETIME NULL,
  completed_at DATETIME NULL,
  notes TEXT NOT NULL,
  created_by_user_id CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_repairs_item
    FOREIGN KEY (item_id) REFERENCES items(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_repairs_created_by_user
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),

  INDEX idx_repairs_item_id (item_id),
  INDEX idx_repairs_status (status),
  INDEX idx_repairs_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rentals (
  id CHAR(36) NOT NULL PRIMARY KEY,
  item_id CHAR(36) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  renter_name VARCHAR(255) NOT NULL,
  renter_contact VARCHAR(255) NOT NULL DEFAULT '',
  start_at DATETIME NOT NULL,
  end_at DATETIME NOT NULL,
  returned_at DATETIME NULL,
  price_amount DECIMAL(12,2) NOT NULL,
  price_period VARCHAR(32) NOT NULL DEFAULT 'fixed',
  currency VARCHAR(10) NOT NULL DEFAULT 'RUB',
  notes TEXT NOT NULL,
  created_by_user_id CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_rentals_item
    FOREIGN KEY (item_id) REFERENCES items(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_rentals_created_by_user
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),

  INDEX idx_rentals_item_id (item_id),
  INDEX idx_rentals_status (status),
  INDEX idx_rentals_start_at (start_at),
  INDEX idx_rentals_end_at (end_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
