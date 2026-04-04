<!-- --------------------------------------------------------------- -->
<!-- ------------------------ COURSE 6 AGENT ----------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 6 - Agent Strategy and Design**

## 📖 6.1 - Agent Strategy

An 🔴 **Agent Strategy** is a mapping that decides which action to take based on a **Percept Sequence** (the complete history of everything the agent has perceived):
* **Performance Measure (PM):** An objective metric used to judge the success of an agent's behavior (e.g., amount of dirt cleaned, energy used);
* **Rationality:** An **Ideal Rational Agent** selects the action expected to maximize its PM based on its percept history and built-in knowledge.

---

## 📖 6.2 - Agent Function Implementation

Agents are categorized by their complexity, moving from **Reactive** (responding to the present) to **Deliberative** (thinking about the future).

### 📑 6.2.1 Table-Driven Agent (Reactive)
* **Definition:** Uses a lookup table containing a specific action for every possible percept sequence;
* **Drawbacks:** Tables become impossibly large (e.g., Chess has $35^{100}$ entries); no autonomy or adaptability;
* **Optimization:** Tables can be avoided using **Markov Environments** (where only the current state matters) or by dynamically computing actions.

<img width="346" height="218" alt="image" src="https://github.com/user-attachments/assets/fa0d5f7c-2f02-4ea3-962a-1402546c1052" />

> ##### Image: Table-Driven Agent Sample

### 📑 6.2.2 Simple Reflex Agent (Reactive)
* **Definition:** Acts based only on the current percept, ignoring history;
* **Condition-Action Rules:** Written as "If [condition] then [action]" (if car-in-front-is-braking then initiate-braking);
* **Limitation:** Only works if the environment is **Fully Observable** (the agent can see everything it needs at that moment).

<img width="546" height="228" alt="image" src="https://github.com/user-attachments/assets/f4a0c48a-0361-4567-9fed-cbd12303e20d" />

> ##### Image: Simple Reflex Agent Sample

### 📑 6.2.3 Model-Based Reflex Agent (Reactive)
* **Definition:** Maintains an **Internal State** (a "model" of the world) to track aspects of the environment that cannot be seen currently;
* **Purpose:** Handles **Partially Observable** environments by remembering the past;
* **Technical Tool:** Often implemented using **Finite-State Machines (FSM)**, where the agent transitions between a finite number of states based on inputs.

_Note_: 🔴 A **Finite-State Machine** (**FSM**), also called a **Finite-State Automaton**, is a conceptual model used to design step-by-step logic. It behaves very much like a model-based reflex agent because it keeps track of its current situation to decide what to do next. The FSM looks at its current State and the new Input. It then follows a set rule to perform a Transition to a new state. This process often triggers a specific action in the real world.

Core definitions:
* **State**: A specific condition the machine is in. An FSM can only be in exactly one state at any given time, chosen from a limited (finite) list of options;
* **Input**: A signal, event, or piece of data received from the outside world;
* **Transition**: The act of changing from one state to another state. This change is always triggered by a specific input.

_Brief Example_: Think of a standard traffic light.
* _States_: The system can only be in one of three states: Green, Yellow, or Red;
* _Input_: A built-in timer counts down to zero;
* _Transition_: If the current state is Green, and the timer input reaches zero, the FSM transitions to the Yellow state.

<img width="820" height="423" alt="image" src="https://github.com/user-attachments/assets/5cbcd9fe-d249-4534-9175-55fc6d9c958b" />

> ##### Image: Model-Based Reflex Agent Sample

### 📑 6.2.4 Goal-Based Agent (Deliberative)
* **Definition:** Acts to achieve specific **Goals** (descriptions of desirable situations);
* **Methodology:** Uses **Search and Planning** to predict how actions will affect the future;
* **Benefit:** More flexible than reflex agents; if the goal changes (e.g., a new destination), the agent adapts without needing new rules.

<img width="819" height="423" alt="image" src="https://github.com/user-attachments/assets/c5917acd-80b2-4bcd-b30b-c44e0a5cc163" />

> ##### Image: Goal-Based Agent Sample

### 📑 6.2.5 Utility-Based Agent (Deliberative)
* **Definition:** Uses a **Utility Function** to map a state to a real number representing "happiness" or desirability;
* **Methodology:** Uses **Decision Theory** to choose actions that maximize *expected* utility;
* **Distinction:** While a goal-based agent only cares about *reaching* the destination, a utility-based agent cares about the *quality* of the path (e.g., speed, safety, comfort).

<img width="766" height="511" alt="image" src="https://github.com/user-attachments/assets/30e0a650-948e-44f5-92c2-8aee8d990d3f" />

> ##### Image: Utility-Based Agent Sample

### 📑 6.2.6 Learning Agent
* **Definition:** An agent capable of improving its performance over time;
* **Components:** Includes a **Learning Element** (to make improvements), a **Critic** (to provide feedback) and a **Performance Element** (to select actions).

<img width="910" height="559" alt="image" src="https://github.com/user-attachments/assets/34dfc2a8-592d-43b5-965b-f8f92aeb6815" />

> ##### Image: Learning Agent Sample

---

### 📑 6.3.3. Agent-Based Systems Design

**Multi-Agent System (MAS) Design** focuses on how multiple intelligent entities interact with their environment and each other.

**Core Concepts:**
* **Concurrent Execution:** Agents must operate in parallel. Each agent requires its own independent thread of control. The processes of perceiving the environment and deciding on actions happen simultaneously for all agents, not sequentially;
* **Agent Program:** The specific logic an agent uses to map a received percept to a chosen action. This program determines the complexity of the agent (ranging from simple reactive responses to complex deliberative planning);
* **Internal Memory:** Agents can maintain a static memory model of the current environment state. This memory is updated dynamically as new percepts are received or actions are performed;
* **Extended Components:** **Learning Agents** require components beyond the standard action-selection program. These include a learning element, a critic and a problem generator;
* **Performance Evaluation:** Simulators can track an objective score conceptually outside the agent to evaluate its success over time.

**System Simulation Implementations:**

```python
class MultiAgentSimulator:
    """
    Provides simulation environments for multi-agent systems.
    """

    def run_simulation(self, initial_state, update_fn, agents, termination_condition):
        """
        Executes a basic multi-agent simulation loop.
        Agents process percepts and determine actions concurrently.
        The environment state updates based on the collective actions.
        """
        state = initial_state
        
        while not termination_condition(state):
            percepts = {}
            for agent in agents:
                percepts[agent] = agent.get_percept(state)
                
            actions = {}
            for agent in agents:
                actions[agent] = agent.program(percepts[agent])
                
            state = update_fn(actions, agents, state)

    def run_eval_simulation(self, initial_state, update_fn, agents, termination_condition, performance_fn):
        """
        Executes a multi-agent simulation loop that includes continuous performance tracking.
        Returns the final evaluated scores for all agents upon termination.
        """
        state = initial_state
        scores = {agent: 0 for agent in agents}
        
        while not termination_condition(state):
            percepts = {}
            for agent in agents:
                percepts[agent] = agent.get_percept(state)
                
            actions = {}
            for agent in agents:
                actions[agent] = agent.program(percepts[agent])
                
            state = update_fn(actions, agents, state)
            scores = performance_fn(scores, agents, state)
            
        return scores
```

---

### 📑 6.4 Object-Oriented (OO) Design: PAGE(S)
When designing agents as objects, the primary components are:
* **Agent:** The entity selecting actions;
* **Environment:** The external world the agent lives in;
* **State:** The current configuration of the environment;
* **Percept:** The specific data the agent receives from the state;
* **Action:** The output/movement the agent performs.

### 📑 6.4.1 Communication Models
1.  🔴 **Blackboard:** A shared data repository where agents read and write information indirectly;
2.  🔴 **Message Passing:** Agents send direct messages to one another, often using **ACL (Agent Communication Language)**.
 
### 📑 6.4.1 Development Steps
1.  **Define the Model:** Identify agent types, roles and knowledge rules (**Ontology**);
2.  **Select Framework:** Choose a platform (like **JADE for Java** or **SPADE for Pyhton**);
3.  **Implement:** Build the agents, their communication protocols, and the solution logic.
