# 🔖 Course 3 - Agent Design, Environments and Architectures

## 📖 3.1 - Methodologies for agent-based systems development
The development of agent-based systems can leverage both classical **Software Engineering** methodologies and specialized **Agent-Oriented** approaches.
Classical software engineering relies on sequential processes, such as the **Waterfall Model** and **Model-Driven Development** (_**MDD**_), as well as iterative Agile frameworks like **Test-Driven Development** (_**TDD**_) and **Behavior-Driven Development** (_**BDD**_).

- **Classical Methodologies**: Includes sequential Waterfall projects, Agile MDD, and iterative testing frameworks like TDD and BDD;
- **Agent-Oriented Methodologies**: Includes Gaia, which focuses heavily on organizational abstraction, and Multiagent Software Engineering (MaSE).

## 📖 3.2 - Agent-based development lifecycle
In a sequential agent-based lifecycle, the specification phase defines system inputs, outputs, agent types and communication protocols using languages like **Cognitive Agent Specification Language** (_**CASL**_) and **AgentSpeak**. The design phase employs **Agent Unified Modelling Language** (_**AUML**_) developed by _**FIPA**_ to model agent architectures, communication networks (via **Agent Communication Language** (_**ACL**_)) and coordination strategies.
Implementation follows the **Agent-Oriented Programming** (_**AOP**_) paradigm, defining agents by their capabilities, initial beliefs and commitments.

Lifecycle Stages:
- **Specification**: Utilizes formal languages like CASL, AgentSpeak and SLABS to define agent inputs, outputs and tasks;
- **Design**: Involves conceptual modeling with Agent Unified Modeling Language (AUML) and defining communications using FIPA's Agent Communication Language (ACL);
- **Implementation**: Employs Agent-Oriented Programming (AOP) principles, concurrent logic or multiparadigm languages (such as Java or Python) through frameworks like JADE and SPADE;
- **Testing**: Includes both unit and automated testing protocols to ensure system reliability.
- 💡 **Key Insight**: The agent-based lifecycle mirrors traditional software engineering but requires specialized modeling languages (AUML) and execution frameworks to handle autonomous behaviors and agent communication.

## 📖 3.3 - Agent design PAGE
🔴 The conceptual design of an agent requires a clear abstraction of its operational parameters, most commonly represented by the **PAGE** model, which stands for **Perception, Action, Goal and Environment**. Conceptually, the environment represents the total set of possible environment states, often expanded to **PAGE(S)** that **include this state configuration**.

🔴 **PAGE Model Components**:
- **Perception**: The inputs the agent receives, such as a sensor detecting dirt or a camera interpreting pixels;
- **Action**: The capabilities of the agent, such as turning, moving, or printing categorizations;
- **Goal**: The objective the agent is designed to achieve, such as minimizing power, maximizing purity, or finding a person's email address;
- **Environment**: The external conditions, such as a grid room, a refinery, or the Internet, including its current state.

<img width="623" height="429" alt="image" src="https://github.com/user-attachments/assets/bcbf4992-a3ea-4cd4-9fbc-36247746ac51" />
<img width="858" height="224" alt="image" src="https://github.com/user-attachments/assets/55884630-85cc-446f-8b22-a0099b59c060" />

> ### Image: _Sample of agents in different types of applications_

## 📖 3.4 - Environment
An agent’s environment—physical or virtual—defines its interaction boundaries and influences system complexity.
Agent-environment interactions can be specified using the **PEAS** model: **Performance measure, Environment, Actuators and Sensors**.
Environments are further classified mathematically across divisions/areas that shape agent reasoning and behavior.

Key Environmental Properties:
- **Accessible vs. Inaccessible**: An accessible environment provides complete, accurate, and up-to-date state information, making agent design simpler; most real-world environments are inaccessible;
- **Deterministic vs. Non-deterministic**: In deterministic settings, actions have guaranteed outcomes, whereas non-deterministic settings require probability distributions to account for stochastic uncertainty;
- **Episodic vs. Sequential (Non-episodic)**: In episodic settings, an agent's performance depends only on discrete, isolated events; in sequential settings, current actions have long-term consequences requiring planning;
- **Static vs. Dynamic**: Static environments only change when the agent acts, while dynamic environments feature independent external processes that change conditions beyond the agent's control;
- **Discrete vs. Continuous**: Defines whether the environment contains a finite, fixed number of actions and percepts or a continuous spectrum;
- **Markovian vs. Non-Markovian**: A Markovian environment follows the Markov property, where future state predictions depend solely on the current state and action, independent of historical data.

## 📖 3.5 - Abstract architectures for agents
Abstract architectures formalize the mathematical view of agents interacting with environment states. An environment exists as a set of states ($S=\{s_{1},s_{2},...\}$), and the agent possesses a set of actions ($A=\{a_{1},a_{2},...\}$). Abstractly, an agent is a function that maps a sequence of environment states to a specific action. The environment's behavior is non-deterministic, modeled as a function mapping the current state and action to a set of possible resulting states. This continuous interaction forms a characteristic behavior represented as a sequence or history of states and actions over time.

Agent architectures can be divided into purely reactive systems and state-based systems. Purely reactive agents make decisions based entirely on the present state without referencing past history, utilizing an action function that directly maps a state to an action. More complex state-based agents possess an internal state that is continuously updated; their architecture splits into a perception subsystem mapping environment states to percepts, a state-update function, and an action function mapping the internal state to the final action.

Architectural Variations:
- **Purely Reactive Agents**: Base actions strictly on the current state with no internal history. An example is a thermostat turning a heater on or off based solely on the current temperature;
- **State-Based Agents**: Maintain an internal memory state to process interactions.
- **Execution Cycle (State-Based)**: The agent observes the environment to generate a percept, updates its internal state based on that percept, selects an action derived from the new state, and executes the action before repeating the cycle.
