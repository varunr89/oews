# Contract: AzureProvisioningService

**Feature**: 003-hosted-sql-db
**Requirements**: FR-005, FR-020, FR-022, FR-023

## Purpose

Create Azure SQL Serverless resources (resource group, server, database).

## Interface

### Method: `create_resource_group(config: DeploymentConfiguration, credential: AzureCliCredential) -> ResourceGroupResult`

**Description**: Create Azure resource group for migration

**Inputs**:
- `config`: DeploymentConfiguration
- `credential`: AzureCliCredential

**Outputs**:
- `ResourceGroupResult`:
  - `resource_group_name`: str
  - `resource_id`: str
  - `location`: str

**Behavior**:
- Use `azure-mgmt-resource.ResourceManagementClient`
- Create resource group in specified region
- Name pattern: `{config.resource_group_name}` or auto-generate
- Set tags for identification (e.g., `created_by: oews-migration`)

**Errors**:
- `AzureProvisioningException`: Resource group creation failed
- `InsufficientQuotaException`: Subscription quota exceeded

**Requirements Mapping**:
- FR-005: Create Azure SQL database (prerequisite: resource group)

---

### Method: `create_sql_server(config: DeploymentConfiguration, credential: AzureCliCredential, resource_group: str) -> SqlServerResult`

**Description**: Create Azure SQL Server

**Inputs**:
- `config`: DeploymentConfiguration
- `credential`: AzureCliCredential
- `resource_group`: str - Resource group name

**Outputs**:
- `SqlServerResult`:
  - `server_name`: str
  - `fully_qualified_domain_name`: str (e.g., "oews-azure-server.database.windows.net")
  - `resource_id`: str
  - `admin_username`: str

**Behavior**:
- Use `azure-mgmt-sql.SqlManagementClient`
- Generate secure admin password (store securely, don't log)
- Create server with firewall rule allowing Azure services
- Wait for server provisioning to complete (long-running operation)

**Errors**:
- `AzureProvisioningException`: Server creation failed
- `ServerNameConflictException`: Server name already taken

**Requirements Mapping**:
- FR-005: Create Azure SQL database (prerequisite: server)

---

### Method: `create_sql_database(config: DeploymentConfiguration, credential: AzureCliCredential, resource_group: str, server_name: str) -> SqlDatabaseResult`

**Description**: Create Azure SQL Serverless database

**Inputs**:
- `config`: DeploymentConfiguration
- `credential`: AzureCliCredential
- `resource_group`: str
- `server_name`: str

**Outputs**:
- `SqlDatabaseResult`:
  - `database_name`: str
  - `connection_string`: str
  - `resource_id`: str
  - `status`: str (e.g., "Online")

**Behavior**:
- Use `azure-mgmt-sql.SqlManagementClient`
- Create database with serverless SKU: `GP_S_Gen5` tier
- Set `auto_pause_delay` for cost optimization
- Wait for database creation to complete

**Errors**:
- `AzureProvisioningException`: Database creation failed
- `DatabaseNameConflictException`: Database name already exists

**Requirements Mapping**:
- FR-005: Create Azure SQL Serverless database

---

### Method: `delete_resources(resources: List[AzureResource], credential: AzureCliCredential) -> RollbackResult`

**Description**: Delete Azure resources during rollback

**Inputs**:
- `resources`: List[AzureResource] - Resources to delete (in reverse creation order)
- `credential`: AzureCliCredential

**Outputs**:
- `RollbackResult`:
  - `success`: bool
  - `deleted_resources`: List[str] - Successfully deleted resource IDs
  - `failed_resources`: List[tuple[str, str]] - (resource_id, error_message)

**Behavior**:
- Iterate through resources in reverse order (database → server → resource group)
- For each resource: call appropriate deletion API
- Wait for long-running delete operations to complete
- Track successes and failures
- If resource group deletion succeeds, all contained resources automatically deleted

**Errors**: None (errors tracked in result, doesn't raise)

**Requirements Mapping**:
- FR-020: Automatic rollback on failure
- FR-022: Notify user during rollback
- FR-023: Handle rollback failures gracefully

---

## Contract Test Assertions

```python
def test_create_resource_group_success():
    # Given: Valid configuration and credentials
    service = AzureProvisioningService()
    config = DeploymentConfiguration(...)
    credential = AzureCliCredential()

    # When: Create resource group
    result = service.create_resource_group(config, credential)

    # Then: Resource group created
    assert result.resource_group_name.startswith("oews-migration")
    assert result.location == config.azure_region

def test_create_sql_server_success():
    # Given: Resource group exists
    service = AzureProvisioningService()

    # When: Create SQL server
    result = service.create_sql_server(config, credential, "rg-test")

    # Then: Server created
    assert result.server_name is not None
    assert ".database.windows.net" in result.fully_qualified_domain_name

def test_create_sql_database_success():
    # Given: Server exists
    service = AzureProvisioningService()

    # When: Create database
    result = service.create_sql_database(config, credential, "rg-test", "server-test")

    # Then: Database created with serverless SKU
    assert result.database_name == config.database_name
    assert result.status == "Online"

def test_create_sql_database_name_conflict():
    # Given: Database name already exists
    service = AzureProvisioningService()

    # When: Create database with existing name
    # Then: Raises exception
    with pytest.raises(DatabaseNameConflictException):
        service.create_sql_database(config, credential, "rg-test", "server-test")

def test_delete_resources_success():
    # Given: Created resources
    service = AzureProvisioningService()
    resources = [AzureResource(...), AzureResource(...)]

    # When: Delete resources
    result = service.delete_resources(resources, credential)

    # Then: All resources deleted
    assert result.success == True
    assert len(result.deleted_resources) == len(resources)
    assert len(result.failed_resources) == 0
```
