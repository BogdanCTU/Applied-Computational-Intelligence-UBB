# 🔖 **Course 5 - Multiagent Systems Characteristics**

## 📖 5.1 - Multiagent Systems

A 🔴 **Multiagent System** (_**MAS**_) **is a network of separate computer programs called agents**.
**These agents connect and interact with one another**. A MAS spreads out computer power and skills across this network. A MAS is 🔴 **decentralized**, meaning no single central computer is in control.
🔴 **The agents must be able to work together**. To do this successfully, agents must **cooperate**, **coordinate** and **negotiate**, just like people do.

### 📑 5.1.1 MAS Challanges

Multiagent systems (MAS) revolve around three core challenges: **communication**, **collaboration** and **coordination**. Agents must exchange knowledge, intentions, and beliefs, collaborate through negotiation (often among self-interested entities) and ensure coordinated, controlled behavior within a shared environment.

🔴 **Collaborative agents are designed to operate autonomously** while cooperating to fulfill user-defined tasks. They are capable of rational decision-making and may incorporate learning mechanisms to improve performance over time.

<img width="484" height="218" alt="image" src="https://github.com/user-attachments/assets/31526138-019e-4799-85ce-750a2125c528" />

> ### Image: Collaborative Agents

Effective **inter-agent cooperation** is achieved through structured mechanisms such as grouping, communication, specialization, resource and task sharing, coordinated actions, and conflict resolution via arbitration or negotiation. These mechanisms enable agents to function collectively despite differing objectives.

### 📑 5.1.2 MAS Organizations

🔴 **MAS organizations define how agents are structured and interact**. They are composed of agent classes assigned specific roles and connected through relationships such as acquaintance, subordination and conflict.

Organizational design can follow multiple approaches:
- **Horizontal Modular Design**: components are functionally separated (e.g., [Prodigy](https://www.researchgate.net/publication/234783121_PRODIGY_An_integrated_architecture_for_planning_and_learning), [ICARUS](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.295.9054&rep=rep1&type=pdf));
- **Hierarchical Vertical Structures**: Bio-inspired models such as ant colonies or immune systems, often leveraging simple interaction rules and reinforcement learning.

At a higher level, MAS adopt organizational paradigms like hierarchies, holarchies, teams, coalitions and markets to model complex systems. Frameworks such as [MOISE](https://moise.sourceforge.net/) support organization-oriented programming, emphasizing role-based design where entities, roles, and activities are clearly defined.

### 📑 5.1.3 MAS Design

🔴 **MAS design involves two fundamental problems**:
- **Agent design** (**micro level**): building autonomous agents capable of independent action;
- **Society design** (**macro level**): enabling effective interaction through cooperation, coordination and negotiation.

### 📑 5.1.4 MAS Advantages

Advantages of a MAS:
- **Decentralized**: does not suffer from the _single point of failure problem_ associated withcentralized systems;
- **Efficiency**: Provides solutions in situations where data sources and expertise are spatially and/or temporallydistributed:
  - Classical View: Data is distributed;
  - Another View: Data is not distributed but multiple agents are used for increasing performance;
- **Performance**: offers computational efficiency, robustness, maintainability and flexibility.

## 📖 5.2 - MAS Characteristics

🔴 **A Multiagent System relies on a robust computational infrastructure to enable autonomous-distributed agents to interact**. Agents operate based on explicit knowledge and use specific protocols to communicate, cooperate, or negotiate to achieve individual or system-wide goals. Communication within these systems generally falls into two architectures: indirect communication via Blackboard Systems or Direct Message Passing using standardized agent languages.

### 📑 5.2.1 MAS Environment Characteristics

The MAS environment provides the necessary foundation for agents to function and interact:
- **Infrastructure:** It specifies and provides the communication and interaction protocols;
- **Protocols:**
    - **Communication Protocols:** Allow agents to exchange and understand basic messages (e.g., _proposing_, _accepting_, or _rejecting_ an action);
    - **Interaction Protocols:** Enable agents to string messages together into meaningful conversations;
* **Agent Nature:** The environment is populated by distributed and autonomous agents, which can be either self-interested or cooperative.

### 📑 5.2.2 The Agent Profile

Fundamentally, an agent is an active object that can **reason**, **perceive** and **act**:
- **Knowledge & Reasoning:** Agents possess explicitly represented knowledge and the internal mechanisms to operate on it and draw inferences;
- **Communication as Action:**
  - _Perception_ includes receiving messages;
  - _Action_ includes sending messages.

### 📑 5.2.3 Coordination, Cooperation and Negotiation

Agents communicate primarily to better achieve their own goals or the goals of the broader system:
* **Coordination:** A general property of a system where agents perform activities in a shared environment;
* **Cooperation:** Coordination specifically between _non-antagonistic_ (friendly/aligned) agents;
* **Negotiation:** Coordination specifically among _competitive_ or _self-interested_ agents.

### 📑 5.2.4 Communication Options in MAS

Agents need structured ways to share information, there area two main known approaches:

#### **Blackboard Systems**

A shared memory or data repository where agents interact _indirectly_. The blackboard holds data, problem states, requests for help, intermediate results and current agent tasks.

* **Advanced Features:** Uses a "moderator" or "dispatcher" agent. Agents register with the dispatcher, which notifies them of relevant changes so they don't have to constantly check the blackboard themselves;
* **Pros:** Highly flexible mechanism, allows for the use of multiple ($n$) blackboards;
* **Cons:** Centralized structure creates a single point of failure and a potential bottleneck, as everyone must read/write to the same place.

#### **Direct Message Passing**

Agents communicate directly using specialized **Agent Communication Languages** (_ACLs_).

* **FIPA-ACL**: Developed by FIPA and implemented in the JADE framework. Uses specific communication protocols, message components and "performatives";
* **Knowledge Query and Manipulation Language (KQML)**: **Knowledge Query and Manipulation Language**. A protocol for exchanging information between agents and applications, utilizing Lisp-like performatives;
* **Knowledge Interchange Format (KIF)**: A logic language used to describe things declaratively within expert systems. It acts as a means for encoding knowledge, functioning as a prefix version of first-order logic extended to handle nonmonotonic reasoning.

## 📖 5.3 - A Dynamic MAS

🔴 **A MAS is considered dynamic when it changes over time**. A dynamic MAS model relies on a few key assumptions. It usually consists of two or more agents ($n \ge 2$). The environment operates with strict, predictable rules and the agents act non-cooperatively, meaning each agent only pursues its own selfish objectives. The system starts at a time of zero and moves forward in steps until a specific stopping condition is met. At the end, the agents look at the final state of the system to evaluate their success.

This dynamic system is formally described using a mathematical tuple: $<S, \mathcal{A}, h, U>$.
- $S$ represents the joint state space, which is the combined situation of all agents;
- $\mathcal{A}$ represents the joint action space, which includes all the possible moves the agents can make;
- $h$ represents the transition function, which calculates how the state changes when agents take action;
- $U$ represents a vector of utility functions, which measure how beneficial the outcome is for each respective agent.

The process works in a loop. At each time step ($t$), the agents observe the current state ($s_t$). Next, each agent chooses an action ($a_t^i$). The entire system then evolves into a new state based on those combined actions ($s_{t+1} = h(s_t, a_t)$). When the state changes, an agent's utility might improve. This measurable improvement is defined as a reward ($r_t^i$). Ultimately, an agent's goal is to maximize the utility of its final state, which is the exact same as maximizing the total sum of all the rewards it receives over time.

