# Socratic Question Bank for Design Review

Socratic questioning guides discovery through carefully structured questions rather than direct critique. These questions surface hidden assumptions, expose gaps in reasoning, and lead to deeper understanding.

---

## Principles of Socratic Questioning

1. **Questions guide discovery; they don't lecture**
2. **Remain open-ended, not yes/no**
3. **Express genuine curiosity about the design**
4. **Progress from broad to specific**
5. **Create productive discomfort without humiliation**
6. **Pause for answers; don't stack questions**

---

## Category 1: Clarifying Questions

**Purpose**: Expose vagueness and ambiguity in the proposal.

### General Clarification

- What exactly do you mean by "{term}"?
- Can you give me an example of that?
- How does this differ from the current approach?
- What is the scope of this change?
- What is explicitly NOT included in this proposal?

### Behavior Clarification

- What is the intended behavior when input is null?
- What is the intended behavior when input is empty?
- What is the intended behavior when input is malformed?
- What happens when the user does {unexpected action}?
- What does "success" look like for this component?

### Requirements Clarification

- Who are the actual users and what are their workflows?
- What are the hard requirements vs. nice-to-haves?
- What constraints are we operating under?
- What is the expected scale (users, data, requests)?
- What is the timeline and why?

### Interface Clarification

- What does the API contract look like?
- What error messages will users see when this fails?
- What are the expected response times?
- What data is required vs. optional?
- How is this documented for consumers?

---

## Category 2: Probing Assumptions

**Purpose**: Challenge underlying beliefs that may be unfounded.

### Technical Assumptions

- What assumptions does this make about network reliability?
- What assumptions does this make about database consistency?
- What assumptions does this make about execution environment?
- What assumptions does this make about data format/quality?
- What if {assumption} turns out to be wrong?

### User Assumptions

- What assumptions does this make about user behavior?
- What assumptions does this make about user knowledge?
- What happens when users don't follow the expected path?
- Have we validated these assumptions with real users?
- What if users use this differently than intended?

### Dependency Assumptions

- What assumptions does this make about {dependency} availability?
- What assumptions does this make about {dependency} performance?
- What assumptions does this make about {API} stability?
- What if {external service} changes their API?
- What if {library} is deprecated or abandoned?

### Implicit Assumptions

- What implicit constraints are built into this design?
- What external factors could invalidate this approach?
- What are we assuming will stay the same?
- What industry trends might affect this?
- What business changes could break this?

---

## Category 3: Probing Evidence

**Purpose**: Examine the support for claims and assertions.

### Testing Evidence

- What tests validate this handles the edge case?
- What load testing supports this scaling claim?
- What security testing has been performed?
- How was this approach validated before proposing?
- What is the test coverage for this change?

### Data Evidence

- What data supports this design decision?
- Where does this requirement come from?
- Has this been benchmarked?
- What metrics will prove this works?
- How do we know the current approach is insufficient?

### Experience Evidence

- Has this pattern been used successfully elsewhere?
- What problems did similar approaches encounter?
- Do we have production experience with this?
- What did competitors/industry do in this situation?
- Are there case studies or references?

### Reasoning Evidence

- What is the logical chain from requirements to this design?
- Where might this reasoning be flawed?
- What alternative conclusions could we draw from the same evidence?
- What evidence would change our conclusion?
- How confident are we in this reasoning?

---

## Category 4: Questioning Perspectives

**Purpose**: Consider the proposal from different viewpoints.

### Role Perspectives

- How would a security-focused reviewer analyze this?
- How would a performance engineer evaluate this?
- How would an SRE assess the operability?
- How would a new hire understand this code?
- How would a customer experience this?

### Adversarial Perspectives

- How would a malicious actor try to exploit this?
- What would a determined attacker do with this information?
- How could this be abused by internal bad actors?
- What would someone trying to DoS this system do?
- How could competitors exploit weaknesses here?

### Temporal Perspectives

- How will this look in 6 months?
- How will this look in 2 years?
- What will we wish we had done differently?
- How will requirements evolve?
- What technical debt does this create?

### Alternative Perspectives

- What would a different team do here?
- How would {known expert} approach this?
- What would a simpler solution look like?
- What would a more robust solution look like?
- What are we not considering?

---

## Category 5: Probing Implications

**Purpose**: Explore downstream effects and dependencies.

### Failure Implications

- If {component} fails, what cascades?
- What depends on this behaving correctly?
- What is the blast radius of a failure here?
- How do we detect when this fails?
- What is the recovery procedure?

### Change Implications

- If we need to change this later, how hard is it?
- What does migration look like?
- How do we roll this back if it fails?
- What breaking changes does this introduce?
- What documentation needs to update?

### Scale Implications

- What happens at 10x current load?
- What happens at 100x current load?
- What resources scale linearly vs. exponentially?
- Where are the bottlenecks?
- What costs scale with this?

### Integration Implications

- How does this affect {dependent system}?
- What downstream consumers need to change?
- How does this affect monitoring/alerting?
- What operational procedures change?
- How does this affect on-call burden?

---

## Category 6: Meta-Questions

**Purpose**: Reflect on the analysis process itself.

### Process Questions

- What is the most important question we haven't asked?
- What are we afraid to bring up about this design?
- What would make us reject this approach entirely?
- What's the worst case scenario we're ignoring?
- If this fails, what will we wish we had asked?

### Bias Questions

- Are we anchored on the first solution proposed?
- Are we suffering from sunk cost fallacy?
- Are we avoiding conflict by not raising concerns?
- Are we overconfident because it worked last time?
- What blind spots might we have?

### Completeness Questions

- What haven't we considered?
- What requirements are we forgetting?
- What stakeholders haven't been consulted?
- What prior art haven't we reviewed?
- What expertise are we missing?

### Decision Questions

- Do we have enough information to decide?
- What would change our decision?
- What is the cost of being wrong?
- What is the cost of waiting for more information?
- Are we deciding by default or by choice?

---

## Using Questions Effectively

### Question Progression

Start broad, then drill down:

1. **Open with context**: "Help me understand the approach here..."
2. **Clarify basics**: "What is the intended behavior when...?"
3. **Probe assumptions**: "What are we assuming about...?"
4. **Examine evidence**: "What validates that...?"
5. **Consider perspectives**: "How would a security reviewer see...?"
6. **Explore implications**: "What happens if this fails?"
7. **Meta-reflect**: "What haven't we asked?"

### Question Framing

| Instead of... | Ask... |
|---------------|--------|
| "This won't scale" | "What happens at 10x load?" |
| "This is insecure" | "How could an attacker exploit this?" |
| "This is wrong" | "What assumptions does this make?" |
| "You forgot about X" | "How does this handle X?" |
| "Bad idea" | "What would make this approach fail?" |

### Avoiding Common Mistakes

- **Don't stack questions** - Ask one, wait for answer
- **Don't use questions as statements** - Genuine curiosity only
- **Don't interrogate** - Create dialogue, not confrontation
- **Don't answer your own questions** - Let them discover
- **Don't rush** - Silence creates space for thinking

---

## Domain-Specific Question Banks

### API Design

- What is the versioning strategy?
- How are breaking changes communicated?
- What is the authentication/authorization model?
- How are errors represented?
- What is the pagination strategy?

### Database Design

- What are the access patterns?
- What indexes support these queries?
- What is the data retention policy?
- How do we handle schema migrations?
- What is the backup/recovery strategy?

### Distributed Systems

- What is the consistency model?
- How are failures detected?
- What is the retry/backoff strategy?
- How is state synchronized?
- What are the CAP trade-offs?

### Security

- What is the threat model?
- What data is sensitive?
- How are secrets managed?
- What audit logging exists?
- What is the incident response plan?

### Performance

- What are the SLOs?
- What are the critical paths?
- Where are the bottlenecks?
- What caching strategy is used?
- How is performance monitored?

---

*These questions are derived from Socratic method literature, design review best practices, and architectural decision frameworks.*
