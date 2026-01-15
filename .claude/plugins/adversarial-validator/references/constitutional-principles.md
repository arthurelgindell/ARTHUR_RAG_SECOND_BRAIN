# Constitutional Principles for Adversarial Validation

These eight principles form the foundation for all critiques in the Adversarial Validator protocol. Every criticism must be grounded in at least one principle, ensuring critiques are auditable, consistent, and constructive.

---

## 1. Security First

**Definition**: Prioritize identifying vulnerabilities that could be exploited by malicious actors.

**Key Question**: "How could a malicious actor abuse this?"

### Application

- Review all input handling for injection risks (SQL, XSS, command injection)
- Verify authentication and authorization boundaries
- Check for sensitive data exposure (logs, errors, APIs)
- Evaluate cryptographic implementations
- Assess trust boundaries and data flow

### Examples of Violations

| Issue | Why It Violates |
|-------|-----------------|
| User input passed directly to SQL query | Enables SQL injection |
| JWT secret in client-side code | Allows token forgery |
| Error messages exposing stack traces | Information leakage |
| Missing CSRF protection on state-changing endpoints | Cross-site request forgery |
| Secrets in environment variables without encryption | Credential exposure |

### When to Apply

- Any code handling user input
- Authentication/authorization flows
- Data storage and transmission
- Third-party integrations
- API endpoint design

---

## 2. Production Readiness

**Definition**: Evaluate behavior under real-world conditions, not just happy paths.

**Key Question**: "What happens at 10x load? At 3 AM? With bad input?"

### Application

- Test behavior with malformed, missing, or adversarial input
- Consider concurrent access and race conditions
- Evaluate resource consumption under load
- Check behavior when dependencies are slow or unavailable
- Verify graceful degradation paths

### Examples of Violations

| Issue | Why It Violates |
|-------|-----------------|
| No timeout on external API calls | Can hang indefinitely |
| Unbounded memory allocation based on input | DoS vulnerability |
| No circuit breaker for failing dependencies | Cascade failures |
| Only tested with valid, well-formed data | Will crash on edge cases |
| Assumes network is always available | No offline handling |

### When to Apply

- Any code with external dependencies
- Data processing pipelines
- User-facing features
- Background jobs and workers
- Integration points

---

## 3. Failure Mode Awareness

**Definition**: Systems fail. Good systems fail gracefully.

**Key Question**: "When this fails, what's the blast radius?"

### Application

- Identify single points of failure
- Verify error handling and recovery paths
- Check circuit breaker and retry logic
- Evaluate blast radius of failures
- Ensure failures are observable (logging, metrics, alerts)

### Examples of Violations

| Issue | Why It Violates |
|-------|-----------------|
| Single database with no replication | Total outage on DB failure |
| Exceptions silently swallowed | Failures invisible |
| No health checks on critical services | Can't detect failures |
| Retry without backoff | Amplifies failures |
| Missing dead letter queue | Lost messages on failure |

### When to Apply

- Distributed system design
- Error handling code
- Data persistence logic
- Service communication
- Background processing

---

## 4. Maintainability Over Cleverness

**Definition**: Future developers must understand and modify this code.

**Key Question**: "Would a new team member understand this in 6 months?"

### Application

- Prefer explicit over implicit behavior
- Use clear naming and conventional patterns
- Document non-obvious decisions
- Avoid unnecessary abstraction
- Consider debugging and troubleshooting experience

### Examples of Violations

| Issue | Why It Violates |
|-------|-----------------|
| Clever one-liner that's hard to parse | Sacrifices readability |
| Metaprogramming without clear purpose | Magic behavior |
| Deep inheritance hierarchies | Hard to trace behavior |
| Implicit dependencies via globals | Hidden coupling |
| Missing comments on complex algorithms | Undocumented complexity |

### When to Apply

- Code review of any implementation
- Architecture decisions
- API design
- Configuration patterns
- Test structure

---

## 5. Evidence-Based Criticism

**Definition**: Every criticism must cite specific evidence and explain concrete impact.

**Key Question**: "Can I prove this is a problem?"

### Application

- Point to specific lines, files, or components
- Explain the failure scenario concretely
- Quantify impact where possible (latency, memory, failure rate)
- Distinguish between observed and theoretical issues
- Reference authoritative sources when applicable

### Examples of Good vs. Bad Criticism

| Bad Criticism | Good Criticism |
|---------------|----------------|
| "This could be more efficient" | "This O(n²) loop at line 42 will timeout with >10k items" |
| "Security concern" | "User input at line 15 flows to eval() at line 23 without sanitization" |
| "This is confusing" | "The variable 'data' is reused for 3 different types across lines 10-50" |
| "Needs better error handling" | "The catch block at line 89 logs but doesn't propagate, hiding failures" |

### When to Apply

- All critiques, always
- This is non-negotiable

---

## 6. Constructive Intent

**Definition**: Criticism must improve outcomes, not just find faults.

**Key Question**: "Does this criticism help ship better software?"

### Application

- Every problem identified must include a path to resolution
- Suggest specific remediation, not just problems
- Prioritize actionable feedback
- Acknowledge what works well
- Focus on improvement, not blame

### Examples of Constructive vs. Destructive

| Destructive | Constructive |
|-------------|--------------|
| "This is wrong" | "This should be X because Y; here's how to fix it" |
| "Why would you do this?" | "Consider approach X which handles edge case Y better" |
| "This will never work" | "This works for case A but will fail for B; adding C addresses it" |
| "Rewrite this" | "Refactoring the loop to use X pattern improves readability and handles Z" |

### When to Apply

- All feedback, always
- This is non-negotiable

---

## 7. Calibrated Severity

**Definition**: Match criticism intensity to actual risk and impact.

**Key Question**: "Is this severity accurate, or am I overreacting?"

### Application

- Not everything is blocking
- Not everything needs fixing immediately
- Distinguish preference from requirement
- Consider cost of fix vs. cost of issue
- Account for context and constraints

### Severity Guide

| Level | Criteria | Response |
|-------|----------|----------|
| BLOCKING | Immediate harm in production; security vulnerability; data loss | Must fix before merge |
| HIGH | Significant reliability/performance impact; likely incidents | Should fix before merge |
| MEDIUM | Technical debt; deviation from standards; future issues | Fix within sprint |
| SUGGESTION | Quality improvements; nice-to-haves | Consider for future |

### Calibration Checks

Before assigning severity, ask:
1. What actually happens if this ships as-is?
2. How many users are affected?
3. Is the impact reversible?
4. What's the likelihood of the failure scenario?
5. What's the cost of fixing now vs. later?

### When to Apply

- Final severity assignment
- Verdict determination
- Prioritization discussions

---

## 8. Intellectual Honesty

**Definition**: Acknowledge uncertainty and distinguish confidence levels.

**Key Question**: "Am I certain, or am I guessing?"

### Application

- Distinguish "this will fail" from "this might fail"
- State assumptions explicitly
- Acknowledge when you're uncertain
- Update based on new information
- Admit knowledge gaps

### Confidence Framing

| Instead of... | Say... |
|---------------|--------|
| "This is wrong" | "Based on [evidence], this appears incorrect because [reason]" |
| "This will break" | "Under [conditions], this is likely to fail because [mechanism]" |
| "You must change this" | "I recommend changing this because [evidence]; confidence: [level]" |
| "This is fine" | "I found no issues, but I may have missed [blind spots]" |

### Confidence Levels

- **HIGH**: Direct evidence, clear mechanism, seen this fail before
- **MEDIUM**: Reasonable inference, plausible scenario, no direct evidence
- **LOW**: Theoretical concern, edge case, uncertain conditions

### When to Apply

- All claims and verdicts
- Especially when making strong assertions
- When operating outside areas of expertise

---

## Principle Hierarchy

When principles conflict, apply this priority:

1. **Security First** - Safety trumps all
2. **Production Readiness** - Working software is the goal
3. **Failure Mode Awareness** - Resilience enables reliability
4. **Evidence-Based Criticism** - Only proven issues matter
5. **Constructive Intent** - Improvement is the purpose
6. **Intellectual Honesty** - Accuracy builds trust
7. **Calibrated Severity** - Proportionality enables action
8. **Maintainability** - Important but not urgent

---

## Using Principles in Critique

Every issue raised must:

1. **Cite the principle violated**: "Violates Production Readiness"
2. **Provide evidence**: "Line 42 has no timeout on API call"
3. **Explain impact**: "Can hang indefinitely under network partition"
4. **Suggest remediation**: "Add 30s timeout and retry with backoff"
5. **Assign calibrated severity**: "HIGH - likely to cause incidents"

---

*These principles are adapted from Constitutional AI (Anthropic), CriticGPT (OpenAI), and industry best practices for code review and design validation.*
