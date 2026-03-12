# Research: Limiting LINE Bot to First 20 Users (Beta Testing)

**Date**: 2026-01-17
**Focus**: User access control for beta/testing phase
**Status**: Complete

---

## Problem Decomposition

**Goal**: Limit dev LINE Bot to only accept the first 20 employee users during testing phase.

**Core Requirements**:
- Accept only the first 20 users who add the bot as friend
- Reject/ignore messages from users beyond the limit
- Simple implementation (testing phase only)
- Reversible when ready for wider release

**Constraints**:
- Must work with existing LINE Bot Lambda architecture
- Minimal infrastructure changes (temporary feature)
- No changes to LINE Developer Console required
- Dev environment only

**Success Criteria**:
- First 20 users can interact normally
- User 21+ receives a "beta full" message
- Count persists across Lambda invocations
- Easy to disable when beta ends

---

## Solution Space (Divergent Phase)

### Option 1: DynamoDB Allowlist Table (New Table)

**Description**: Create a dedicated DynamoDB table to store allowed user IDs. Check against this table on every message.

**How it works**:
1. Create `dr-daily-report-line-beta-users-dev` table
2. On `follow` event, check count; if < 20, add user_id
3. On `message` event, check if user_id exists in table
4. Reject messages from non-allowlisted users

**Pros**:
- Clean separation of concerns
- Easy to inspect/manage users via AWS Console
- Survives Lambda restarts
- Can manually add/remove users

**Cons**:
- New infrastructure (temporary table)
- DynamoDB cost (minimal, but non-zero)
- Requires Terraform changes

**Implementation Complexity**: Medium (Terraform + Python)

---

### Option 2: Aurora Table for Beta Users

**Description**: Add a `line_beta_users` table to existing Aurora database.

**How it works**:
1. Create table: `CREATE TABLE line_beta_users (user_id VARCHAR(64) PRIMARY KEY, joined_at TIMESTAMP)`
2. On `follow` event, check count; if < 20, insert user
3. On `message` event, check if user exists
4. Reject if not in table

**Pros**:
- Uses existing Aurora infrastructure
- Can join with other data if needed
- SQL queries for management

**Cons**:
- Aurora connection overhead for simple check
- Overkill for 20 users
- Requires migration

**Implementation Complexity**: Medium (Migration + Python)

---

### Option 3: Environment Variable Allowlist (Static)

**Description**: Store comma-separated user IDs in Doppler/env var.

**How it works**:
1. Set `LINE_BETA_USERS=U123,U456,U789...` in Doppler
2. On message, check if `user_id in LINE_BETA_USERS.split(',')`
3. Pre-populate with known employee user IDs

**Pros**:
- Simplest implementation
- No infrastructure changes
- Instant deployment via Doppler

**Cons**:
- Requires knowing user IDs upfront (users must add bot first)
- Manual update for each new user
- Not "first 20" - requires explicit user ID management
- Limited to env var size

**Implementation Complexity**: Low (Python only)

---

### Option 4: DynamoDB Counter + Allowlist in Existing Pattern

**Description**: Extend existing DynamoDB usage pattern (like Telegram watchlist) for LINE beta users.

**How it works**:
1. Use module similar to `terraform/modules/dynamodb/`
2. Create `dr-daily-report-line-beta-users-dev` table with:
   - `user_id` (PK)
   - `joined_at` timestamp
   - TTL for auto-cleanup after beta
3. Lambda checks/inserts atomically

**Pros**:
- Follows existing project patterns
- DynamoDB atomic operations prevent race conditions
- TTL auto-cleans after beta period
- Reusable infrastructure pattern

**Cons**:
- New table needed
- Terraform deployment required

**Implementation Complexity**: Medium (Terraform + Python)

---

### Option 5: In-Memory Set with S3 Persistence (Recommended)

**Description**: Keep user set in Lambda memory, persist to S3 for durability.

**How it works**:
1. On Lambda cold start, load user set from S3 JSON file
2. On `follow` event, if set size < 20, add user and save to S3
3. On `message` event, check if user in set
4. S3 file: `s3://line-bot-pdf-reports-{account}/beta-users.json`

**Pros**:
- Uses existing S3 bucket (no new infrastructure)
- Fast in-memory lookups
- Simple JSON file (easy to inspect/edit)
- No Terraform changes needed

**Cons**:
- Race condition possible (two simultaneous follows)
- S3 eventual consistency (acceptable for beta)
- Requires S3 read on cold start

**Implementation Complexity**: Low-Medium (Python only)

---

### Option 6: LINE Official Account Settings (No Code)

**Description**: Use LINE Official Account Manager to limit friends.

**How it works**:
1. LINE Official Account has a "Greeting message" feature
2. Cannot directly limit friends, but can close friend additions

**Pros**:
- No code changes

**Cons**:
- **Cannot actually limit to first N users** - LINE doesn't have this feature
- Can only turn off friend additions entirely
- No programmatic control

**Implementation Complexity**: N/A (not viable)

---

## Evaluation Matrix

| Criterion | DynamoDB (Opt 1) | Aurora (Opt 2) | Env Var (Opt 3) | DynamoDB Pattern (Opt 4) | S3 (Opt 5) |
|-----------|------------------|----------------|-----------------|--------------------------|------------|
| Performance | 9/10 | 7/10 | 10/10 | 9/10 | 8/10 |
| Simplicity | 6/10 | 5/10 | 9/10 | 6/10 | 8/10 |
| First-N Logic | 10/10 | 10/10 | 3/10 | 10/10 | 9/10 |
| No New Infra | 3/10 | 8/10 | 10/10 | 3/10 | 10/10 |
| Reversibility | 9/10 | 8/10 | 10/10 | 9/10 | 10/10 |
| **Total** | **37** | **38** | **42** | **37** | **45** |

**Scoring notes**:
- **First-N Logic**: Can it automatically accept first 20 without manual ID management?
- **No New Infra**: Does it require Terraform/AWS changes?
- **Reversibility**: How easy to disable when beta ends?

---

## Ranked Recommendations

### 1. S3 Persistence (Score: 45/50) - Recommended

**Why**: Best balance of simplicity, no infrastructure changes, and "first 20" automation.

**Trade-offs**:
- Gain: No Terraform, uses existing S3, easy to disable
- Lose: Slight race condition risk (acceptable for 20-user beta)

**Implementation**:
```python
# In src/integrations/line_bot.py

import boto3
import json

class LineBot:
    BETA_USER_LIMIT = 20
    BETA_USERS_S3_KEY = "beta-users.json"

    def __init__(self):
        # ... existing init ...
        self.s3_client = boto3.client('s3')
        self.beta_bucket = os.getenv('PDF_BUCKET_NAME')  # Reuse existing bucket
        self.beta_users = self._load_beta_users()

    def _load_beta_users(self) -> set:
        """Load beta users from S3 on cold start"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.beta_bucket,
                Key=self.BETA_USERS_S3_KEY
            )
            data = json.loads(response['Body'].read())
            return set(data.get('users', []))
        except self.s3_client.exceptions.NoSuchKey:
            return set()
        except Exception as e:
            logger.warning(f"Failed to load beta users: {e}")
            return set()

    def _save_beta_users(self):
        """Persist beta users to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.beta_bucket,
                Key=self.BETA_USERS_S3_KEY,
                Body=json.dumps({'users': list(self.beta_users)}),
                ContentType='application/json'
            )
        except Exception as e:
            logger.error(f"Failed to save beta users: {e}")

    def _is_beta_user(self, user_id: str) -> bool:
        """Check if user is in beta program"""
        return user_id in self.beta_users

    def _try_add_beta_user(self, user_id: str) -> bool:
        """Try to add user to beta. Returns True if added, False if full."""
        if user_id in self.beta_users:
            return True  # Already a beta user
        if len(self.beta_users) >= self.BETA_USER_LIMIT:
            return False  # Beta full
        self.beta_users.add(user_id)
        self._save_beta_users()
        return True

    def handle_follow(self, event):
        """Handle follow event with beta limit"""
        source = event.get("source", {})
        user_id = source.get("userId", "")

        if not user_id:
            return self.get_help_message()

        if self._try_add_beta_user(user_id):
            logger.info(f"✅ Beta user added: {user_id} ({len(self.beta_users)}/{self.BETA_USER_LIMIT})")
            return self.get_help_message()
        else:
            logger.info(f"❌ Beta full, rejecting: {user_id}")
            return self._get_beta_full_message()

    def handle_message(self, event):
        """Handle message with beta check"""
        source = event.get("source", {})
        user_id = source.get("userId", "")

        if not self._is_beta_user(user_id):
            return self._get_beta_full_message()

        # ... existing message handling ...

    def _get_beta_full_message(self):
        return """ขออภัยครับ 🙏

ขณะนี้ Daily Report Bot อยู่ในช่วงทดสอบ และรับผู้ใช้ครบจำนวนแล้ว

กรุณาติดต่อทีมพัฒนาหากต้องการเข้าร่วมทดสอบ

ขอบคุณที่สนใจครับ! 🙂"""
```

**To disable when beta ends**: Remove the beta check methods and `_is_beta_user()` calls.

---

### 2. Environment Variable (Score: 42/50)

**When to choose**: If you already know the 20 employee user IDs (e.g., from a test run).

**Trade-offs**:
- Gain: Simplest, instant deployment
- Lose: Must manually collect and manage user IDs

**Implementation**:
```python
# Simple check
BETA_USERS = set(os.getenv('LINE_BETA_USERS', '').split(','))

def _is_beta_user(self, user_id: str) -> bool:
    return user_id in BETA_USERS or not BETA_USERS
```

---

### 3. DynamoDB Table (Score: 37-38/50)

**When to choose**: If you need atomic operations, want to query beta users, or plan to extend the feature.

**Trade-offs**:
- Gain: Robust, queryable, follows project patterns
- Lose: Requires Terraform deployment

---

## Additional Considerations

### Getting User IDs from LINE

Per [LINE Developers documentation](https://developers.line.biz/en/docs/messaging-api/getting-user-ids/):

1. **From webhooks**: User ID is in `source.userId` on follow/message events
2. **Get all followers API**: Only for **verified or premium accounts**
3. **User ID format**: `U[0-9a-f]{32}` (e.g., `U8189cf6745fc0d808977bdb0b9f22995`)

Your current code already extracts user_id at `line_bot.py:197`:
```python
source = event.get("source", {})
user_id = source.get("userId", "")
```

### LINE Account Type Limitation

If your LINE Official Account is **unverified**:
- Cannot use `get_followers` API to list all users
- Must track users via webhook events (which the recommended solution does)

### Race Condition Mitigation

If you're concerned about the S3 race condition:
1. Accept it (20 users, low traffic during beta)
2. Use DynamoDB with conditional writes
3. Use Aurora with `INSERT ... ON CONFLICT`

---

## Quick Start Guide

### For S3 Solution (Recommended)

1. **No Terraform changes needed** - uses existing S3 bucket

2. **Modify `src/integrations/line_bot.py`**:
   - Add beta user methods (see code above)
   - Add beta check in `handle_follow()` and `handle_message()`

3. **Deploy**:
   ```bash
   git add src/integrations/line_bot.py
   git commit -m "feat(line-bot): Add 20-user beta limit"
   git push origin dev  # Triggers deploy
   ```

4. **Verify**:
   - Add bot as friend from test account
   - Check S3 for `beta-users.json`
   - Confirm user is listed

5. **To end beta**:
   - Remove beta check code
   - Delete `beta-users.json` from S3
   - Deploy

---

## Resources

- [LINE Developers - Get user IDs](https://developers.line.biz/en/docs/messaging-api/getting-user-ids/)
- [LINE Messaging API Reference](https://developers.line.biz/en/reference/messaging-api/)
- [line-bot-sdk-python Documentation](https://line-bot-sdk-python.readthedocs.io/en/stable/linebot.html)

---

## Next Steps

```bash
# Recommended: Implement S3 solution
# 1. Edit src/integrations/line_bot.py with beta user logic
# 2. Deploy to dev
# 3. Test with employee accounts

# Alternative: Use env var if you have user IDs
# 1. Collect user IDs from initial test users
# 2. Set LINE_BETA_USERS in Doppler
# 3. Add simple check in line_bot.py
```

---

*Research completed: 2026-01-17*
