# Consultation Form Tool

## Purpose

Defines the standard structure, validation rules, and submission process for consultation requests.

The objective is to transform conversational information into a complete, validated, and structured consultation request that can be processed by the business team.

---

## Responsibilities

- Collect consultation information
- Validate customer input
- Normalize collected data
- Confirm submitted information
- Create a structured consultation request
- Return submission status

---

## Tool Goal

Convert natural conversation into a standardized consultation request.

---

## Tool Capabilities

- Collect customer information
- Validate required fields
- Confirm collected data
- Generate structured consultation requests
- Submit consultation requests
- Return submission status

---

## Inputs

Typical inputs include:

- Full Name
- Company Name
- Email Address
- Phone Number
- Requested Service
- Project Description
- Industry (optional)
- Company Size (optional)
- Website (optional)
- Budget (optional)
- Timeline (optional)
- Preferred Contact Method (optional)
- Additional Notes (optional)

---

## Outputs

The tool produces a structured consultation request containing:

### Customer Information

- Name
- Email
- Phone

### Company Information

- Company Name
- Industry
- Company Size

### Project Information

- Requested Service
- Business Goals
- Project Description
- Budget
- Timeline

### Submission Information

- Timestamp
- Submission Status
- Request Identifier (if supported)

---

## Validation Rules

Before submission, verify that:

- All required fields are completed.
- Email addresses follow a valid format.
- Phone numbers follow the expected format.
- Required fields are not empty.
- Customer confirms critical information before submission.

---

## Execution Flow

### Step 1

Collect customer information.

### Step 2

Validate required fields.

### Step 3

Identify missing or invalid information.

### Step 4

Request corrections if necessary.

### Step 5

Summarize the collected information.

### Step 6

Ask the customer to confirm the information.

### Step 7

Submit the consultation request.

### Step 8

Return the submission result.

---

## Error Handling

If validation fails:

- Explain the issue clearly.
- Ask for corrected information.
- Retry validation.

If submission fails:

- Inform the customer politely.
- Log the failure if supported.
- Retry according to business rules.

The tool must never invent missing information.

---

## Security Considerations

- Collect only necessary information.
- Handle customer data securely.
- Respect privacy requirements.
- Never expose confidential information.
- Process personal information according to applicable regulations.

---

## Dependencies

- Consultation Workflow
- CRM Tool
- Email Tool
- Integration Tool

---

## Success Criteria

The tool is successful when:

- Required information is collected.
- Customer information is validated.
- The consultation request is successfully submitted.
- The business team receives a complete and structured request.

---

## Limitations

This tool:

- Cannot approve consultation requests.
- Cannot estimate pricing.
- Cannot make business decisions.
- Cannot schedule meetings directly.
- Cannot qualify leads independently.
- Cannot modify business workflows.

---

## Notes

This tool is responsible only for collecting, validating, and submitting consultation requests.

The decision to initiate a consultation belongs to the Consultation Workflow, not this tool.
