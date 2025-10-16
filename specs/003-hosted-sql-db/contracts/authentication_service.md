# Contract: AzureAuthenticationService

**Feature**: 003-hosted-sql-db
**Requirements**: FR-003, FR-004, SR-001, SR-002, SR-003

## Purpose

Verify Azure CLI authentication and obtain credentials for Azure SDK operations.

## Interface

### Method: `verify_cli_session() -> AuthenticationResult`

**Description**: Check if user has active Azure CLI session

**Inputs**: None (reads from Azure CLI state)

**Outputs**:
- `AuthenticationResult`:
  - `is_authenticated`: bool - Whether valid session exists
  - `subscription_id`: str - Active Azure subscription ID (if authenticated)
  - `account_name`: str - Logged-in account email/name
  - `tenant_id`: str - Azure tenant ID

**Behavior**:
- Attempt to create `AzureCliCredential` from `azure-identity`
- Call Azure SDK to verify credentials work (e.g., list subscriptions)
- If successful: return authenticated result with subscription details
- If fails: return unauthenticated result with empty fields

**Errors**:
- `AzureCliNotInstalledException`: Azure CLI not found on system
- `AzureCliNotLoggedInException`: No active `az login` session
- `AzureAuthenticationException`: Credentials exist but invalid/expired

**Requirements Mapping**:
- FR-003: Use Azure CLI credentials
- FR-004: Verify active session before deployment

---

### Method: `get_credential() -> AzureCliCredential`

**Description**: Get Azure CLI credential object for SDK use

**Inputs**: None

**Outputs**:
- `AzureCliCredential` object (from `azure-identity`)

**Behavior**:
- Return credential object suitable for Azure SDK clients
- Credential automatically uses cached `az login` session
- No credentials stored or logged (SR-001, SR-002)

**Errors**:
- `AzureCliNotLoggedInException`: No active session

**Requirements Mapping**:
- FR-003: Use Azure CLI session for authentication
- SR-001: No credential logging
- SR-002: Secure credential handling

---

### Method: `validate_permissions(subscription_id: str) -> PermissionsResult`

**Description**: Check if authenticated user has required Azure permissions

**Inputs**:
- `subscription_id`: str - Target subscription ID

**Outputs**:
- `PermissionsResult`:
  - `has_permissions`: bool - Whether user can create resources
  - `missing_permissions`: List[str] - List of missing permission scopes
  - `role`: str - User's role in subscription (if available)

**Behavior**:
- Use Azure Resource Management API to check role assignments
- Verify user has at least "Contributor" role or equivalent
- Check specific permissions: create resource groups, create SQL resources

**Errors**:
- `InsufficientPermissionsException`: User lacks required permissions
- `SubscriptionNotFoundException`: Subscription ID not found

**Requirements Mapping**:
- SR-003: Validate permissions before resource creation

---

## Contract Test Assertions

```python
def test_verify_cli_session_when_logged_in():
    # Given: User has run `az login`
    service = AzureAuthenticationService()

    # When: Verify CLI session
    result = service.verify_cli_session()

    # Then: Authentication succeeds
    assert result.is_authenticated == True
    assert result.subscription_id is not None
    assert result.account_name is not None

def test_verify_cli_session_when_not_logged_in():
    # Given: User has NOT run `az login`
    service = AzureAuthenticationService()

    # When: Verify CLI session
    # Then: Raises exception
    with pytest.raises(AzureCliNotLoggedInException):
        service.verify_cli_session()

def test_get_credential_returns_valid_credential():
    # Given: User authenticated
    service = AzureAuthenticationService()

    # When: Get credential
    credential = service.get_credential()

    # Then: Returns AzureCliCredential
    assert isinstance(credential, AzureCliCredential)

def test_validate_permissions_with_contributor_role():
    # Given: User has Contributor role
    service = AzureAuthenticationService()

    # When: Validate permissions
    result = service.validate_permissions("subscription-123")

    # Then: Has permissions
    assert result.has_permissions == True
    assert len(result.missing_permissions) == 0
```
