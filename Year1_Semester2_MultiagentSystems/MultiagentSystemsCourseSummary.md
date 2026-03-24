<!-- --------------------------------------------------------------- -->
<!-- -------------------- COURSE 1 INTRODUCTION -------------------- -->
<!-- --------------------------------------------------------------- -->

# 🔖 **Course 1 - Introduction to Multiagent Systems**

## 📖 1 - Introduction
<span style="color:red">🔴**Artificial Intelligence**</span> (_**AI**_) encompasses both symbolic representations, such as logic and expert systems and computational intelligence, which relies on numerical knowledge representations like machine learning and fuzzy systems.
Within this spectrum, the agent paradigm serves as a computational model of human behavior, characterized by autonomy, reactivity, proactivity and communication.
These agents are transforming productivity across diverse fields, evolving from tools that automate repetitive tasks into advanced autonomous systems.
This evolution has led to the rise of **Agentic AI**, where autonomous systems powered by Large Language Models (_**LLM**_) **independently plan, reason and execute complex workflows with minimal human supervision**.

<span style="color:red">🔴**Distributed Artificial Intelligence**</span> (_**DAI**_), established between 1975 and 1980, shifts the focus from centralized, monolithic intelligence to decentralized problem-solving. It removes the requirement for data to reside in a single location.
<span style="color:red">**Multiagent Systems act as the primary paradigm of Distributed Artificial Intelligence**</span>, modeling a society of interacting agents working concurrently.

- ⚙️ Major application domains for artificial intelligence agents include medicine, educational data mining, search-based software engineering, e-business, computer vision and bioinformatics;
- 🤖 Agentic AI distinguishes itself from standard artificial intelligence agents through its focus on complex concurrency, coordination and independent goal execution without direct human triggering/supervision.

## 📖 2 - DAI and agents
Distributed Artificial Intelligence is an interdisciplinary field integrating artificial intelligence, software engineering, sociology, economics and game theory to study and build Multiagent Systems.
🔴 **An agent is a computational entity that perceives its environment through sensors and acts upon it through effectors autonomously**. This abstraction applies universally, whether the agent is a human using sensory organs and muscles, a physical robot utilizing cameras and motors or a software agent processing bit strings to deliver data outputs.

<img width="330" height="138" alt="image" src="https://github.com/user-attachments/assets/65277d00-58a6-4681-8e7d-6822f425e64f" />

> ### Image: [educba](https://www.educba.com/agents-in-artificial-intelligence/)

Research in Distributed Artificial Intelligence is traditionally divided into two primary directions:
- 🤖 **Multiagent Systems** (_**MAS**_): focus on how independent agents coordinate their knowledge, communicate and reason about their social interactions within a shared environment;
- 📑 **Distributed Problem Solving** (_**DPS**_): divides a specific problem among multiple nodes that share knowledge to accelerate the solution process.
Modern Distributed Problem Solving encompasses distributed planning, search and sophisticated distributed machine learning techniques designed to handle massive datasets and reduce training times.

Agent manifestations based on sensory and actuation mechanisms:
  - _Human agents utilize eyes and ears for sensors and hands or vocal cords for effectors_;
  - _Robotic agents utilize infrared or cameras for sensors and grippers or wheels for effectors_;
  - _Software agents utilize encoded input strings for sensors and computational outputs for effectors_.

Distributed Machine Learning architectures:
  - 🔴 **Data Parallelism** replicates the model across nodes and slices the data across processing units, representing the most widely adopted approach;
  - 🔴 **Model Parallelism** splits a single large model into different independent segments across nodes to accelerate training for complex architectures;
  - 🔴 **Federated Learning** enables multiple entities to collaboratively train a shared model without exchanging their localized raw data.

## 📖 3 - DAI vs AI
The fundamental distinction between traditional **Artificial Intelligence** (_**AI**_) and **Distributed Artificial Intelligence** (_**DAI**_) lies in their perspective on intelligence and interaction. The long-term objective of Distributed Artificial Intelligence is to develop mechanisms that enable seamless interaction among computational entities and humans, addressing the critical challenge of determining when, how and with whom to interact.
While both fields address the computational aspects of intelligence, Distributed Artificial Intelligence serves as a broader generalization of traditional paradigms that shifts focus from the individual to the collective.

- 💾 **Traditional Artificial Intelligence** **concentrates on isolated cognitive processes within individuals**, viewing intelligence as a property of a standalone disconnected system;
- 📚 **Distributed Artificial Intelligence** **focuses on social processes within groups**, treating intelligence as an emergent property of connected systems that actively interact, negotiate and collaborate.


<!-- --------------------------------------------------------------- -->
<!-- -------------------- COURSE 2 APPLICATIONS -------------------- -->
<!-- --------------------------------------------------------------- -->

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

