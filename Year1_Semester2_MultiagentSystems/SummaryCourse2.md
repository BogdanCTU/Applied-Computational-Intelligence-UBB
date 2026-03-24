# 🔖 **Course 2 - Introduction to Multiagent Systems**

## 🤖 1 - Agents
🔴 An **agent** is defined as a **computer system situated within an environment, capable of autonomous action to fulfill its design objectives**.
Agents continuously interact with their surroundings by receiving input through sensors and executing output via effectors or actions.
The fundamental concept underlying agency is 🔴 **autonomy**, **which is the ability of a system to control its internal state and behavior without human intervention**.

<img width="352" height="150" alt="image" src="https://github.com/user-attachments/assets/32b47034-1f29-4d64-8157-4eeacee001cb" />
> ### Image: Agentic Flow

- 💡 **Key Insight**: _Agents differ from traditional software programs because they operate autonomously and can intelligently delegate tasks_.

## ⚙️ 2 - Characteristics / Properties of agents
An agent’s architecture determines its behavior, mapping perceptions to actions via its internal program. Success is measured externally by a performance metric. Effective agents act autonomously and flexibly, responding to environmental changes while proactively pursuing goal directed behaviors.

- **Reactivity**: The capacity to perceive environmental conditions and respond appropriately to state changes.
- **Pro-activeness**: The ability to exhibit goal-directed behavior by taking initiative rather than strictly reacting to events.
- **Rationality**: The execution of optimal decisions that maximize a specific performance measure based on current knowledge.
- **Social Ability**: The capability to communicate and interact cooperatively with other agents or human users.
- **Key Insight**: Effective agents require a flexible architecture that balances reactive responses with proactive, rational goal execution.

## 🤖 3 - Intelligent agents
🔴 **An intelligent agent extends fundamental agency by incorporating an initial knowledge base and the vital capability of learning**.
This learning capability ensures true autonomy, allowing the agent to deduce and adapt its behavior based on empirical experience rather than relying solely on static, pre-programmed rules. Agents operating exclusively on initial knowledge risk losing flexibility and failing if their environment evolves unexpectedly.

Intelligent agents frequently utilize a utility function, mapping environment states to real numbers to quantify the degree of success.
The agent mathematically prefers and targets states yielding the maximum utility. **Techniques such as reinforcement learning are often employed to iteratively optimize this utility over time through environmental interaction**.

- 💡 **Key Insight**: _The integration of machine learning and utility functions enables agents to maintain autonomy and rationality in dynamic, unpredictable environments_.

## 🕵️‍♂️ 4 - Agent paradigm
The concept of agents operates as a transformative paradigm across both 💻 **Software Engineering** (_**SWE**_) and 🤖 **Artificial Intelligence** (_**AI**_):
- **Software Engineering Paradigm**: Utilizes software agents as a structural abstraction to automate tasks and manage system complexity through delegation;
- **Artificial Intelligence Paradigm**: Utilizes artificial agents as computational models of human intelligence and decision-making within **Distributed Artificial Intelligence** (_**DAI**_);
- 💡 **Key Insight**: Developing agent-based systems requires integrating intelligent decision-making within rigorous, foundational software engineering frameworks.

## 🌐 5 - Application areas
Agent technologies are applied in environments that require flexibility, autonomy and the ability to learn. They may function as single-agent systems with centralized control or as Multiagent Systems designed for decentralized contexts where data, control and expertise are distributed.
🔴 In **Multiagent Systems** (_**MAS**_), learning can occur through centralized training with decentralized execution, where agents learn together but act independently based on local information, or through fully decentralized learning, where each agent learns on its own. While this increases scalability, it can also lead to instability or inconsistent behavior among agents.

- **Single-agent Systems**: Characterized by centralized control and learning execution.
- **Multiagent Systems**: Ideal for domains requiring decentralized control, such as distributed healthcare or industrial process management.
- **Centralized Training / Decentralized Execution**: Agents leverage a shared learning model but operate autonomously in the environment.
- **Fully Decentralized Execution**: Highly scalable models where agents learn and act entirely independently, though susceptible to behavioral instability.
- 💡 **Key Insight**: Multiagent Systems provide essential decentralized architectures for environments where centralized control is either impossible or computationally inefficient.

## 🛠️ 6 - Application domains
Agents are software programs that act like independent workers. They are useful for handling complex tasks, especially when many systems or users are involved.

- **Distributed Systems**: Applications include air traffic control, smart factory automation and internet device cooperation;
- **E-Business and Profiling**: Utilizing clustering and behavioral data mining to segment customers and drive recommender systems;
- **Mobile Agents**: Network-bound entities that migrate between hosts to execute code locally, conserving bandwidth and reducing latency;
- **Human-Computer Interaction**: Intelligent interfaces and personal digital assistants that adapt to user behavior through active observation;
- 💡 **Key Insight**: By operating directly at the data source or adapting to user inputs, agents optimize both network efficiency and human-computer workflows.

## 🤖 7 - Agents vs. existing paradigms
🔴 **Agents differ from traditional software and Object-Oriented constructs by being autonomous, proactive and adaptive**.
Unlike standard procedures or objects, which are passive and dependent on external invocation, agents encapsulate both state and behavior, possess their own continuous control thread and determine how to respond based on internal goals. They are smart active entities capable of reasoning and acting independently in dynamic environments, unlike Expert Systems that rely on user input.

- **Autonomy of Behavior**: Agents control the execution of their own methods, whereas standard objects are controlled by the invoking entity.
- **Active Execution**: Agents maintain persistent threads of control, enabling continuous environmental interaction compared to passive objects.
- **Environmental Situation**: Unlike traditional Expert Systems, agents are actively situated in and act upon an external environment rather than acting merely as static advisory databases.
- 💡 **Key Insight**: Agents elevate traditional object-oriented and symbolic artificial intelligence models by integrating state encapsulation with independent, active decision-making.

## 💻 8 - Comparison of two software paradigms
🔴 **Conventional software is hierarchical, centralized and data-driven, executing pre-programmed behaviors for predictable outcomes**.
🔴 **Multiagent Systems (_MAS_), (inspired by biological swarms) are decentralized and knowledge-driven, with numerous small agents interacting to produce complex, emergent behavior**.

- **Conventional Software**: Relies on centralized hierarchies, data-driven logic, and rigid, pre-programmed behaviors.
- **Multiagent Software**: Utilizes distributed networks, knowledge-driven operations, and generates emergent system behaviors.
- **Swarm Intelligence**: Employs parallel, specialized agents to collaboratively solve complex tasks without centralized leadership.
- 💡 **Key Insight**: Multiagent paradigms shift system design from rigid, top-down control to flexible, decentralized networks capable of emergent problem-solving.

<img width="866" height="731" alt="image" src="https://github.com/user-attachments/assets/74ba044b-6a17-4710-b061-38f98bf892c2" />
> ### Image: Comparison of two software paradigms

## 🖥️ 9 - Agent oriented software engineering (AOSE)
**Agent-Oriented Software Engineering** (_**AOSE**_) provides methodologies to model, design and build complex systems by decomposing them into autonomous agents, abstracting system architectures and organizing agents like human organizations. In AOSE, system components correspond to agent organizations and individuals, with explicit interaction mechanisms enabling cooperation, coordination, and conflict resolution to achieve system goals.

- **Decomposition**: Structuring software into decentralized components featuring persistent, independent threads of control.
- **Abstraction**: Leveraging the agent paradigm to simplify the conceptualization and visualization of complex systems.
- **Organization**: Establishing formal structures and relationships among agents to manage complex workflows.
- **Interaction** Mechanisms: Utilizing communication and negotiation protocols rather than basic programmatic calls to manage subsystem relationships.
- 💡 **Key Insight**: Agent-Oriented Software Engineering provides the necessary abstraction and organizational frameworks to engineer complex systems as collaborative societies of autonomous software entities.
