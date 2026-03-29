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

**A MAS needs an environment that gives agents a digital infrastructure to interact**, in order to function properly. This environment provides specific rules, called **protocols**.
Communication protocols let agents send and understand messages. For example, an agent might propose a course of action, and another might reject it. Interaction protocols allow agents to have ongoing conversations. In this environment, an agent is an active object that has the ability to reason, perceive its surroundings, and take action.

# CONTINUE HERE
# CONTINUE HERE
# CONTINUE HERE

## 📖 5.3 - A Dynamic MAS

🔴 **A MAS is considered dynamic when it changes over time**. A dynamic MAS model relies on a few key assumptions. It usually consists of two or more agents ($n \ge 2$). The environment operates with strict, predictable rules and the agents act non-cooperatively, meaning each agent only pursues its own selfish objectives. The system starts at a time of zero and moves forward in steps until a specific stopping condition is met. At the end, the agents look at the final state of the system to evaluate their success.

This dynamic system is formally described using a mathematical tuple: $<S, \mathcal{A}, h, U>$.
- $S$ represents the joint state space, which is the combined situation of all agents;
- $\mathcal{A}$ represents the joint action space, which includes all the possible moves the agents can make;
- $h$ represents the transition function, which calculates how the state changes when agents take action;
- $U$ represents a vector of utility functions, which measure how beneficial the outcome is for each respective agent.

The process works in a loop. At each time step ($t$), the agents observe the current state ($s_t$). Next, each agent chooses an action ($a_t^i$). The entire system then evolves into a new state based on those combined actions ($s_{t+1} = h(s_t, a_t)$). When the state changes, an agent's utility might improve. This measurable improvement is defined as a reward ($r_t^i$). Ultimately, an agent's goal is to maximize the utility of its final state, which is the exact same as maximizing the total sum of all the rewards it receives over time.

