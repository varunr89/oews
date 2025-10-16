# Quickstart: Azure SQL Database Deployment

**Feature**: 003-hosted-sql-db
**Purpose**: Validate the Azure SQL deployment feature end-to-end

## Prerequisites

1. **Azure CLI** installed and authenticated:
   ```bash
   az --version  # Verify Azure CLI installed
   az login      # Authenticate with Azure
   ```

2. **Test SQLite Database**:
   - Use existing `data/oews.db` (from feature 002)
   - Or create test database:
     ```bash
     sqlite3 test_migration.db
     CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, salary REAL);
     INSERT INTO employees VALUES (1, 'Alice', 75000.0), (2, 'Bob', 82000.0);
     .quit
     ```

3. **Configuration File**:
   Create `.env` file in project root:
   ```env
   AZURE_REGION=eastus
   AZURE_RESOURCE_GROUP_PREFIX=oews-quickstart
   BATCH_SIZE=1000
   VALIDATION_SAMPLE_PCT=0.10
   PROGRESS_UPDATE_INTERVAL_SEC=5
   ```

## Test Scenarios

### Scenario 1: Successful Full Migration

**Given**: Valid SQLite database and Azure CLI session

**Steps**:
```bash
# 1. Run deployment command
python -m src.cli.main deploy-azure data/oews.db

# Expected output:
# ✓ Verifying Azure CLI session...
# ✓ Loading configuration from .env...
# ✓ Validating database file: data/oews.db (140KB, 15 tables)
# ✓ Creating Azure resource group: oews-quickstart-abc123...
# ✓ Provisioning Azure SQL Server: oews-azure-server-xyz789...
# ✓ Creating Azure SQL Database: oews-azure...
# → Migrating schema (15 tables)...
# ✓ Created table: employees
# ✓ Created table: departments
# ... (13 more tables)
# → Transferring data...
# → employees: 1000/1000 rows (100%)
# → departments: 50/50 rows (100%)
# ... (13 more tables)
# → Validating migration...
# ✓ All tables exist in both databases
# ✓ Row counts match for all 15 tables
# ✓ Sample validation passed (10% of rows checked)
# ✓ Migration completed successfully!
#
# Validation report saved to: validation_report_<job_id>.json
# Azure SQL connection string: Server=oews-azure-server-xyz789.database.windows.net;Database=oews-azure;...
```

**Verify**:
1. Check Azure portal for created resources
2. Review `validation_report_<job_id>.json`
3. Connect to Azure SQL database and query sample data

**When**: Migration completes

**Then**:
- All tables created in Azure SQL
- All data transferred
- Validation report shows PASS status
- Exit code 0

---

### Scenario 2: Invalid Database Path

**Given**: Non-existent database file path

**Steps**:
```bash
python -m src.cli.main deploy-azure /nonexistent/database.db
```

**Expected Output**:
```
✗ Error: Database file not found at /nonexistent/database.db
Please check the file path and try again.
```

**Then**:
- Clear error message (FR-019)
- Exit code 1
- No Azure resources created

---

### Scenario 3: Missing Azure CLI Session

**Given**: User has NOT run `az login`

**Steps**:
```bash
az logout
python -m src.cli.main deploy-azure data/oews.db
```

**Expected Output**:
```
✗ Error: No active Azure CLI session detected
Please run 'az login' and try again.
```

**Then**:
- Clear error message instructing user to run `az login` (FR-019, FR-025)
- Exit code 1
- No Azure resources created

---

### Scenario 4: Invalid Region Configuration

**Given**: `.env` file has invalid region

**Steps**:
```bash
# Edit .env
echo "AZURE_REGION=invalid-region-xyz" > .env

python -m src.cli.main deploy-azure data/oews.db
```

**Expected Output**:
```
✗ Error: Invalid Azure region 'invalid-region-xyz'
Valid regions include: eastus, westus, centralus, northeurope, ...
Please update AZURE_REGION in .env file.
```

**Then**:
- Clear error message with valid region examples (FR-024, FR-025)
- Exit code 1
- No Azure resources created

---

### Scenario 5: Simulated Migration Failure with Rollback

**Given**: Migration fails during data transfer (simulate by interrupting)

**Steps**:
```bash
# Start migration
python -m src.cli.main deploy-azure data/oews.db

# Interrupt after schema migration starts (Ctrl+C or kill process)
```

**Expected Output**:
```
✓ Creating Azure SQL Database: oews-azure...
→ Migrating schema (15 tables)...
✓ Created table: employees
✗ Error: Migration interrupted

→ Initiating automatic rollback...
→ Deleting Azure SQL Database: oews-azure...
→ Deleting Azure SQL Server: oews-azure-server-xyz789...
→ Deleting resource group: oews-quickstart-abc123...
✓ Rollback completed successfully

All Azure resources have been removed.
```

**Then**:
- Rollback notification displayed (FR-022)
- All created Azure resources deleted (FR-020)
- Exit code 1

---

### Scenario 6: Validation Failure Detection

**Given**: Data intentionally corrupted in Azure SQL after transfer (manual test)

**Steps**:
```bash
# 1. Complete normal migration
python -m src.cli.main deploy-azure data/oews.db

# 2. Manually delete rows from Azure SQL
# 3. Re-run validation only (if supported) or check validation report

# Expected in validation report:
```

**Expected in validation_report.json**:
```json
{
  "status": "FAIL",
  "table_results": [
    {
      "table_name": "employees",
      "row_count_match": false,
      "row_count_source": 1000,
      "row_count_target": 950,
      "discrepancies": ["Row count mismatch: source has 1000 rows, target has 950 rows"]
    }
  ]
}
```

**Then**:
- Validation report shows FAIL status (FR-017)
- Specific discrepancies listed (FR-019)
- User receives clear remediation guidance

---

## Cleanup

After quickstart testing, clean up Azure resources:

```bash
# Option 1: Use Azure Portal
# 1. Navigate to Resource Groups
# 2. Delete resource group "oews-quickstart-*"

# Option 2: Use Azure CLI
az group list --query "[?starts_with(name, 'oews-quickstart')].name" -o tsv | xargs -I {} az group delete --name {} --yes --no-wait

# Verify cleanup
az group list --query "[?starts_with(name, 'oews-quickstart')]"
```

---

## Success Criteria

All scenarios must:
1. Execute without unhandled exceptions
2. Display appropriate progress updates (FR-012)
3. Show clear error messages with actionable guidance (FR-019, FR-025)
4. Successfully rollback on failure (FR-020, FR-022)
5. Generate validation report for successful migrations (FR-017)

---

## Troubleshooting

**Azure CLI errors**:
```bash
az account show  # Verify logged in
az account list  # List available subscriptions
```

**Connection issues**:
- Check Azure SQL firewall rules (should allow Azure services)
- Verify network connectivity to Azure

**Validation failures**:
- Review `validation_report_<job_id>.json` for details
- Check deployment logs: `deployment_<job_id>.log`

---

**Status**: Quickstart guide complete - ready for implementation testing
