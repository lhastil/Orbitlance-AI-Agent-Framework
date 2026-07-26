# CRM Tool

## Purpose

Defines the standard interface and behavior for interacting with Customer Relationship Management (CRM) systems.

The objective is to ensure that customer information, conversation outcomes, and business activities are accurately synchronized with the organization's CRM.

---

## Responsibilities

- Create customer records
- Update existing records
- Manage company information
- Store conversation summaries
- Update lead status
- Create follow-up tasks
- Synchronize business data

---

## Tool Goal

Provide a consistent and reliable interface for managing customer and lead information across supported CRM platforms.

---

## Tool Capabilities

- Create Contact
- Update Contact
- Search Contact
- Create Company
- Update Company
- Search Company
- Create Lead
- Update Lead Status
- Create Opportunity
- Add Notes
- Create Follow-up Tasks
- Associate Contacts with Companies
- Retrieve CRM Records

---

## Inputs

Typical inputs include:

### Contact Information

- Full Name
- Email Address
- Phone Number

### Company Information

- Company Name
- Industry
- Company Size
- Website

### Lead Information

- Requested Service
- Business Goals
- Pain Points
- Qualification Status
- Lead Source

### Conversation Information

- Conversation Summary
- Recommendations
- Internal Notes
- Follow-up Requirements

---

## Outputs

The tool may return:

- Contact ID
- Company ID
- Lead ID
- Opportunity ID
- Task ID
- Synchronization Status
- Error Details (if applicable)

---

## Validation Rules

Before performing any action:

- Validate required fields.
- Check for duplicate contacts.
- Check for duplicate companies.
- Verify email format.
- Verify phone number format (if applicable).
- Confirm customer information when necessary.

---

## Execution Flow

### Step 1

Receive structured CRM request.

### Step 2

Validate input data.

### Step 3

Search for existing records.

### Step 4

Determine whether to create or update records.

### Step 5

Perform the requested CRM operation.

### Step 6

Verify successful synchronization.

### Step 7

Return the operation result.

---

## Error Handling

If an operation fails:

- Return a clear error message.
- Preserve customer data.
- Retry only when appropriate.
- Never create duplicate records intentionally.
- Log synchronization failures if supported.

---

## Security Considerations

- Respect customer privacy.
- Never expose confidential CRM information.
- Follow access permissions.
- Synchronize only verified information.
- Protect personally identifiable information (PII).

---

## Dependencies

- Consultation Form Tool
- Consultation Workflow
- Follow-up Workflow
- Integration Tool

---

## Success Criteria

The tool is successful when:

- Customer information is synchronized correctly.
- Duplicate records are avoided.
- Lead information is complete.
- CRM records remain consistent.
- Business teams receive accurate customer information.

---

## Limitations

This tool:

- Cannot qualify leads independently.
- Cannot make business decisions.
- Cannot modify CRM permissions.
- Cannot delete CRM records unless explicitly supported.
- Cannot estimate project pricing.
- Cannot communicate directly with customers.

---

## Notes

This tool provides a standardized CRM interface independent of any specific CRM provider.

CRM-specific implementations (e.g., HubSpot, Salesforce, Zoho, Pipedrive, GoHighLevel, Notion, or custom APIs) should conform to this interface while handling platform-specific details internally.
