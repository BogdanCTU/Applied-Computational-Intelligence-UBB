# 🔖 Course 3 - LECTURE 4

## 📖 3.1 - Concrete Architectures for Agents

Concrete architectures define the practical methodologies used to construct autonomous agents, translating abstract agent models into implementable systems:
- 🔴 **Abstract Architecture**: **abstract/formal view of agents and their interaction with the environment**;
- 🔴 **Concrete Architecture**: **concrete architectures focus on decomposition into modular components**, the interaction between these modules and the implementation of decision-making mechanisms. These architectures are broadly categorized into three types:
  - **Reactive**: fast reactions/responses to changes detected in the environment;
  - **Deliberative**: focused on long term planning of actions, centered on a set of basic
goals;
  - **Hybrid**: a combination between reactive and a deliberative.

## 📑 3.1.1 - Reactive architecture

🔴 **Reactive architecture emphasize immediate responsiveness to environmental stimuli**. Main characteristics:
- operate without maintaining historical context, planning capabilities or complex internal states;
- decision-making is achieved through direct mappings from perceived situations to actions.

**Advantages**: This simplicity allows for **fast execution and low computational overhead**, making reactive agents suitable for dynamic environments such as video games or obstacle-avoiding robots.

**Disadvantages**: their lack of memory and learning capabilities limits their adaptability and long-term optimization.

<img width="685" height="294" alt="image" src="https://github.com/user-attachments/assets/c3270454-95ba-4e34-bea6-5b2100b8f9c4" />

> ### Image: Reactive architecture agent representation

## 📑 3.1.2 - Deliberative architecture 

🔴 **Deliberative architecture incorporate internal representations of the environment and rely on planning mechanisms**. Main characteristics:
- agents maintain state, remember past interactions and predict future outcomes through structured reasoning processes;
- planning in such systems involves searching through possible states and actions using predictive models.

<img width="788" height="194" alt="image" src="https://github.com/user-attachments/assets/fa64e36a-f542-4be7-98c7-438086efc980" />

> ### Image: Deliberative architecture agent representation

Problems addressed by planning can be categorized as:
- Ignorable: steps can be skipped;
- Recoverable: steps can be reversed;
- Irrecoverable: decisions are final.

**Deliberative agents may operate in offline mode when the environment is known** or **online mode in uncertain environments**, requiring adaptive replanning and learning techniques such as reinforcement learning.

## 📑 3.1.3 - Hybrid architecture

🔴 Hybrid architecture aim to **integrate the strengths of both reactive and deliberative approaches**.
They combine fast responsiveness with strategic planning by structuring agents into layered systems.
In horizontal layering, each layer independently connects to both input and output, enabling parallel behavior generation. In vertical layering, processing flows sequentially through layers, though this introduces potential fault tolerance issues. Hybrid systems are particularly effective in complex environments where both immediate reactions and long-term reasoning are required.

<img width="680" height="515" alt="image" src="https://github.com/user-attachments/assets/15c7992e-6027-4fce-986e-837324990222" />

> ### Image: Hybrid architecture agent representation

## 📑 3.1.4 - Logic-based architecture

🔴 **Logic-based architectures rely on symbolic representations and formal logic to drive decision-making**.
Main characteristics:
- can be deliberative or hybrid;
- the syntactic manipulation corresponds to logical deduction or theorem proving;
- their computational complexity often limits real-time applicability;
- systems typically lack inherent learning capabilities, although extensions like Inductive Logic Programming (ILP) introduce supervised rule learning.

## 📑 3.1.5 - Belief-desire intention (BDI) architecture
🔴 The _BDI_ architecture **models human practical reasoning** by structuring agent cognition into three components:
- **Beliefs**: information about the world;
- **Desires**: objectives to achieve;
- **Intentions**: committed plans of action.

Decision-making is split into deliberation (selecting goals) and means-ends reasoning (determining how to achieve them). 🔴 **This framework provides an intuitive and modular approach to agent design and is widely used in applications requiring human-like reasoning**.

<img width="637" height="404" alt="image" src="https://github.com/user-attachments/assets/1b002fc0-714d-4b80-a065-ccb4d75b87bb" />

> ### Image: Belief-desire intention (BDI) architecture agent representation

## 📖 3.2 - Agent Programming Languages

**Agent-oriented programming** (_**AOP**_) represents a paradigm shift introduced to directly encode agent behavior using high-level mentalistic constructs such as beliefs, desires and intentions.
🔴 **AOP abstracts away low-level implementation details, focusing instead on specifying “what” the agent should achieve rather than “how” to achieve it**. This positions AOP as a post-declarative paradigm that **extends object-oriented programming principles**.

Several specialized programming languages and frameworks support agent-oriented development:
- **AGENT0**, one of the earliest AOP languages, uses a Lisp-like syntax to define agent behavior;
- **AgentSpeak**, adopts a Prolog-like syntax and directly implements the BDI architecture, enabling structured reasoning and planning. Extensions such as **AgentSpeak(PL)** incorporate probabilistic reasoning through Bayesian networks, enhancing decision-making under uncertainty. The Jason framework serves as an interpreter for extended AgentSpeak, facilitating practical deployment;
- **Concurrent MetateM** represents another approach, where logical specifications are directly executed as programs. This enables agents to operate based on time-dependent logical constraints.
