# A Local ReAct Coding Agent with Hidden-Test Evaluation

Vincent Le  
Knox College  
Math/Stat 361 Research  
Advisor: Prof. Andrew Leahy

## Abstract

I built a coding agent from scratch around a local Qwen3-14B model served by vLLM. The agent uses a standard ReAct loop: the model sees a goal, a message history, and tool schemas, then either calls tools or replies in text. The system has 11 tools for file I/O, search, shell execution, Python execution, subagent delegation, and explicit completion. All file paths go through a `_safe_path` sandbox that confines the agent to a workspace.

The project is not a claim about beating Claude, Codex, or other production agents. It is a small transparent agent that I can explain line by line. I evaluated it on 627 tasks using hidden tests. During hardening, I found a leak in my MBPP conversion script: about 93% of MBPP tasks exposed 2 of the 3 graded asserts to the agent. That inflated an earlier score of 79.9%. After regenerating the MBPP tasks as spec-only prompts, the real score was 67.3%: 422 out of 627 tasks, with a 95% confidence interval of 64% to 71%.

I also ran a small SkillOpt experiment where the model weights stayed frozen and only a natural-language skill document was optimized. On 84 test tasks, the empty, seed, and optimized arms scored 0.786, 0.738, and 0.774. Exact-binomial McNemar tests gave p-values at least 0.29. A repeat of the empty arm flipped about 6 of 84 tasks, which is about the size of the observed gaps. I treat that result as inconclusive.

## Introduction

I wanted a coding agent I could inspect without guessing what a framework was doing. The target was simple: take a natural-language task, operate on a local repository, edit files, run tests, and stop when the task is done. The model was local Qwen3-14B, served through vLLM on one GPU with an OpenAI-compatible endpoint. The Python code used the OpenAI SDK, vLLM, and `python-dotenv`. No agent framework.

That constraint mattered. A framework would have made progress faster, and it probably would have handled some edge cases better. It also would have hidden too much of the agent behind abstractions. This was a Math/Stat 361 research project, and the final artifact had to be something I could defend at the source-code level. The goal was not just performance. It was transparency.

The agent uses ReAct, following the general pattern from Yao et al. (2023). The model alternates between reasoning through the task and taking actions through tools. That idea is not new. Claude, Codex, and similar systems use tool-calling loops with much better engineering around them. My system does not beat them, and I do not claim that it does. The question here is narrower: how far can a small local implementation get, and what breaks when it is evaluated carefully?

The answer is mixed. The final benchmark result is usable but not impressive by commercial-agent standards. The agent solves many basic programming tasks, some harder ones, and it fails in predictable ways. The most common failure was surprisingly boring: the model answered in prose without calling a tool. That happened on 66 of 627 tasks. A guardrail that nudges the model to act recovered most of those cases.

The more important result was the evaluation leak. My first full benchmark result looked much better than it deserved to. It said 501 of 627 tasks passed, or 79.9%. Later, while hardening the project with a multi-agent audit and a cross-check using Codex/GPT-5.5, I found that my MBPP converter was putting graded asserts into the prompt. The agent could read 2 of the 3 graded assertions on about 93% of the 424 MBPP tasks. That invalidated the earlier MBPP score.

I fixed the converter, regenerated all 424 MBPP tasks as spec-only goals, and reran the benchmark. The corrected score was 422 of 627, or 67.3%. HumanEval+ had never leaked and stayed around 79.8%, which was a useful consistency check. The MBPP score after de-leaking was 66.7%. The hand-written hard set was 21.6%.

That is the main lesson from the project. Agent evaluation is easy to fool by accident. A result can look stable while a dataset pipeline is leaking information. Hidden tests, validation gates, and adversarial review are not extra polish. They are the difference between a measurement and a number.

## System

The core function is `run_agent(goal, workspace)`. It starts with a user goal and a workspace directory. Each iteration sends the current message history plus the tool schemas to the local OpenAI-compatible endpoint. The model can return either plain text or `tool_calls`. If it returns tool calls, the agent executes them, appends the tool results to the message history with `role="tool"`, and loops again. The maximum number of iterations is 15.

There is one implementation detail that became load-bearing. When the model returns an assistant message with `tool_calls`, that assistant message must be stored verbatim in the message history. If it is not, the OpenAI-compatible API rejects the next request with a 400 error. The API expects the tool result messages to match a previous assistant message that contained tool calls. I hit this because the message history is not just a transcript for humans. It is part of the protocol.

The client is created lazily and uses an explicit 120 second timeout with `max_retries=1`. The timeout matters because a local model can stall long enough to make debugging unclear. One retry is enough to tolerate a transient failure without hiding repeated failures behind long waits.

The tool surface has 11 tools:

- `read_file`
- `write_file`
- `apply_patch`
- `multi_edit`
- `list_dir`
- `glob_files`
- `grep_files`
- `run_bash`
- `run_python`
- `spawn_subagent`
- `finish`

The file tools are intentionally basic. `read_file` reads a file. `write_file` writes a file. `apply_patch` applies a patch. `multi_edit` performs multiple edits. The discovery tools list directories, glob files, and grep text. The execution tools run shell or Python commands. `spawn_subagent` delegates a goal to another agent loop inside the same workspace. `finish` is an explicit completion signal.

I made `finish` a tool because plain text is ambiguous. If the model says “done” in prose, that might be a final answer or it might be commentary. The runtime needs a clean signal. In this project, replying in prose without a tool call does not end the task. The agent either calls tools, calls `finish`, or runs out of iterations.

The sandbox is the main safety boundary. Every file path goes through `_safe_path(path, workspace)`. It resolves `..`, turns paths into real locations, and blocks paths that escape the workspace. The model never sees the `workspace` argument. It can ask to read `src/main.py`, but it cannot choose the root that path is resolved against. That root is passed by the runtime.

This is not a complete security sandbox. `run_bash` and `run_python` can still execute code, so they need to be treated as dangerous tools. The file sandbox solves one narrower problem: tool calls for file operations should not read or write outside the assigned repository. For a coding agent, that boundary is basic hygiene.

The loop is verbose by design. The runtime logs each step: model calls, tool invocations, tool results, and model reasoning when available. This is partly for debugging, but mostly for learning. A silent coding agent is harder to study. If it changes a file and only reports success, I lose the evidence trail. The whole point of this project was to make that trail visible.

## Evaluation and the Leak

I built a benchmark with 627 tasks. It had 163 HumanEval+ tasks, 424 sanitized MBPP tasks, 37 hand-written hard tasks, and 3 legacy demo tasks. The benchmark runs the agent on each task in a temporary workspace and scores the result with tests that the agent does not control.

The scoring uses hidden tests. During the agent run, the grading tests are removed. The agent only sees the task prompt and the visible repository state. After the agent stops, the grader restores the tests and runs them independently. This matters because a coding agent with shell access can inspect anything placed in the workspace. If the tests are there, they are not hidden.

The benchmark also has a validation gate. For each task, a reference solution must pass and the stub must fail. Broken tasks are pruned before agent evaluation. This is a simple check, but it catches a class of benchmark errors that would otherwise waste time. If the reference fails, the task may be wrong. If the stub passes, the task is too weak.

The evaluation leak came from the MBPP converter. MBPP tasks usually include examples or assertions in their source format. My converter was supposed to turn them into spec-only goals while keeping the graded tests hidden. It did not do that correctly. For about 93% of the 424 MBPP tasks, it put 2 of the 3 graded asserts into the prompt that the agent could read.

That means the agent often saw most of its grader. It still had to write code, but the task was much easier than intended. The earlier full benchmark score was 501 of 627, or 79.9%. That number was inflated.

I found the problem while hardening the project. I ran a multi-agent audit and then cross-checked the evaluation setup with Codex/GPT-5.5. The audit forced me to inspect the data path instead of only looking at pass rates. Once I looked directly at generated MBPP prompts and their hidden tests, the leak was obvious.

The fix was to regenerate all 424 MBPP tasks with spec-only goals. The prompts no longer included the graded asserts. Then I reran the full benchmark. The corrected score was 422 of 627, or 67.3%, with a 95% confidence interval of 64% to 71%.

The HumanEval+ score stayed around 79.8%. That subset had never leaked, so it acted like a consistency check. If HumanEval+ had also collapsed, I would have suspected some broader benchmark change. It did not. The corrected drop was concentrated where the leak had been.

This was annoying, but it was useful. The project became more credible after the lower number. The earlier result was too good for the system I had built. The corrected result fits the actual agent better.

## Results

The final benchmark result was 422 passes out of 627 tasks, or 67.3%. The 95% confidence interval was 64% to 71%.

By dataset, HumanEval+ was about 79.8%. The de-leaked MBPP score was 66.7%. The hand-written hard tasks were 21.6%. That spread makes sense. HumanEval+ tasks are compact function-writing problems. MBPP has more variety after removing leaked asserts. The hand-written hard tasks were designed to stress the agent more directly.

By difficulty, the pass rates were:

- Easy: 74%
- Medium: 74%
- Hard: 54%

The easy and medium rates being equal is not a typo. Difficulty labels are coarse. They are useful for grouping, but they are not a perfect predictor of what a local ReAct agent will solve. Some “easy” tasks require the model to infer missing details or avoid a trap. Some “medium” tasks are direct if the tests point toward the needed behavior.

The most common failure mode was `no_action`. On 66 of 627 tasks, the model answered in prose without calling a tool. This is a strange failure because it is not a coding mistake. The model often described what should be done, then stopped. For this runtime, that is useless. The agent cannot fix a repository by explaining the fix.

I added a guardrail that nudges the model to act when it tries to answer without a tool call. That recovered most of the `no_action` cases. I do not treat this as a deep algorithmic improvement. It is more like adding a sign that says “use the tools.” Still, it mattered. Local instruction-following can be brittle, and tool use is the behavior the whole system depends on.

Other failures were more ordinary. Some solutions were wrong. Some edits were incomplete. Some tasks hit the 15-iteration limit. Some likely suffered from local model limits. Qwen3-14B is capable, but it is not a replacement for a larger production coding agent.

I also learned that benchmark scores are more fragile than they look. A single run gives one number, but the local stack has nondeterminism even at temperature 0. vLLM can produce run-to-run differences. That became clear in the SkillOpt experiment, where repeating the same empty-arm condition flipped about 6 of 84 tasks.

So the final score should be read as a measured result for this implementation under this benchmark, not as a universal property of Qwen3-14B or ReAct. The benchmark is useful because it is hidden-test based and the leak was fixed. It is still one evaluation setup.

## SkillOpt

The SkillOpt experiment asked a narrower question: can I improve the agent by optimizing a natural-language skill document while leaving the model weights frozen?

The skill document is plain text. The optimizer can edit it with append, insert, replace, and delete operations. Candidate documents are evaluated through a validation gate. The model itself is not fine-tuned. This connects to prior work on optimizing prompts or text instructions, including OPRO, TextGrad, and GEPA. Voyager is also relevant because it stores and reuses skills in an agent setting. I was pointed to a paper called “SkillOpt,” but I could not verify it, so I do not rely on it as a source.

The experiment had three arms on 84 test tasks:

- Empty skill document: 0.786
- Seed skill document: 0.738
- Optimized skill document: 0.774

The optimized arm did not beat the empty arm. It did beat the seed arm, but the gap was small. I reported Wilson confidence intervals and used exact-binomial McNemar tests for paired comparisons. All p-values were at least 0.29.

That means I do not have evidence that the skill optimizer worked. The clean conclusion is under-powered and inconclusive.

The run-to-run noise makes that conclusion stronger. I reran the empty arm and about 6 of 84 tasks flipped. That is roughly 7 percentage points. The observed arm gaps are the same size as the nondeterminism. A difference that size could be an optimizer effect, or it could just be the local inference stack moving around.

The validation set was also tiny: 12 tasks. That is too small for a reliable optimizer signal. With a small validation set, an optimizer can chase noise. With one test run per arm, I cannot separate document quality from sampling variation. Temperature 0 did not remove the problem.

I still think the experiment was worth running because it put a number on a common claim. It is easy to say that better instructions improve agents. Sometimes they do. Here, with this model, this optimizer, and this task count, I could not show it. The optimized document landed near the empty baseline, and the statistics did not support a stronger claim.

A better version would use a larger validation set, more test tasks, repeated runs per arm, and maybe a cleaner split by task type. It would also need stricter controls around inference nondeterminism. That is future work, not a result from this project.

## Limitations

This project used one model: Qwen3-14B. It ran locally through vLLM on one GPU. I did not compare multiple model sizes, multiple serving stacks, or commercial APIs. The result is therefore about this agent in this setting.

The ReAct loop is standard. I implemented it from scratch, but I did not invent the method. The agent does not exceed Claude or Codex in capability. It is much smaller and less engineered. Its value is that the implementation is visible.

The benchmark is better after the leak fix, but it is still limited. The hard task set has only 37 hand-written tasks. The SkillOpt test set has 84 tasks, and the validation set has 12. Those are small numbers. They are enough to catch large effects. They are not enough to measure subtle improvements.

The evaluation used a single run per main condition. That is weak because vLLM showed nondeterminism even at temperature 0. A stronger evaluation would run each condition multiple times and report variation across runs.

The tools are also limited. The agent can read files, edit files, search, and run commands. It does not have a browser. It does not have a rich planner. It does not have long-term memory beyond the message history and any files it writes. The subagent tool exists, but this project does not prove that delegation is useful.

The sandbox is narrow. `_safe_path` protects file tools from escaping the workspace, but shell execution remains powerful. A real deployment would need stronger process isolation. For this research project, the agent was run locally on controlled benchmark workspaces.

The SkillOpt optimizer is local and simple. It edits a natural-language document, validates candidates, and keeps the model frozen. That is a reasonable experiment, but it is not a full prompt-optimization study. The negative result should not be read as “skill optimization does not work.” It means this experiment could not tell.

## What’s Mine vs Reused

The ReAct idea is reused. Yao et al. (2023) introduced the ReAct pattern of combining reasoning and actions. My agent follows that general structure.

The idea of agent skills is also not mine. Voyager used a skill library in a Minecraft agent setting. TextGrad, GEPA, and OPRO are part of the broader line of work on optimizing text, prompts, or programs through feedback. My SkillOpt experiment sits near that family, but it is much smaller.

The local inference stack is reused. Qwen3-14B is an external model. vLLM is the serving engine. The OpenAI Python SDK provides the client interface. `python-dotenv` loads configuration. I did not build those systems.

What I built is the small coding-agent runtime around them: the `run_agent(goal, workspace)` loop, tool schema wiring, tool execution path, workspace sandbox for file tools, benchmark harness, validation gate, MBPP regeneration fix, hidden-test scoring, and the SkillOpt experiment code.

I also built the teaching shape of the project. The source is deliberately small. The runtime is verbose. The examples form a ladder from a basic chat script to a sandboxed ReAct loop. That design choice is part of the research artifact because the project was supposed to be explainable.

The leak discovery is also part of my result. It was not a feature I planned, but it changed the project. The final evaluation is stronger because the bad number was thrown out.

## Conclusion

I built a from-scratch local coding agent using a standard ReAct loop, a local Qwen3-14B model through vLLM, and a small set of tools. The system can solve a real portion of benchmark programming tasks, and its final hidden-test score was 67.3% over 627 tasks.

The most important technical lesson was not the loop. The loop is straightforward. Send messages and schemas, receive tool calls, execute tools, append results, repeat. The details matter more than the slogan: store assistant tool-call messages verbatim, keep file paths inside the workspace, give the client real timeouts, and make the model call an explicit `finish` tool.

The most important research lesson was the MBPP leak. My first score was 79.9%, and it was wrong. The converter exposed graded asserts in most MBPP prompts. After fixing the tasks and rerunning the benchmark, the score dropped to 67.3%. HumanEval+ stayed around 79.8%, which helped isolate the leak. That was a useful failure. It made the evaluation less flattering and more real.

The SkillOpt result was inconclusive. The optimized skill document scored 0.774 on 84 tasks, compared with 0.786 for an empty document and 0.738 for a seed document. The paired tests were not significant, and run-to-run noise was about the same size as the arm gaps. I do not claim skill optimization worked.

The final system does not beat production agents. It is not novel as an agent architecture. Its contribution is smaller: a transparent local implementation, a hidden-test benchmark, a documented evaluation leak, and a set of measurements that I can explain without waving at a framework. That was the point of the project.