# **Feedback Module**

## Overview

The Feedback Module is a critical component of Nevron's autonomous decision-making system. It processes action results, evaluates outcomes, and updates the context for future decisions in the Planning Module. This module is essential for the agent's learning loop, enabling it to learn from past experiences and improve its decision-making over time.

The Feedback Module is implemented in `src/feedback/feedback_module.py` and provides structured methods for collecting, storing, and analyzing feedback related to agent actions.

---

## How It Works

The Feedback Module operates as follows:

1. **Feedback Collection**:
   Captures feedback based on the action performed and its outcome, assigning a feedback score to evaluate success or failure. This evaluation is used to inform future decisions by the Planning Module.

2. **Feedback Storage**:
   Maintains an internal history of feedback entries, including details about the action, its outcome, and the assigned feedback score. This history serves as a memory of past performance.

3. **Feedback Retrieval**:
   Allows querying of recent feedback entries for analysis, monitoring, and providing context to the Planning Module for informed decision-making.

4. **Context Integration**:
   Integrates with the Planning Module to provide historical context about action outcomes, enabling the agent to make more informed decisions based on past experiences.

---

## Integration with Planning Module

The Feedback Module directly integrates with the Planning Module to create a learning loop:

1. The Planning Module selects an action based on current context, agent personality, and goals
2. The action is executed by the agent
3. The Feedback Module evaluates the outcome using LLM-based analysis
4. This feedback is stored and provided to the Planning Module as part of the context
5. The cycle repeats, with the agent continuously learning and improving

This integration is key to Nevron's autonomous decision-making capability, allowing it to adapt its behavior based on the success or failure of previous actions.

---

## Technical Features

### 1. Feedback Collection

The `collect_feedback` method records feedback for a specific action and its outcome. It assigns a feedback score based on predefined criteria:

- **Failure**: Assigned a score of `-1.0` if the outcome is `None`.
- **Success**: Assigned a score of `1.0` for successful outcomes.

#### Implementation:

```python
feedback_score = -1.0 if outcome is None else 1.0
```

- **Inputs**:

  - `action` (str): The name of the action performed.
  - `outcome` (Any): The outcome of the action; `None` for failure or a value indicating success.

- **Output**:

  - Returns a feedback score (`float`) for the action.

- **Example Usage**:

```python
feedback_score = feedback_module.collect_feedback("fetch_data", outcome=data)
```

### 2. LLM-Based Outcome Evaluation

The Feedback Module can use the LLM to perform a more nuanced evaluation of action outcomes:

- Analyzes the outcome in the context of the agent's goals
- Considers the quality and relevance of the outcome
- Provides detailed feedback that goes beyond simple success/failure
- Generates insights that can guide future decisions

This LLM-based evaluation creates a richer context for the Planning Module, enabling more sophisticated decision-making.

---

### 3. Feedback History Retrieval

The `get_feedback_history` method retrieves the most recent feedback entries, limited by the specified count.

#### Features:

- Enables monitoring of agent performance
- Provides historical context for the Planning Module
- Default limit is set to 10 entries

#### Example:

```python
recent_feedback = feedback_module.get_feedback_history(limit=5)
```

---

### 4. Feedback Reset

The `reset_feedback_history` method clears the internal feedback history, resetting the module's state. This is useful for testing or reinitializing feedback tracking.

#### Example:

```python
feedback_module.reset_feedback_history()
```

---

## Key Methods

### `collect_feedback`

Captures feedback for a given action and outcome.

**Arguments**:

- `action` (str): The action name.
- `outcome` (Optional[Any]): The outcome of the action.

**Returns**:

- `float`: Feedback score.

### `get_feedback_history`

Retrieves recent feedback entries.

**Arguments**:

- `limit` (int): Number of entries to retrieve (default: 10).

**Returns**:

- `List[Dict[str, Any]]`: Recent feedback entries.

### `reset_feedback_history`

Clears the feedback history.

**Returns**:

- `None`

### `get_action_performance_metrics`

Calculates performance metrics for specific actions.

**Arguments**:

- `action` (str): The action to analyze.
- `time_period` (Optional[int]): Time period in seconds to consider (default: all history).

**Returns**:

- `Dict[str, float]`: Performance metrics including success rate and average score.

---

## Example Workflow

1. The Planning Module selects an action based on current context, agent personality, and goals
2. The action is executed by the agent (e.g., `fetch_data`)
3. The outcome of the action is evaluated, and feedback is collected:
   ```python
   feedback_module.collect_feedback("fetch_data", outcome=data)
   ```
4. The feedback is stored in the history
5. The outcome and feedback are added to the context
6. The Planning Module uses this updated context for the next decision cycle

---

## Benefits

- **Continuous Learning**: Enables the agent to learn from experience without human intervention
- **Performance Monitoring**: Tracks agent actions and their outcomes, enabling better performance evaluation
- **Adaptability**: Facilitates improvements by learning from historical data
- **Decision Support**: Provides valuable context to the Planning Module for better decision-making

---

## Configuration Options

The Feedback Module can be configured through environment variables:

- `FEEDBACK_HISTORY_SIZE`: Maximum number of feedback entries to store (default: 1000)
- `FEEDBACK_EVALUATION_PROMPT`: Custom prompt for LLM-based outcome evaluation

These settings can be adjusted in your `.env` file to fine-tune the agent's feedback behavior.

---

## Best Practices

1. **Consistent Feedback Collection**: Ensure feedback is collected for all critical actions to build a comprehensive history
2. **Detailed Outcome Logging**: Provide as much detail as possible in action outcomes to enable better evaluation
3. **Regular Performance Analysis**: Use `get_action_performance_metrics` to monitor and optimize agent behavior
4. **Periodic Reset**: Use `reset_feedback_history` during major strategy changes to allow fresh learning

---

## Advanced Usage

### Custom Feedback Scoring

For more nuanced feedback, you can implement custom scoring logic:

```python
def custom_score(outcome):
    if outcome is None:
        return -1.0
    elif isinstance(outcome, dict) and "quality" in outcome:
        # Scale from 0 to 1 based on quality
        return outcome["quality"] / 10.0
    else:
        return 0.5  # Partial success

feedback_score = feedback_module.collect_feedback("analyze_data", outcome=result, 
                                                 score_function=custom_score)
```

---

## Integration with Agent Runtime

The Feedback Module is integrated into the agent's runtime loop in `src/agent.py`:

```python
async def start_runtime_loop(self) -> None:
    while True:
        try:
            # 1. Choose an action using LLM-based planning
            action_name = await self.planning_module.get_action(self.state)
            
            # 2. Execute action using execution module
            success, outcome = await self.execution_module.execute_action(action_name)
            
            # 3. Collect feedback
            reward = self._collect_feedback(action_name.value, outcome)
            
            # 4. Update context and state
            self.context_manager.add_action(
                action=action_name,
                state=self.state,
                outcome=str(outcome) if outcome else None,
                reward=reward,
            )
            self._update_state(action_name)
            
            # 5. Sleep or yield
            await asyncio.sleep(settings.AGENT_REST_TIME)
        except Exception as e:
            logger.error(f"Error in runtime loop: {e}")
            break
```

This loop demonstrates how the Feedback Module fits into the agent's decision-making cycle, collecting feedback after each action and updating the context for future decisions.

---

## Known Limitations

- **Binary Default Scoring**: Default feedback scores are binary (`-1.0` or `1.0`). For more nuanced evaluation, use custom scoring functions.
- **Limited Context Consideration**: The current implementation doesn't fully account for the state context in which actions were performed.
- **Memory Constraints**: The feedback history is limited to a fixed number of entries, which may limit long-term learning in some scenarios.

---

If you have any questions or need further assistance, please refer to the [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).

