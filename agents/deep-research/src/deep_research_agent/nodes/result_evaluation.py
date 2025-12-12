"""
Result Evaluation Node (Lead Orchestrator Logic)
Evaluates the result of a step execution and decides whether to:
1. Proceed to next step
2. Add new sub-steps (Recursive Planning)
3. Retry current step (optional)
"""

import json
import logging
from datetime import datetime
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from deep_research_agent.state import ResearchAgentState, ResearchStep, ResearchStepStatus
from agent_core.utils.models import get_chat_model

logger = logging.getLogger(__name__)

EVALUATION_TEMPLATE = """
You are the Lead Orchestrator of a Deep Research Agent.
You are evaluating the result of a research step to decide the next move.

Current Date: {current_date}
Current Topic: {topic}
Current Step: {step_title}
Expected Output: {expected_output}
Current Recursion Depth: {current_depth}

Execution Result (Insight):
{insight_content}

Your Task:
Analyze if the result satisfies the expected output, considering validity and freshness significantly based on Current Date ({current_date}).
- If YES: Mark complete.
- IF NO or PARTIAL: Identify what is missing or what new questions have emerged.

Constraint:
- Max Recursion Depth is {max_depth}. If current depth >= max_depth, you MUST NOT generate new steps, just accept what we have.

Output JSON format:
{{
    "status": "APPROVED" | "NEEDS_MORE_INFO",
    "reasoning": "Explanation of decision",
    "new_steps": [  # Only if NEEDS_MORE_INFO
        {{
            "title": "Title for new sub-step",
            "description": "Description of what to do",
            "keywords": ["keyword1"],
            "expected_output": "What to find",
            "assigned_agent": "researcher" 
        }}
    ]
}}
"""

MAX_RECURSION_DEPTH = 3

async def evaluate_task_result(state: ResearchAgentState) -> ResearchAgentState:
    """
    Evaluates the result of the current task.
    Dynamically modifies the plan if needed (Recursive Planning).
    """
    current_step = state.get_current_step()
    if not current_step:
        logger.warning("No current step to evaluate.")
        return state

    # Get the insight from the current step
    step_id = current_step.step_id
    insight = state.extracted_insights.get(step_id)
    
    # Determine if we should proceed with evaluation
    should_evaluate = True
    
    if not insight:
        logger.warning(f"No insight found for step {step_id}. Assuming failed or empty. Skipping evaluation.")
        should_evaluate = False
    elif current_step.depth >= MAX_RECURSION_DEPTH:
        logger.info(f"Max recursion depth {MAX_RECURSION_DEPTH} reached. Skipping evaluation for expansion.")
        should_evaluate = False

    if should_evaluate:
        try:
            llm = get_chat_model(
                temperature=0.2, # Low temp for decision making
                model_name=state.config.llm_model
            )
            
            current_date_str = datetime.now().strftime("%Y-%m-%d")
            prompt = ChatPromptTemplate.from_template(EVALUATION_TEMPLATE)
            messages = prompt.format_messages(
                topic=state.research_plan.topic,
                step_title=current_step.title,
                expected_output=current_step.expected_output,
                current_depth=current_step.depth,
                max_depth=MAX_RECURSION_DEPTH,
                insight_content=insight.content[:2000], # Truncate to avoid huge context
                current_date=current_date_str
            )
            
            response = await llm.ainvoke(messages)
            content = response.content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            decision_data = json.loads(content)
            
            status = decision_data.get("status")
            
            if status == "NEEDS_MORE_INFO":
                new_steps_data = decision_data.get("new_steps", [])
                new_steps = []
                
                for i, step_data in enumerate(new_steps_data):
                    new_step_id = f"{current_step.step_id}.sub{i+1}"
                    new_steps.append(ResearchStep(
                        step_id=new_step_id,
                        title=step_data.get("title"),
                        description=step_data.get("description"),
                        keywords=step_data.get("keywords", []),
                        expected_output=step_data.get("expected_output", ""),
                        assigned_agent=step_data.get("assigned_agent", "researcher"),
                        depth=current_step.depth + 1
                    ))
                
                if new_steps:
                    logger.info(f"Recursive Planning: Adding {len(new_steps)} new sub-steps at depth {current_step.depth + 1}")
                    state.insert_steps_after_current(new_steps)
                    
            else:
                logger.info(f"Step {step_id} approved.")
                
        except Exception as e:
            logger.error(f"Error in evaluate_task_result: {e}")
            # On error, we default to proceeding
        
    # Always advance the step index after evaluation
    # If new steps were inserted, this index now points to the first new step.
    # If no new steps, this index points to the original next step.
    state.current_step_index += 1
    return state
