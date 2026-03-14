-- Migration 026: Add response_body column to user_requests
-- Stores the actual response text sent to the user (truncated to 10KB)

ALTER TABLE user_requests
    ADD COLUMN response_body TEXT DEFAULT NULL;
