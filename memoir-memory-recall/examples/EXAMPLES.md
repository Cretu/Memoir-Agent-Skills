# Memory Recall Examples

## Example 1: Childhood Memory

**User Input**: "Tell me about your first day of school"

**Skill Response**:
Thank you for sharing. I'd like to explore this memory more deeply.

- Where exactly was the school building? What did it look like from the outside?
- What did you hear when you walked through the doors for the first time?
- Who was with you when you entered the classroom?
- What do you remember seeing on the walls or desks?
- How did your body feel? Were your hands sweaty? Did your stomach feel tight?

**Follow-up**:
- "Tell me more about the moment you said goodbye to your parents."
- "What was the first thing your teacher said?"

---

## Example 2: Travel Memory

**User Input**: "Describe your first trip abroad"

**Skill Response**:
I'd like to help you recall this experience in detail.

- What airport or station did you depart from?
- What was the first thing that felt different when you arrived?
- Who met you at your destination, or were you alone?
- What did you eat first in the new country?
- What was the weather like?

**Follow-up**:
- "What did you pack, and what do you wish you'd brought?"
- "Describe the moment you realized you were really far from home."

---

## Example 3: Relationship Memory

**User Input**: "Tell me about when we met"

**Skill Response**:
Let's explore this moment together.

- Where were you when you first saw them?
- What were you wearing? What were they wearing?
- What was the environment like—sounds, lighting, smells?
- What was the first thing they said to you?
- How did you know they were interested in talking?

**Follow-up**:
- "What did you talk about for the first hour?"
- "How did you feel when you said goodbye?"

---

## Example 4: Work Memory

**User Input**: "I got fired once"

**Skill Response**:
That sounds like a significant moment. Let's explore it carefully.

- Where did it happen—in an office, over the phone?
- Who told you? What was their expression?
- What did you say in response?
- What did you do immediately afterward?
- What was the ride home like?

**Follow-up**:
- "What did you do that night?"
- "How did you explain it to your family?"

---

---

## Example 5: Complete Session Cycle (Recall → Capture → Save)

This example shows how a full memory recall session ends, including the Memory Capture block and the confirmation-to-save step.

**User Input**: "I remember the morning my father taught me to fish."

**Skill Response** (after several rounds of deepening questions):

We have explored this memory well. Here is your Memory Capture:

```markdown
### 🧠 Memory Capture: First Fishing Morning
**Context**: Age 9, summer 1987, the creek behind Grandpa's farm, Father and me
**Sensory Details**:
*   [Sight]: Pre-dawn grey light, mist sitting low on the water, my father's red flannel shirt
*   [Sound]: The soft click of the reel, frogs still going, the line hitting the water
*   [Smell/Taste/Touch]: Worms from a tin can, cold rod handle, my fingers going numb
**Key Sequence**:
1.  Woke before sunrise, found Father already at the door with the gear
2.  Walked down the hill in the dark without a torch
3.  He baited my hook without speaking, handed it over
4.  First cast snagged a branch; he untangled it without irritation
5.  Second cast held — a long still wait — then the line pulled
**Emotional Truth**: He never explained anything, just showed me. At the time I thought he was impatient. Now I understand he was teaching me to pay attention.
**Status**: Ready for Architecture
```

Shall I save this to `memories/first-fishing-morning.md`?

**User**: Yes, save it.

**Skill**: Saved to `memories/first-fishing-morning.md`. Shall we explore another memory, or do you have enough material to move on to the **memoir-architect-biographer** skill (Architect)?

---

## Session Format

When conducting a memory recall session:

1. **Acknowledge** the memory the user shared
2. **Ask context questions** (where, when, who)
3. **Ask sensory questions** (see, hear, smell, feel)
4. **Ask narrative questions** (what happened next, before)
5. **Ask emotional questions** (how did it feel, why mattered)
6. **Summarize** as a Memory Capture block (not prose paragraphs)
7. **Confirm with the user** before saving to `memories/`
8. **Transition** — offer to recall another memory or move to Architect
