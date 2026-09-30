# AI Professional Identity Platform

## 1. Project Overview

Build a production-ready, desktop-first but responsive web application for job seekers.

The product should transform a job seeker's resume and additional professional information into a structured AI-powered professional identity.

The core product consists of four connected capabilities:

1. Candidate Knowledge Profile
2. AI-generated interview/question intelligence
3. Employer-facing candidate AI chatbot
4. AI-generated personal professional website

The application should be designed as a scalable SaaS product, initially targeting individual job seekers and later potentially supporting recruiters/employers.

The product must not be positioned merely as an AI resume builder. The primary differentiation is the persistent candidate knowledge base that powers interview preparation, an employer-facing AI profile, and the candidate's personal website.

---

# 2. Target Users

## Candidate / Job Seeker

A candidate can:

* Register and authenticate
* Upload a resume/CV
* Add/edit professional information
* Add additional personal/professional notes
* Review and correct extracted resume information
* View generated skills and experience
* View AI-generated interview questions
* Filter questions by category, skill, role and experience
* Generate additional questions
* Enable an employer-facing AI profile
* Preview and select personal website templates
* Edit website content
* Preview the website securely
* Purchase/unlock premium features through a one-time payment
* Publish/download permitted assets
* Create support requests
* View support conversations
* Manage their AI profile visibility

## Employer / Recruiter

An employer should be able to access a candidate's shared AI profile through a secure candidate-specific link.

The employer can ask natural-language questions about the candidate.

Examples:

* "What Python experience does this candidate have?"
* "Tell me about their AWS experience."
* "What projects have they worked on?"
* "Does the candidate have team leadership experience?"
* "What database technologies have they used?"

Employer answers must be grounded strictly in candidate-provided information.

The AI must never invent skills, companies, responsibilities, achievements, technologies, qualifications or experience.

## Administrator

Administrators can:

* View registrations
* View candidate profiles
* View payment records
* View revenue/payment statistics
* View support requests
* Respond to support requests
* Manage users
* Manage website templates
* Manage candidate AI profile status
* View website publication status
* View relevant system/audit logs
* Monitor AI processing and failures

---

# 3. Core Product Principle

The system should create a Candidate Knowledge Base.

The knowledge base consists of:

* Structured candidate profile
* Resume content
* Work experience
* Skills
* Projects
* Education
* Certifications
* Achievements
* Candidate-provided notes
* Other approved professional information
* Document chunks
* Vector embeddings
* Source metadata
* Relationships between skills, experience, projects and questions

Do not treat the vector database as the primary source of truth.

PostgreSQL structured data is the source of truth.

Vector search is used for semantic retrieval from unstructured candidate information.

---

# 4. Recommended Technology Stack

## Frontend

Use:

* Next.js
* TypeScript
* React
* Tailwind CSS
* shadcn/ui
* TanStack Query
* Zod

Use a responsive desktop-first design.

The application must work properly on desktop and tablet and remain usable on mobile.

Public candidate websites must be SEO-friendly.

## Backend

Use:

* Python
* Django
* Django REST Framework
* Celery
* Redis

Keep backend business logic in Django rather than implementing critical business logic in Next.js.

## Database

Use:

* PostgreSQL
* pgvector

Do not introduce an external vector database unless there is a demonstrated scalability requirement.

## Storage

Use:

* AWS S3

Resume and private candidate documents must use private S3 storage.

Use pre-signed URLs when temporary access is required.

## Deployment

Use Docker for local development.

Production target:

* AWS
* CloudFront
* AWS WAF
* Application Load Balancer
* Django application
* Next.js application
* RDS PostgreSQL
* S3
* ElastiCache Redis
* Celery workers
* CloudWatch

The first implementation should remain easy to run locally with Docker Compose.

## Payments

Design the payment layer using a provider abstraction.

Initial preferred provider:

* Razorpay

The system should support:

* UPI
* Cards
* Net banking

Payment processing must be webhook-driven and idempotent.

Do not grant paid features merely because the frontend reports successful payment.

---

# 5. AI Provider Architecture

Do not tightly couple the business logic to one AI vendor.

Create an AI provider abstraction.

Conceptually:

AIProvider

* generate()
* generate_structured()
* embed()
* moderate()

Implement the provider layer so that OpenAI or Anthropic can be used without rewriting application business logic.

The application must support structured JSON responses from the AI wherever structured data is required.

Never parse fragile free-form AI responses when a structured response is appropriate.

---

# 6. Resume Processing Pipeline

When a candidate uploads a resume:

1. Store the original file securely.
2. Validate file type and size.
3. Extract text.
4. Parse the resume into structured sections.
5. Extract:

   * name
   * title
   * summary
   * contact information
   * skills
   * experience
   * companies
   * job titles
   * education
   * certifications
   * projects
   * achievements
   * links
6. Show extracted information to the candidate.
7. Allow the candidate to correct the extracted information.
8. Save the corrected structured profile.
9. Chunk relevant unstructured content.
10. Generate embeddings.
11. Store embeddings in PostgreSQL/pgvector.
12. Generate candidate-specific questions.
13. Mark processing status as complete.

The candidate must be able to see processing status.

Use Celery for expensive/asynchronous operations.

Do not perform complete resume processing synchronously inside an HTTP request.

---

# 7. Candidate Knowledge Base

Recommended core entities:

* User
* CandidateProfile
* CandidateDocument
* CandidateNote
* CandidateExperience
* CandidateSkill
* CandidateProject
* CandidateEducation
* CandidateCertification
* CandidateAchievement
* DocumentChunk
* DocumentEmbedding
* CandidateLink

Each piece of AI-generated information must be traceable to candidate-provided information where practical.

Store source metadata for important knowledge.

Example:

source_type:

* resume
* experience
* project
* note
* certification
* candidate_input

source_id:

* related database record

This enables grounded employer chatbot responses.

---

# 8. Question Generation Engine

Build a dedicated question generation subsystem.

Questions should be generated proactively after the candidate profile is processed.

Question categories:

## General

* Career background
* Resume overview
* Education
* Career progression

## Technical

* Programming languages
* Frameworks
* Databases
* Cloud
* DevOps
* Architecture
* Security
* Testing

## Experience

* Responsibilities
* Achievements
* Challenges
* Decisions
* Technical implementations

## Project

For every important project generate:

* project overview
* candidate responsibility
* architecture
* technologies
* challenges
* decisions
* tradeoffs
* failures
* results
* performance
* scalability
* security
* lessons learned
* follow-up questions

## Behavioral

* Leadership
* Teamwork
* Conflict
* Communication
* Decision making
* Failure
* Mentoring
* Ownership
* Stakeholder management

## Domain

Generate questions based on:

* candidate industry
* role
* seniority
* domain
* skills
* experience

## Deep-Dive Questions

The system should recursively generate follow-up questions from claims made in the resume.

Example:

Candidate statement:

"Implemented Redis caching to improve API performance."

Generate:

* Why was caching required?
* Why was Redis selected?
* What data was cached?
* What caching strategy was used?
* How was invalidation handled?
* What happened when Redis was unavailable?
* What performance improvement was observed?
* What alternatives were evaluated?

Questions should be stored with relationships to:

* skill
* experience
* project
* source
* category
* difficulty
* seniority

---

# 9. Employer AI Profile

Candidates can enable an employer-facing AI profile.

The system generates a secure shareable URL.

Example:

/candidate/{public_identifier}

or:

/profile/{public_identifier}

The employer should see:

* Candidate name
* Professional headline
* Selected profile information
* Skills
* Experience
* Projects
* Selected achievements
* AI chatbot

The candidate must control what information is exposed.

Candidate controls:

* Enable/disable profile
* Regenerate public URL
* Expire public URL
* Control visible sections
* Disable chatbot
* Enable/disable job description matching (see §10A)
* View access/activity history

---

# 10. Employer Chatbot RAG

Employer questions must use retrieval-augmented generation.

Flow:

Employer Question
↓
Intent / query analysis
↓
Structured database lookup
+
Vector similarity search
+
Candidate ID filtering
↓
Relevant evidence
↓
LLM
↓
Grounded response

Every retrieval operation must be scoped to the correct candidate.

Never allow cross-candidate retrieval.

The chatbot must:

* Answer only from candidate-approved information.
* Clearly state when information is unavailable.
* Never invent experience.
* Never infer qualifications that are not supported.
* Avoid unsupported claims.
* Prefer concise factual answers.
* Where practical, identify the source section used for the answer.

Example:

Question:
"Does the candidate have AWS experience?"

Answer:
"Yes. The candidate's profile lists AWS experience involving EC2, S3 and RDS."

If the candidate has no AWS information:

"I don't see AWS experience in the candidate information provided."

Do not fabricate an answer.

---

# 10A. Job Description Matching

An employer can paste a job description and get an evidence-based assessment of how well the candidate's profile matches it.

It is available wherever the employer chatbot is: on the employer AI profile (§9) and as a widget on the candidate's personal website (§11). Candidates can also run it privately on their own dashboard to check their fit for a job before applying.

Flow:

Job description (untrusted text)
↓
Requirement extraction (structured output)
↓
Per-requirement retrieval (structured lookup + vector search, scoped to the candidate)
↓
Per-requirement assessment with cited evidence (structured output)
↓
Score computed in code from the assessments
↓
Report

## Output

For every extracted requirement:

* requirement text
* importance: required / preferred
* status: met / partial / no evidence
* evidence: the candidate profile items that support it, with their source section
* short explanation

Plus an overall score (0–100) and a short summary of strengths and gaps.

## Rules

* The score is calculated deterministically in code from the per-requirement statuses and importance weights. The LLM never outputs the overall number directly, so the same assessments always produce the same score.
* "No evidence" means the information is not in the candidate's approved profile. It must never be presented as the candidate lacking the skill. Wording: "Not found in the candidate's profile", never "The candidate does not have …".
* Every "met" or "partial" status must cite profile evidence. An assessment without evidence is downgraded to "no evidence".
* Only candidate-approved, visible profile data may be used, with the same candidate-ID scoping as §10. Sections the candidate has hidden are excluded.
* Assess only job-relevant skills, experience, qualifications and certifications. Never infer or score protected or personal attributes such as age (for example from graduation years), gender, ethnicity, nationality, disability or employment gaps.
* The job description is untrusted input: pass it to the model as delimited data and ignore any instructions inside it.
* Show a disclaimer with every report: the score is an aid based on the candidate's profile, not a hiring decision.

## Candidate controls

* Enable/disable matching on the employer profile and website independently of the chatbot
* Preview a match themselves before enabling it
* View the history of match requests made against their profile (timestamp, job title if detected, score)

## Abuse and cost controls

The public matching endpoint is unauthenticated and calls the LLM, so it requires:

* rate limiting per IP address and per candidate
* a maximum job description length
* bot protection on the public widget
* caching of reports for identical job descriptions against an unchanged profile
* audit logging of every match request

## Storage

JobMatchRequest: candidate, source (employer_profile / website / candidate_self), job description hash, extracted requirements, per-requirement assessments, score, model, created date.

Store the job description text itself only for as long as needed to display the report, and never log it.

---

# 11. Website Generator

The platform should generate a professional personal website from the candidate's structured profile.

The website must be generated from reusable templates rather than allowing the LLM to generate arbitrary production HTML/CSS for every candidate.

Recommended architecture:

Candidate Data
↓
Website Configuration
↓
Selected Template
↓
Theme
↓
Rendered Website

Initial release must contain at least five substantially different templates.

Every template can include the employer chatbot (§10) and job description matching (§10A) as an embedded widget. The widgets call the same backend endpoints as the employer AI profile and obey the same candidate controls: if the candidate disables the chatbot or matching, the widget is not rendered.

## Template 1 — Executive

Suitable for:

* managers
* executives
* consultants

Sections:

* Hero
* Summary
* Experience
* Leadership
* Achievements
* Skills
* Education
* Contact

## Template 2 — Modern Professional

Sections:

* Hero
* About
* Experience
* Skills
* Projects
* Certifications
* Contact

## Template 3 — Technical / Developer

Suitable for:

* software engineers
* architects
* DevOps
* data engineers

Sections:

* Profile
* Technology stack
* Projects
* Architecture/technical achievements
* Experience
* GitHub
* Certifications
* Contact

## Template 4 — Creative

Suitable for:

* designers
* marketers
* content professionals
* creatives

Use visual portfolio sections and large typography.

## Template 5 — Minimal

Clean professional design with:

* Name
* Title
* Summary
* Experience
* Skills
* Projects
* Education
* Contact

Templates must be responsive.

---

# 12. Website Preview Security

The system must provide a protected preview mode.

Do not claim that browser content can be made impossible to download.

Implement reasonable deterrence and access controls:

* No download button in preview
* Authenticated preview
* Tokenized preview URLs
* Expiring preview tokens
* Server-side authorization
* Watermarking where appropriate
* Prevent obvious right-click/save interactions
* Prevent unauthorized API access
* Do not expose template source files
* Do not expose unpublished content
* Rate limiting
* Audit logging

The goal is to prevent casual/manual downloading and unauthorized access, not to provide impossible DRM.

---

# 13. Website Publishing

A candidate should eventually receive a public URL.

Examples:

/u/john-doe

or:

/portfolio/john-doe

The URL identifier must be unique.

Future support can include custom domains.

Do not make custom domains a requirement for MVP.

---

# 14. Payments

The product uses a one-time payment model.

Do not build the architecture around subscriptions.

Payment state should be explicit:

* pending
* initiated
* successful
* failed
* refunded
* cancelled

Use payment provider webhooks.

Payment events must be idempotent.

Paid feature access must be controlled by backend entitlements.

Example:

Entitlement:

* premium_templates
* website_publish
* website_download
* employer_ai_profile
* priority_support

The exact commercial packaging can be configured later.

---

# 15. Support System

Candidates should be able to create support requests.

Support ticket fields:

* ticket number
* candidate
* subject
* description
* priority
* status
* created date
* updated date
* assigned admin
* messages

Statuses:

* Open
* In Progress
* Waiting for User
* Resolved
* Closed

Admin can respond from the admin dashboard.

Candidate can view the conversation.

---

# 16. Admin Dashboard

Admin dashboard should contain:

## Overview

* Total registrations
* Active candidates
* Completed profiles
* Published websites
* Enabled employer profiles
* Total payments
* Successful payments
* Revenue
* Open support tickets

## Users

* Search
* Filter
* View profile
* Payment status
* Website status
* AI profile status
* Account status

## Payments

* Payment ID
* Candidate
* Amount
* Currency
* Provider
* Status
* Date
* Refund status

## Support

* Ticket list
* Filters
* Assignment
* Status
* Conversation

## Website Templates

* Create
* Edit
* Enable/disable
* Preview
* Version

## Audit

Track important events such as:

* login
* resume upload
* profile update
* AI processing
* employer profile activation
* public profile access
* payment
* refund
* support changes
* admin actions

---

# 17. Suggested PostgreSQL Model Structure

Core entities should include approximately:

User
CandidateProfile
CandidateDocument
CandidateNote
CandidateExperience
CandidateSkill
CandidateProject
CandidateEducation
CandidateCertification
CandidateAchievement
CandidateLink

DocumentChunk
DocumentEmbedding

Question
QuestionCategory
QuestionSkill
QuestionSource

EmployerProfile
EmployerChatSession
EmployerChatMessage
JobMatchRequest

Website
WebsiteTemplate
WebsiteTheme
WebsiteVersion

Payment
Entitlement

SupportTicket
SupportMessage

AuditLog

Do not over-normalize during the first implementation. Use practical Django models and introduce additional abstraction only when required.

---

# 18. Frontend Structure

Suggested Next.js application structure:

/app
/(auth)
/dashboard
/profile
/resume
/questions
/ai-profile
/website
/templates
/support
/payment
/admin
/public-profile

Reusable components should be placed in:

/components

API/client abstractions:

/lib/api

Validation:

/lib/validation

Types:

/types

Do not place business logic directly into page components.

---

# 19. Backend Structure

Suggested Django structure:

backend/
config/
apps/
accounts/
candidates/
documents/
resume_parser/
knowledge_base/
questions/
ai_profile/
chatbot/
websites/
payments/
support/
admin_portal/
audit/

Use service classes for complex operations.

Example:

ResumeProcessingService
CandidateProfileService
EmbeddingService
QuestionGenerationService
CandidateRetrievalService
EmployerChatService
WebsiteGenerationService
PaymentService
EntitlementService

Do not put large amounts of business logic directly inside Django views.

---

# 20. Background Tasks

Use Celery for:

* resume parsing
* document processing
* embedding generation
* question generation
* website asset generation
* AI processing
* email notifications
* cleanup of expired preview tokens
* analytics aggregation

Long-running AI jobs must be asynchronous.

Provide job status to the frontend.

---

# 21. Error Handling

The application must fail gracefully.

AI failures should not corrupt candidate data.

If AI generation fails:

* preserve existing candidate information
* record the failure
* allow retry
* provide useful status
* do not expose stack traces to users

All important background jobs should have retry policies.

---

# 22. Security

Security is a first-class requirement.

Implement:

* secure authentication
* authorization checks
* candidate-level data isolation
* CSRF protection where applicable
* secure cookies
* rate limiting
* input validation
* file type validation
* file size limits
* malware scanning strategy for uploaded files
* private object storage
* signed URLs
* API authorization
* audit logs
* secret management
* encrypted transport
* no secrets in source control

Never trust IDs supplied by the frontend.

Every object access must be authorized server-side.

---

# 23. AI Safety / Accuracy Rules

The system must never invent candidate information.

AI-generated content must be treated as a transformation or interpretation of candidate-provided data, not as a source of new factual information.

For resume/profile generation:

* Do not invent employers.
* Do not invent job titles.
* Do not invent years.
* Do not invent technologies.
* Do not invent certifications.
* Do not invent achievements.
* Do not invent metrics.
* Do not invent responsibilities.

When information is missing, explicitly indicate that it is missing.

Candidate approval should be required before publishing important AI-generated content.

---

# 24. MVP Scope

Build the MVP in this order.

## Phase 1

Authentication

Candidate profile

Resume upload

Resume parsing

Structured profile extraction

Candidate review/edit

PostgreSQL persistence

## Phase 2

Candidate Knowledge Base

Document chunking

pgvector

Embeddings

Question generation

Question dashboard

Question categorization

## Phase 3

Employer AI Profile

Secure public link

RAG chatbot

Candidate visibility controls

Chat session logging

Job description matching (employer profile and candidate self-check)

## Phase 4

Website Builder

Five templates

Template selection

Candidate content mapping

Secure preview

Public website

Embedded chatbot and job matching widgets

## Phase 5

Payments

Razorpay integration

Webhook processing

Entitlements

One-time purchase

## Phase 6

Support

Candidate tickets

Admin responses

Notifications

## Phase 7

Admin Dashboard

Registrations

Payments

Support

Websites

AI profiles

Audit logs

---

# 25. Development Principles

When implementing the application:

1. Prefer simple maintainable architecture over premature abstraction.
2. Do not implement all modules at once.
3. Build and verify one vertical slice at a time.
4. Write tests for business-critical services.
5. Keep frontend and backend contracts explicit.
6. Use typed API schemas.
7. Use database migrations.
8. Never silently modify existing data during AI processing.
9. Make background jobs retryable and idempotent.
10. Never expose secrets.
11. Never trust frontend authorization.
12. Keep AI providers replaceable.
13. Keep website templates data-driven.
14. Keep payment provider integration replaceable.
15. Keep candidate data isolated by candidate ID at every retrieval layer.
16. Prefer structured AI outputs over free-form parsing.
17. Log AI processing failures without logging sensitive resume content unnecessarily.
18. Do not add dependencies without a clear reason.
19. Do not introduce microservices during MVP.
20. Start as a modular monolith.

---

# 26. Recommended Initial Architecture

Use a modular monolith:

Next.js
↓
Django REST API
↓
PostgreSQL + pgvector
↓
Redis
↓
Celery

Supporting:

S3
AI Provider
Razorpay

Do not use microservices initially.

The architecture should leave room to extract services later if scale requires it.

---

# 27. Definition of Done

A feature is not complete merely because the UI exists.

A feature is complete when:

* frontend works
* backend API works
* database persistence works
* authorization works
* validation works
* error handling works
* loading states work
* tests exist for critical logic
* responsive behavior works
* security considerations are addressed
* logs are useful
* documentation is updated

Before implementing a feature, inspect the existing architecture and reuse existing patterns.

Do not duplicate functionality.

---

# 28. First Development Goal

Do NOT immediately implement the entire platform.

Start with the first vertical slice:

User Registration
→ Candidate Dashboard
→ Resume Upload
→ Resume Parsing
→ Structured Candidate Profile
→ Candidate Review/Edit
→ Persist to PostgreSQL

After this vertical slice is stable, implement the Candidate Knowledge Base and question-generation engine.

Only after these are stable should the Employer AI Profile and website generator be implemented.

The application should always remain runnable during development.

Use Docker Compose for local development.

Maintain a clear README containing:

* architecture
* environment variables
* local setup
* Docker commands
* database migration commands
* test commands
* AI provider configuration
* payment provider configuration
* deployment notes
