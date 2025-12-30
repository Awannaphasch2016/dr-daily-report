# Evidence Hierarchy Templates

**Purpose**: Practical templates for applying Progressive Evidence Strengthening (CLAUDE.md Principle #2) to specific domains.

**When to use**: When verifying operations in a specific domain (UI, file system, database, message queues, etc.), use the appropriate template to ensure you check all evidence layers.

---

## Template Structure

Each domain template follows the 4-layer evidence hierarchy:

1. **Surface Signals** (Weakest): Did execution finish?
2. **Content Signals** (Stronger): Is data structure valid?
3. **Observability Signals** (Stronger): What actually happened?
4. **Ground Truth** (Strongest): Does reality match intent?

---

## HTTP/REST API Verification

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Status code | HTTP status code | `assert response.status_code == 200` |
| **Content** | Response payload | JSON schema validation | `assert "user_id" in response.json()` |
| **Observability** | Application logs | Check for ERROR/WARN logs | `grep ERROR /var/log/app.log` |
| **Ground Truth** | Database state | Query database directly | `SELECT * FROM users WHERE id = ?` |

### Code Example

```python
def verify_user_creation_api(email: str):
    # Layer 1: Surface
    response = requests.post("/api/users", json={"email": email})
    assert response.status_code == 201  # Created

    # Layer 2: Content
    data = response.json()
    assert "user_id" in data
    assert data["email"] == email

    # Layer 3: Observability
    logs = check_application_logs(last_seconds=5)
    assert not any(log.level == "ERROR" for log in logs)

    # Layer 4: Ground Truth
    user = db.query(User).filter_by(email=email).first()
    assert user is not None
    assert user.email == email
```

---

## File System Operations

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Exit code | Process exit code | `echo $?` returns 0 |
| **Content** | File content | Read and validate content | `cat file.txt \| grep "expected"` |
| **Observability** | System logs | Check syslog/journalctl | `journalctl -u service --since "1 minute ago"` |
| **Ground Truth** | Disk state | Verify file exists with correct permissions | `ls -la /path/to/file` |

### Code Example

```python
def verify_file_write(path: str, content: str):
    # Layer 1: Surface
    result = subprocess.run(["touch", path], capture_output=True)
    assert result.returncode == 0

    # Layer 2: Content
    with open(path, "r") as f:
        actual_content = f.read()
    assert actual_content == content

    # Layer 3: Observability
    # Check system logs for write errors
    logs = subprocess.run(
        ["journalctl", "-u", "filesystem", "--since", "1 minute ago"],
        capture_output=True, text=True
    )
    assert "error" not in logs.stdout.lower()

    # Layer 4: Ground Truth
    stat_result = os.stat(path)
    assert stat_result.st_size == len(content)
    assert os.access(path, os.R_OK)  # Readable
```

---

## Database Operations

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Rowcount | Affected rows count | `cursor.rowcount > 0` |
| **Content** | Query result | Validate returned data | `assert len(results) == expected_count` |
| **Observability** | Database logs | Check DB error logs | `tail -f /var/log/mysql/error.log` |
| **Ground Truth** | Table state | Direct table inspection | `SELECT * FROM table WHERE id = ?` |

### Code Example

```python
def verify_user_insert(user_data: dict):
    # Layer 1: Surface
    result = db.execute(
        "INSERT INTO users (email, name) VALUES (?, ?)",
        (user_data["email"], user_data["name"])
    )
    assert result.rowcount == 1

    # Layer 2: Content
    # Verify insert returned expected structure
    assert result.lastrowid is not None
    user_id = result.lastrowid

    # Layer 3: Observability
    # Check database logs for errors during insert
    db_logs = check_database_logs(last_seconds=5)
    assert not any("ERROR" in log for log in db_logs)

    # Layer 4: Ground Truth
    # Query table directly to verify data persisted correctly
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    assert user is not None
    assert user["email"] == user_data["email"]
    assert user["name"] == user_data["name"]
```

---

## UI/Frontend Interactions

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Event fired | Event listener triggered | `onClick handler called` |
| **Content** | DOM updated | Inspect DOM changes | `expect(element).toHaveTextContent("Success")` |
| **Observability** | Console logs | Check browser console | `expect(console.error).not.toHaveBeenCalled()` |
| **Ground Truth** | Visual render | Screenshot/visual regression | `expect(screenshot).toMatchSnapshot()` |

### Code Example (Playwright)

```python
def verify_button_click(page):
    # Layer 1: Surface
    button = page.locator("#submit-button")
    button.click()  # Event fired successfully (no exception)

    # Layer 2: Content
    # Verify DOM updated correctly
    success_message = page.locator("#success-message")
    expect(success_message).to_be_visible()
    expect(success_message).to_have_text("Form submitted successfully")

    # Layer 3: Observability
    # Check console for errors
    console_logs = page.evaluate("() => window.consoleErrors || []")
    assert len(console_logs) == 0

    # Layer 4: Ground Truth
    # Verify visual render matches expectation
    screenshot = page.screenshot()
    assert compare_with_baseline(screenshot, "submit-success.png")
```

---

## Message Queue Operations

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Send ACK | Producer received acknowledgment | `response.MessageId is not None` |
| **Content** | Message payload | Validate message structure | `assert "body" in message` |
| **Observability** | Broker logs | Check queue/broker logs | `aws sqs get-queue-attributes` |
| **Ground Truth** | Consumer state | Verify consumer processed message | Check consumer database/state |

### Code Example (AWS SQS)

```python
def verify_message_sent(queue_url: str, message: dict):
    # Layer 1: Surface
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )
    assert "MessageId" in response
    message_id = response["MessageId"]

    # Layer 2: Content
    # Receive message to verify payload
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
    assert "Messages" in messages
    received = json.loads(messages["Messages"][0]["Body"])
    assert received == message

    # Layer 3: Observability
    # Check queue metrics
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages"]
    )
    assert int(attrs["Attributes"]["ApproximateNumberOfMessages"]) >= 1

    # Layer 4: Ground Truth
    # Verify consumer processed message (check consumer's database/state)
    time.sleep(2)  # Wait for async processing
    consumer_record = db.query(ProcessedMessage).filter_by(
        message_id=message_id
    ).first()
    assert consumer_record is not None
    assert consumer_record.status == "processed"
```

---

## AWS Lambda Deployment

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Exit code | Deployment command succeeded | `aws lambda update-function-code` exit 0 |
| **Content** | Function metadata | Check function configuration | `aws lambda get-function-configuration` |
| **Observability** | CloudWatch logs | Check deployment logs | `aws logs filter-pattern "ERROR"` |
| **Ground Truth** | Actual invocation | Invoke function and verify response | `aws lambda invoke --function-name X` |

### Code Example

```bash
#!/bin/bash
# Progressive Evidence Strengthening for Lambda deployment

FUNCTION_NAME="my-lambda-function"

# Layer 1: Surface - Deployment command succeeds
echo "Layer 1: Deploying Lambda..."
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file fileb://function.zip
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Layer 1 FAILED: Deployment command failed"
  exit 1
fi
echo "✅ Layer 1 PASSED: Deployment command succeeded"

# Layer 2: Content - Function configuration correct
echo "Layer 2: Verifying function configuration..."
CONFIG=$(aws lambda get-function-configuration --function-name "$FUNCTION_NAME")
TIMEOUT=$(echo "$CONFIG" | jq -r '.Timeout')
if [ "$TIMEOUT" -ne 60 ]; then
  echo "❌ Layer 2 FAILED: Timeout is $TIMEOUT, expected 60"
  exit 1
fi
echo "✅ Layer 2 PASSED: Function configuration correct"

# Layer 3: Observability - No errors in logs
echo "Layer 3: Checking CloudWatch logs..."
ERRORS=$(aws logs filter-log-events \
  --log-group-name "/aws/lambda/$FUNCTION_NAME" \
  --filter-pattern "ERROR" \
  --start-time "$(($(date +%s) - 300))000" \
  | jq '.events | length')
if [ "$ERRORS" -gt 0 ]; then
  echo "❌ Layer 3 FAILED: Found $ERRORS errors in logs"
  exit 1
fi
echo "✅ Layer 3 PASSED: No errors in CloudWatch logs"

# Layer 4: Ground Truth - Function actually works
echo "Layer 4: Invoking function..."
OUTPUT=$(aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{"test": true}' \
  response.json \
  | jq -r '.StatusCode')
if [ "$OUTPUT" -ne 200 ]; then
  echo "❌ Layer 4 FAILED: Invocation status $OUTPUT"
  exit 1
fi
RESPONSE=$(cat response.json | jq -r '.statusCode')
if [ "$RESPONSE" -ne 200 ]; then
  echo "❌ Layer 4 FAILED: Function returned $RESPONSE"
  exit 1
fi
echo "✅ Layer 4 PASSED: Function invocation successful"

echo ""
echo "✅ ALL LAYERS VERIFIED - Deployment confirmed"
```

---

## Testing/Test Execution

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Test passed | No exception raised | `pytest test_file.py::test_function` exit 0 |
| **Content** | Assertions passed | All assertions succeeded | Assertions in test body |
| **Observability** | No error logs | Test didn't log errors | `caplog.records` is empty |
| **Ground Truth** | Side effects correct | Verify actual state changes | Check database/file/API state |

### Code Example

```python
def test_user_creation_with_evidence_layers(caplog):
    """
    Test user creation verifying all evidence layers.

    This is an example of applying Progressive Evidence Strengthening
    to test verification.
    """

    # Layer 1: Surface - Test executes without exception
    user = create_user(email="test@example.com", name="Test User")
    # If this fails, exception is raised (surface layer fails)

    # Layer 2: Content - Assertions pass
    assert user is not None  # Content exists
    assert user.email == "test@example.com"  # Content correct
    assert user.id is not None  # Has expected fields
    assert isinstance(user.created_at, datetime)  # Correct types

    # Layer 3: Observability - No errors logged
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) == 0, f"Found error logs: {error_logs}"

    # Layer 4: Ground Truth - Database state matches intent
    # Query database directly (bypassing ORM to avoid false positives)
    with db.engine.connect() as conn:
        result = conn.execute(
            "SELECT * FROM users WHERE id = %s", (user.id,)
        ).fetchone()

    assert result is not None, "User not found in database"
    assert result["email"] == "test@example.com"
    assert result["name"] == "Test User"
    assert result["deleted_at"] is None  # Not soft-deleted

    # ✅ All layers verified - test is truly passing
```

---

## CI/CD Pipeline Verification

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | Pipeline status | GitHub Actions/CI returns success | `workflow conclusion == "success"` |
| **Content** | Artifacts created | Build artifacts exist | Check S3/artifact storage |
| **Observability** | Pipeline logs | No errors in CI logs | `gh run view --log \| grep ERROR` |
| **Ground Truth** | Deployed service | Service responding correctly | `curl https://api.example.com/health` |

### Code Example (GitHub Actions Verification)

```bash
#!/bin/bash
# Verify CI/CD pipeline using Progressive Evidence Strengthening

WORKFLOW_RUN_ID="$1"

# Layer 1: Surface - Pipeline completed successfully
echo "Layer 1: Checking workflow status..."
STATUS=$(gh run view "$WORKFLOW_RUN_ID" --json conclusion -q '.conclusion')
if [ "$STATUS" != "success" ]; then
  echo "❌ Layer 1 FAILED: Workflow status is $STATUS"
  exit 1
fi
echo "✅ Layer 1 PASSED: Workflow completed successfully"

# Layer 2: Content - Artifacts exist
echo "Layer 2: Verifying artifacts..."
ARTIFACTS=$(gh run view "$WORKFLOW_RUN_ID" --json artifacts -q '.artifacts | length')
if [ "$ARTIFACTS" -eq 0 ]; then
  echo "❌ Layer 2 FAILED: No artifacts created"
  exit 1
fi
echo "✅ Layer 2 PASSED: $ARTIFACTS artifacts created"

# Layer 3: Observability - No errors in logs
echo "Layer 3: Checking pipeline logs..."
ERRORS=$(gh run view "$WORKFLOW_RUN_ID" --log | grep -i "error" | wc -l)
if [ "$ERRORS" -gt 0 ]; then
  echo "⚠️  Layer 3 WARNING: Found $ERRORS potential errors in logs"
  # May not be fatal, but warrants investigation
fi
echo "✅ Layer 3 PASSED: Logs reviewed"

# Layer 4: Ground Truth - Deployed service is healthy
echo "Layer 4: Verifying deployed service..."
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health)
if [ "$HEALTH_CHECK" -ne 200 ]; then
  echo "❌ Layer 4 FAILED: Health check returned $HEALTH_CHECK"
  exit 1
fi
RESPONSE=$(curl -s https://api.example.com/health | jq -r '.status')
if [ "$RESPONSE" != "healthy" ]; then
  echo "❌ Layer 4 FAILED: Service reports status: $RESPONSE"
  exit 1
fi
echo "✅ Layer 4 PASSED: Deployed service is healthy"

echo ""
echo "✅ ALL LAYERS VERIFIED - Pipeline truly succeeded"
```

---

## Template for New Domains

When applying Progressive Evidence Strengthening to a new domain:

1. **Identify Surface Signals**: What confirms execution finished? (status codes, exit codes, boolean success)

2. **Identify Content Signals**: What validates data structure? (schemas, types, presence of fields)

3. **Identify Observability Signals**: What reveals execution details? (logs, traces, metrics, audit trails)

4. **Identify Ground Truth**: What confirms intent matched reality? (persistent state, side effects, actual outcomes)

### Template

```markdown
## [Domain Name] Verification

### Evidence Layers

| Layer | Check | How to Verify | Example |
|-------|-------|---------------|---------|
| **Surface** | [What surface signal?] | [How to check?] | [Code example] |
| **Content** | [What content validation?] | [How to validate?] | [Code example] |
| **Observability** | [What logs/traces?] | [How to inspect?] | [Code example] |
| **Ground Truth** | [What actual state?] | [How to verify?] | [Code example] |

### Code Example

\```[language]
def verify_[operation]([params]):
    # Layer 1: Surface
    [check surface signal]

    # Layer 2: Content
    [validate content]

    # Layer 3: Observability
    [check logs/traces]

    # Layer 4: Ground Truth
    [verify actual state]
\```
```

---

## Best Practices

1. **Always progress through all layers** - Don't stop at surface signals
2. **Document which layer failed** - Helps with debugging
3. **Use domain templates as checklists** - Ensures no layers are skipped
4. **Adapt templates to context** - Not all layers are always applicable
5. **Add new domains as discovered** - Extend this document when applying PES to new areas

---

## See Also

- CLAUDE.md Principle #2: Progressive Evidence Strengthening
- `.claude/skills/error-investigation/SKILL.md` - AWS-specific verification
- `.claude/skills/testing-workflow/DEFENSIVE.md` - Testing verification
- `.claude/skills/deployment/SKILL.md` - Deployment verification
