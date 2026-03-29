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
