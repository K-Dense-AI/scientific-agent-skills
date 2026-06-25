# Common ACT-R Model Patterns

This reference describes standard model patterns used across ACT-R cognitive models. Each pattern includes the key architectural features, representative chunk types, production structure, and critical parameters.

---

## 1. Memory Retrieval Models

### Canonical Example: Paired Associates Task

The participant learns associations (e.g., "2 -- BEAR") and must recall the paired word when cued with the number (Anderson, 2007, Ch. 5).

### Architecture

- **Declarative memory**: Stores paired-associate chunks
- **Goal buffer**: Tracks trial state (encoding, retrieval, response)
- **Visual module**: Reads stimulus from screen
- **Motor module**: Types response

### Key Chunk Types

```lisp
(chunk-type pair probe answer)
(chunk-type goal step probe answer)
```

### Production Skeleton

1. `read-probe` -- Attend to and encode the visual probe
2. `retrieve-answer` -- Request retrieval of the paired associate
3. `respond` -- Output the retrieved answer via motor module
4. `fail` -- Handle retrieval failure

### Critical Parameters

| Parameter | Role | Typical Value |
|-----------|------|---------------|
| d (decay) | Controls forgetting of pairs | **0.5** (Anderson & Schooler, 1991) |
| s (noise) | Variability in retrieval success | **0.2 -- 0.5** (Anderson, 2007) |
| tau (threshold) | Retrieval failure threshold | **-0.5 to 0.5** (set empirically) |
| S (mas) | Fan effect strength | **1.5 -- 3.0** (Anderson & Reder, 1999) |

### Behavioral Predictions

- **Power law of forgetting**: Accuracy decreases as a power function of lag (Anderson & Schooler, 1991)
- **Fan effect**: RT increases logarithmically with number of associations (Anderson & Reder, 1999)
- **Spacing effect**: Distributed practice produces slower forgetting (Pavlik & Anderson, 2005)

---

## 2. Skill Acquisition Models

### Canonical Example: Power Law of Practice

Models the transition from slow, deliberate processing to fast, automatic performance (Taatgen & Anderson, 2002; Newell & Rosenbloom, 1981).

### Architecture

- **Declarative memory**: Stores facts needed for initial performance
- **Procedural memory**: Productions that initially retrieve facts, then compile into direct rules
- **Production compilation**: Enabled (:epl t)

### Mechanism

1. **Interpretive phase**: Productions retrieve declarative knowledge to guide behavior
2. **Compilation**: Two sequential productions merge into one (Taatgen & Anderson, 2002)
3. **Tuning**: Compiled productions gain utility through reward learning

### Critical Parameters

| Parameter | Role | Typical Value |
|-----------|------|---------------|
| Production compilation | Must be enabled | :epl t (Taatgen & Anderson, 2002) |
| alpha (learning rate) | Speed of utility learning | **0.2** (Anderson, 2007) |
| Reward value | Goal reward for successful completion | **Task-dependent** |

### Behavioral Predictions

- **Power law of practice**: RT = a * N^(-b), where N is practice trials (Newell & Rosenbloom, 1981)
- **Qualitative shift**: Errors change from declarative-based to procedural-based with practice

---

## 3. Decision-Making Models

### Canonical Example: Instance-Based Learning

Models decisions based on accumulated experience with outcomes (Gonzalez et al., 2003).

### Architecture

- **Declarative memory**: Stores instances (situation-decision-outcome triples)
- **Blending**: Uses blended retrieval to aggregate over multiple instances (:blt t)
- **Utility learning**: Optional, for strategy selection

### Key Chunk Types

```lisp
(chunk-type instance
 situation ;; features of the current context
 decision ;; action taken
 outcome ;; result observed (e.g., reward value)
)
```

### Mechanism (Gonzalez et al., 2003)

1. Encode current situation
2. Retrieve (or blend) instances matching current situation
3. Evaluate expected outcomes for each possible decision
4. Select decision with highest expected value
5. Execute decision, observe outcome, store new instance

### Critical Parameters

| Parameter | Role | Typical Value |
|-----------|------|---------------|
| d (decay) | Recency weighting of instances | **0.5** (Anderson & Schooler, 1991) |
| s (noise) | Exploration vs. exploitation | **0.25 -- 1.0** (Gonzalez et al., 2003) |
| Blending | Aggregate over instances | :blt t (Lebiere, 1999) |

### Behavioral Predictions

- **Recency effect**: Recent outcomes influence decisions more than distant ones
- **Frequency effect**: More frequently experienced outcomes have higher base-level activation
- **Risk sensitivity**: Noise parameter s controls risk-seeking vs. risk-averse behavior

---

## 4. Problem Solving Models

### Canonical Example: Tower of Hanoi

Models multi-step problem solving with goal decomposition (Anderson, 2007, Ch. 8).

### Architecture

- **Goal buffer**: Tracks current goal and subgoals (stack-based)
- **Imaginal buffer**: Holds intermediate problem state representation
- **Declarative memory**: Stores known move patterns and strategies

### Production Structure

1. `set-goal` -- Identify the top-level goal
2. `decompose-problem` -- Push subgoal onto goal stack
3. `execute-move` -- Perform a primitive action
4. `pop-subgoal` -- Return to parent goal after completing subgoal
5. `check-done` -- Verify goal is achieved

### Critical Parameters

| Parameter | Role | Typical Value |
|-----------|------|---------------|
| Goal activation (G) | Strength of goal-directed retrieval | **1.0 -- 3.0** (Anderson, 2007) |
| Imaginal delay | Time for problem state updates | **200 ms** (Anderson, 2007) |

---

## 5. Cognitive Control / Conflict Models

### Canonical Example: Stroop Task

Models the conflict between automatic word reading and controlled color naming.

### Architecture

- **Visual module**: Encodes both color and word features
- **Procedural memory**: Competing productions for word-reading vs. color-naming
- **Utility-based selection**: Higher utility for task-relevant production

### Mechanism

1. Encode stimulus (color and word simultaneously)
2. Two productions compete: read-word (high utility from practice) vs. name-color (task-instructed)
3. Conflict resolved by utility + noise
4. Incongruent trials: competing retrieval or motor responses add time

### Critical Parameters

| Parameter | Role | Typical Value |
|-----------|------|---------------|
| Utility of word-reading | Reflects automaticity | Higher initial utility |
| Utility of color-naming | Reflects task instruction | Set by experimenter |
| sigma (utility noise) | Conflict resolution stochasticity | **0.5 -- 1.5** (Anderson, 2007) |

---

## References

- Anderson, J. R. (2007). *How Can the Human Mind Occur in the Physical Universe?* Oxford University Press.
- Anderson, J. R., & Reder, L. M. (1999). The fan effect: New results and new theories. *JEP: General*, 128(2), 186-197.
- Anderson, J. R., & Schooler, L. J. (1991). Reflections of the environment in memory. *Psychological Science*, 2(6), 396-408.
- Gonzalez, C., Lerch, J. F., & Lebiere, C. (2003). Instance-based learning in dynamic decision making. *Cognitive Science*, 27(4), 591-635.
- Lebiere, C. (1999). The dynamics of cognition: An ACT-R model of cognitive arithmetic. *Kognitionswissenschaft*, 8(1), 5-19.
- Newell, A., & Rosenbloom, P. S. (1981). Mechanisms of skill acquisition and the law of practice. In J. R. Anderson (Ed.), *Cognitive Skills and Their Acquisition*. Erlbaum.
- Pavlik, P. I., & Anderson, J. R. (2005). Practice and forgetting effects on vocabulary memory. *Cognitive Science*, 29(4), 559-586.
- Taatgen, N. A., & Anderson, J. R. (2002). Why do children learn to say "Broke"? *Cognition*, 86(2), 123-155.
