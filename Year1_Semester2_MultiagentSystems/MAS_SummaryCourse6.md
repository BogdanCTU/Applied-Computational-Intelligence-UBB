<!-- --------------------------------------------------------------- -->
<!-- ------------------------ COURSE 6 AGENT ----------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 6 - Agent Strategy and Design**

## 📖 1 - Agent Strategy
## Lecture 6 Summary: Agent Strategy and Design

### 1. Agent Strategy
An **Agent Strategy** is a mapping that decides which action to take based on a **Percept Sequence** (the complete history of everything the agent has perceived).

* **Performance Measure (PM):** An objective metric used to judge the success of an agent's behavior (e.g., amount of dirt cleaned, energy used).
* **Rationality:** An **Ideal Rational Agent** selects the action expected to maximize its PM based on its percept history and built-in knowledge.

---

### 2. Agent Function Implementation
Agents are categorized by their complexity, moving from **Reactive** (responding to the present) to **Deliberative** (thinking about the future).

#### 2.1 Table-Driven Agent (Reactive)
* **Definition:** Uses a lookup table containing a specific action for every possible percept sequence.
* **Drawbacks:** Tables become impossibly large (e.g., Chess has $35^{100}$ entries); no autonomy or adaptability.
* **Optimization:** Tables can be avoided using **Markov Environments** (where only the current state matters) or by dynamically computing actions.

#### 2.2 Simple Reflex Agent (Reactive)
* **Definition:** Acts based only on the current percept, ignoring history.
* **Condition-Action Rules:** Written as "If [condition] then [action]" (e.g., If car-in-front-is-braking then initiate-braking).
* **Limitation:** Only works if the environment is **Fully Observable** (the agent can see everything it needs at that moment).

#### 2.3 Model-Based Reflex Agent (Reactive)
* **Definition:** Maintains an **Internal State** (a "model" of the world) to track aspects of the environment that cannot be seen currently.
* **Purpose:** Handles **Partially Observable** environments by remembering the past.
* **Technical Tool:** Often implemented using **Finite-State Machines (FSM)**, where the agent transitions between a finite number of states based on inputs.



#### 2.4 Goal-Based Agent (Deliberative)
* **Definition:** Acts to achieve specific **Goals** (descriptions of desirable situations).
* **Methodology:** Uses **Search and Planning** to predict how actions will affect the future.
* **Benefit:** More flexible than reflex agents; if the goal changes (e.g., a new destination), the agent adapts without needing new rules.

#### 2.5 Utility-Based Agent (Deliberative)
* **Definition:** Uses a **Utility Function** to map a state to a real number representing "happiness" or desirability.
* **Methodology:** Uses **Decision Theory** to choose actions that maximize *expected* utility.
* **Distinction:** While a goal-based agent only cares about *reaching* the destination, a utility-based agent cares about the *quality* of the path (e.g., speed, safety, comfort).

#### 2.6 Learning Agent
* **Definition:** An agent capable of improving its performance over time.
* **Components:** Includes a **Learning Element** (to make improvements), a **Critic** (to provide feedback), and a **Performance Element** (to select actions).

---

### 3. Agent-Based Systems Design

#### Multi-Agent System (MAS) Simulation
To run a MAS, the system must ensure **Concurrent Execution** (agents running at the same time, usually in their own threads).

```python
def run_simulation(state, update_function, agents, termination_condition):
    """
    Executes a multi-agent simulation loop.
    """
    while not termination_condition(state):
        # Collect inputs for all agents simultaneously
        for agent in agents:
            percepts[agent] = get_percept(agent, state)
        
        # Each agent decides on an action based on its program
        for agent in agents:
            actions[agent] = agent.program(percepts[agent])
            
        # Apply all actions to the environment at once
        state = update_function(actions, agents, state)
```

#### Object-Oriented (OO) Design: PAGE(S)
When designing agents as objects, the primary components are:
* **Agent:** The entity selecting actions.
* **Environment:** The external world the agent lives in.
* **State:** The current configuration of the environment.
* **Percept:** The specific data the agent receives from the state.
* **Action:** The output/movement the agent performs.

#### Communication Models
1.  **Blackboard:** A shared data repository where agents read and write information indirectly.
2.  **Message Passing:** Agents send direct messages to one another, often using **ACL (Agent Communication Language)**.

#### Development Steps
1.  **Define the Model:** Identify agent types, roles, and knowledge rules (**Ontology**).
2.  **Select Framework:** Choose a platform (like JADE).
3.  **Implement:** Build the agents, their communication protocols, and the solution logic.
