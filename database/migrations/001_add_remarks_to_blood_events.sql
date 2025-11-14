-- ============================================================================
-- Migration 001: Add remarks column to blood_events table
-- ============================================================================
-- Date: 2025-11-14
-- Purpose: Add missing remarks column to support blood transfer notes
-- Issue: "table blood_events has no column named remarks" error
-- ============================================================================

-- Add remarks column if it doesn't exist
-- Note: SQLite doesn't support IF NOT EXISTS for ALTER TABLE,
-- so this may error if column already exists (which is expected and safe)

ALTER TABLE blood_events ADD COLUMN remarks TEXT;

-- Verify the column was added
-- (This is just for documentation - actual verification happens in run_migration.sh)
-- Expected result: Column 'remarks' should appear in: PRAGMA table_info(blood_events);
