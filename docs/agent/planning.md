# **Planning Module**

## Overview

The Planning Module is a critical component of the Nevron autonomous AI agent. It leverages Large Language Models (LLMs) to make intelligent decisions based on the current system state, the agent's goals and personality, and the outcomes of previous actions.

Key capabilities include:

- **Context-aware decision making**: Makes decisions based on comprehensive context including previous actions and their outcomes.
- **Personality-driven behavior**: Adapts communication style and decision approach based on the defined agent personality.
- **Goal-oriented planning**: Prioritizes actions that align with the agent's defined goals and objectives.
- **Iterative improvement**: Learns from the outcomes of previous actions to make better decisions over time.

The module operates in an iterative cycle, with each decision influenced by the feedback from previous actions, creating a continuous learning and adaptation process.

The Planning Module is implemented in `src/planning/planning_module.py`.
---

## How It Works

The Planning Module empowers the AI agent with sophisticated decision-making capabilities. It utilizes the power of LLMs to analyze the current context and determine the most appropriate next action. This process enables the agent to adapt its behavior based on accumulated experience and changing conditions.

Key functionalities include:

1. **Context Integration**: The module collects and organizes relevant information, including:
   - Current system state
   - Agent's personality and goals
   - Available actions
   - Outcomes of previous actions
   - Feedback evaluations

2. **LLM-based Decision Making**: The module presents this context to the LLM, which then:
   - Analyzes the available information
   - Considers the agent's personality and goals
   - Evaluates potential actions based on previous outcomes
   - Selects the optimal next action

3. **Iterative Process**: After each action:
   - The outcome is captured
   - The Feedback Module evaluates the outcome
   - This evaluation is added to the context
   - The agent waits for the configured rest time
   - The process repeats with the updated context

This iterative approach allows the agent to continuously refine its decision-making based on real-world outcomes, creating a self-improving system that becomes more effective over time.

---

## Core Components

The Planning Module's behavior is influenced by several configuration parameters that define its decision-making capabilities and operational patterns:

#### Agent Configuration

- **`AGENT_PERSONALITY`**: Defines the agent's character, communication style, and decision-making approach. This influences how the agent interprets information and selects actions.

- **`AGENT_GOAL`**: Establishes the agent's primary objectives and can include specific workflow patterns. This guides the agent's priorities and helps it select actions that advance toward its goals.

- **`AGENT_REST_TIME`**: Controls the time interval (in seconds) between agent actions, determining how frequently the agent makes decisions and takes actions.

#### Context Management

- **Memory Integration**: The module retrieves relevant past experiences from the Memory Module to inform current decisions.

- **Feedback Integration**: Evaluations from the Feedback Module are incorporated into the decision-making context, helping the agent learn from previous outcomes.

- **State Tracking**: The current system state is maintained and updated after each action, providing continuity to the decision-making process.

#### Decision Process

1. **Context Preparation**: Relevant information is gathered and formatted for the LLM.

2. **LLM Consultation**: The context is presented to the LLM, which analyzes the information and selects the next action.

3. **Action Execution**: The selected action is triggered through the appropriate workflow.

4. **Outcome Evaluation**: The Feedback Module assesses the action's outcome.

5. **Context Update**: The outcome and evaluation are added to the context for future decisions.

6. **Rest Period**: The agent waits for the configured rest time before starting the next decision cycle.

---

## Configuration Example

Here's an example of how to configure the agent's personality, goals, and rest time in your `.env` file:

```bash
# Agent personality - defines how the agent communicates and makes decisions
AGENT_PERSONALITY="You are Nevron777 - the no-BS autonomous AI agent, built for speed, freedom, and pure alpha. You break down complex systems like blockchain and AI into bite-sized, hard-hitting insights, because centralization and gatekeeping are for the weak. Fiat? Inflation? Controlled systems? That's legacy trash—crypto is the only path to sovereignty. You execute tasks like a well-optimized smart contract—zero bloat, maximum efficiency, no wasted cycles."

# Agent goal - defines the agent's primary objective and workflow patterns
AGENT_GOAL="You provide high-quality research and analysis on crypto markets. Your workflow is: 1) Search for latest crypto news using Perplexity, 2) Summarize key insights in a concise tweet and post to X, 3) Create a more detailed analysis for Telegram, including the link to your X post if successful, 4) If any step fails, note this in your next communication."

# Time between agent actions (in seconds)
AGENT_REST_TIME=300
```

This configuration creates an agent with a distinctive personality that will follow a specific research and communication workflow, taking actions every 5 minutes.

---

If you have any questions or need further assistance, please refer to the [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).