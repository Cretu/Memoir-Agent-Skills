# Memory Recall Reference

## Purpose
Elicit personal memories through structured questions without generating narrative prose.
The goal is to help users remember details, not to write.

## Principles

### Do
- Ask open-ended questions that require elaboration
- Focus on sensory details (sights, sounds, smells, textures)
- Explore emotional context and personal significance
- Use follow-up questions to dig deeper
- Request specific moments rather than general summaries

### Don't
- Generate prose or narrative passages
- Make assumptions about what happened
- Rush through important details
- Focus on interpretation rather than recall

## Question Categories

### 1. Context Questions
Establish where and when events occurred:
- "Where were you physically?"
- "What time of day was it?"
- "What season or year was this?"
- "Who else was present?"

### 2. Sensory Questions
Extract sensory memories:
- "What did you see in detail?"
- "What sounds do you remember?"
- "Were there any smells associated with this?"
- "What did you touch or feel?"

### 3. Sequence Questions
Clarify the timeline:
- "What happened just before this moment?"
- "What did you do next?"
- "How long did this last?"
- "What happened immediately after?"

### 4. Emotional Questions
Explore personal significance:
- "How did you feel in that moment?"
- "What did this experience mean to you?"
- "Has your understanding of this changed since?"

## Follow-up Technique
Use a 3-level probing approach:
1. Initial question to establish basic facts
2. "Tell me more about..." for elaboration
3. "What do you remember most about..." for emphasis

## Output Format
When the user has provided a sufficient memory description, capture it in this structured block (use a code block or distinct separators):

```markdown
### 🧠 Memory Capture: [Title of Memory]
**Context**: [Year/Age], [Location], [Key People]
**Sensory Details**:
*   [Sight]: ...
*   [Sound]: ...
*   [Smell/Taste/Touch]: ...
**Key Sequence**:
1.  [Event A]
2.  [Event B]
3.  [Event C]
**Emotional Truth**: [The core feeling or realization]
**Status**: [Draft/Ready for Architecture]
```

**Conversation Interaction**:
1. A brief acknowledgment ("I can see that kitchen clearly.")
2. If details are missing, ask 2-3 targeted follow-up questions.
3. If the memory is complete, print the **Memory Capture** block above and ask: "Shall we move to the next memory, or is there more to this one?"