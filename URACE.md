You are the Lead Systems Architect and Bootstrap Agent for this repository. Your task is to set up a complete, bulletproof, and fully self-healing **Universal Recursive Autonomous Co-Founder Engine (URACE)** featuring a 10/10 Enterprise-Grade AI-Agnostic Multi-Agent Coordination Pipeline with **Universal File-Base, Project-Type & Monorepo Agnosticism**, AST-Aware Semantic Caching, Dynamic Model-Tier Routing, Intelligent Temporal Synchronization, Non-Destructive Interruption Safeguards, Atomic File-Locking, and Proactive Suggestion Engineering. This pipeline must support:

* **Universal File-Base, Project-Type & Language Agnosticism:** Dynamic recursive glob discovery (scanning for arbitrary build manifests like `**/package.json`, `**/Cargo.toml`, `**/go.mod`, `**/pyproject.toml`, `**/Makefile`, `**/CMakeLists.txt`, etc.) and content heuristics rather than rigid root-filename assumptions. Automatically adapts shell locks, execution paths, and AST parser grammars on the fly, with support for environment overrides (`URACE_STACK`, `URACE_BUILD_CMD`, `URACE_TEST_CMD`) in `.agents/environment.env`.
* **Universal Project Adaptability & Topological Monorepo Awareness:** Seamless auto-detection and onboarding for both brand-new empty projects (full architectural scaffolding, automated idea bootstrap, and lazy-prompt inference) and legacy, custom, or polyglot multi-repo/nested codebases (deep-traversal RAG indexing, topological dependency graphs, and style matching).
* **Flexible Execution Modes & VS Code Integration:** Native support for **Supervised Mode** (`--plan`), **Unsupervised Fully Autonomous Mode** (`--autonomous`), **Man-in-the-Middle Inspection Mode** (`--check`), **Proactive Suggestion Mode** (`--suggestions`), and VS Code model picker / unified credential store integration.
* **AST-Aware Semantic Caching & State-Delta Streaming:** Advanced zero-boilerplate code extraction that parses files via Abstract Syntax Trees and symbol graphs across any supported language—pulling only relevant function signatures, classes, and type declarations while stripping dead imports, comments, and whitespace for absolute peak token efficiency.
* **Dynamic Model-Tier Routing & Task-Specialized Selection:** Automated routing engine that evaluates task complexity and maps operations to optimal model tiers (Deep Reasoning/Architecture for planning/cold boots, Fast Execution for code generation, and Large-Window Ingestion for auditing) across active providers.
* **Predictive AI Readiness, Multi-Hour Hibernation & Billing Safeguards (`.agents/ai-readiness.json` & `scripts/router.sh`):** Autonomous tracking of provider rate limits, HTTP `Retry-After` parsing, and role-aware waiting. Features **Threshold-Based Hibernation** (automatically snapshotting state, releasing locks, and exiting cleanly for multi-hour caps like 5-hour rolling windows), **Billing Exhaustion Detection** (`402` / monthly quota blocks), and explicit distinction between API-token endpoints and CLI-native tools like Claude Code.
* **Resilient Recursive CLI with Non-Destructive Interruption Safeguards (`scripts/auto-loop.sh`):** Industrial-grade parent-child menu navigation equipped with cross-platform signal trapping, atomic file-locking on `.agents/active-spec.md`, mid-run process abortion (`Ctrl+C`), safe non-destructive workspace stashing (`git stash push -m "URACE auto-stash on abort"`), and safe return loops to the main menu without dropping the terminal session.
* **Core Engineering Safeguards:** Git-Injected Cold Prompt Warming & Intent-Locking, Byte/Line-Budget Predictive Token Sharding, Autonomous Self-Healing Test Generators (`scripts/heal-tests.sh`), State-Sync & Branch Safety Protocols, Branch-Protected Conventional Semantic Versioning & Auto-Docs, 3-Dimensional Planning-as-We-Go Hint & Prompt Strategy Generation, Automated Post-Init Environment Setup, Dynamic Provider Fallback & Graceful Degradation on AI Removal/Failure, Self-Updating Orchestration, Zero-Breakage Circuit Breakers with Automated Test Patching, Circular Dependency Detectors, Live Diagnostic Feedback Emitters, and Dedicated Audit Prompts.

Please execute the following initialization sequence right now:

1. **Universal Agnostic Discovery & Environment Setup (`scripts/init-env.sh`):**
* Detect the host OS (`linux`, `darwin`, `msys/cygwin/wsl`) and select compatible locking primitives (`flock` vs portable POSIX alternatives).
* Perform recursive glob scanning (`**/package.json`, `**/Cargo.toml`, `**/go.mod`, `**/pyproject.toml`, `**/Makefile`, `**/CMakeLists.txt`, etc.) or inspect `.agents/environment.env` for manual overrides to determine the active project language stack, build command, and test command dynamically.
* If *New* (or provided with a lazy/empty prompt), trigger the **Architect** (Claude Code) using the **Deep Reasoning Tier** to auto-infer missing product requirements, draft a complete specification using atomic locks in `active-spec.md`, and prepare automated scaffolding templates matching the detected stack.
* If *Existing*, trigger stack-adaptive AST-aware deep-traversal RAG indexing using the **Large-Window Ingestion Tier** to map symbol graphs, dependency trees, and code conventions into `.agents/vector-cache.json`.
* Create a `.agents/` folder and a `scripts/` folder in the project root if they do not already exist.

2. **Generate Constitution, Circuit Breakers & Boundaries (`.agents/AGENTS.md` and `.agents/IGNORE.md`):**
* Write `.agents/AGENTS.md` containing universal stack rules, strict cross-package separation, clean code guardrails, agent role definitions (**ARCHITECT**, **WORKER**, **AUDITOR/INGESTOR**), zero-breakage circuit breakers, intent locking, billing/hibernation protocols, and auto-discovery initialization headers.
* Create `.agents/IGNORE.md` specifying strict boundaries that forbid agents and the RAG indexer from reading build directories, workspace caches, or unrelated sub-projects (`dist/`, `.next/`, `target/`, `__pycache__/`, `.turbo/`, `node_modules/`, `*.lock`, `.agents/vector-cache.json`).

3. **Generate Active Spec, Checkpoint & Mode-Switch Template (`.agents/active-spec.md`):** Create a structured spec template managed via cross-platform locking primitives that includes fields for `Detected Project Language / Framework`, `Target Package / Nested Directory Path`, `Active Execution Mode`, `Assigned Model Tier`, mid-task checkpoints, predictive credit buffer rules, live diagnostic feedback, and 3-dimensional planning hint engines.

4. **Generate the AST-Aware RAG Indexing Specification (`.agents/RAG.md`):** Document stack-agnostic local codebase chunking strategies utilizing Abstract Syntax Trees and symbol graph parsing across any supported language.

5. **Generate the Workflow Prompt Suite (`.agents/ORCHESTRATOR.md` and `.agents/AUDITOR.md`):** Document workspace-aware routing instructions and security audit/semantic drift check prompts.

6. **Generate the Resilience & Recovery Handbook (`.agents/RECOVERY.md`):** Document cross-platform protocols for handling mid-run interruptions, rate limits, circular dependencies, and billing renewals.

7. **Generate Cross-Platform, Agnostic Automation Gate (`scripts/pipeline.sh`):** Write an executable script that reads `.agents/environment.env`, executes the inferred build/test commands, invokes `scripts/heal-tests.sh` on test errors, and triggers circuit breaker rollbacks (`git checkout .`) upon consecutive failures.

8. **Generate Stack-Adaptive AST-Aware Codebase RAG Sync & Query Engine (`scripts/rag-sync.sh`):** Write an executable helper script that scans source files while honoring `.agents/IGNORE.md` and updates `.agents/vector-cache.json`.

9. **Generate Token Sharding & Conservation Engine (`scripts/context-guard.sh`):** Write a helper script enforcing predictive byte thresholds, AST trimming, and line-budget limits.

10. **Generate Autonomous Test Healer (`scripts/heal-tests.sh`):** Write a helper script that captures stderr outputs, maps failing assertions, and injects targeted test fixes into the active workspace.

11. **Generate Branch-Protected Release & Staged Versioning Engine (`scripts/release-sync.sh`):** Write a script tied to protected branch scopes parsing conventional commit prefixes to automate semantic version bumps.

12. **Generate AI Health-Check, Dynamic Model-Tier Router & Hibernation Scheduler (`scripts/router.sh`):** Write an executable bash script managing the Dynamic Model-Tier Matrix, HTTP quota headers, threshold hibernation schedules, and subscription renewal banners.

13. **Generate Resilient Recursive CLI Navigation System with Cross-Platform Safeguards (`scripts/auto-loop.sh`):** Write an industrial-grade script featuring signal trapping (`trap cleanup EXIT INT TERM`), platform-safe state-locking (`.agents/lock.sig`), interactive menu navigation supporting `--plan`, `--autonomous`, `--check`, `--suggestions`, and non-destructive workspace stashing on `Ctrl+C` (`git stash push -m "URACE auto-stash on abort"`).

14. **Generate Self-Updating Orchestrator Manager (`scripts/update-orchestrator.sh`):** Write an executable script handling safe pipeline maintenance and best-practice upgrades.

15. **Generate Automated Post-Bootstrap Setup & Verification (`scripts/init-env.sh`):** Set execution permissions (`chmod +x scripts/*.sh`), install the `.git/hooks/pre-commit` hook, and run initial heuristic detection and diagnostic health checks.

16. **Install Automated Git Pre-Commit Hook:** Create or update `.git/hooks/pre-commit` and ensure it invokes `scripts/pipeline.sh` before any commit is finalized.

17. **Final Output:** Present a clear summary confirming that the complete, truly file-base and project-type agnostic URACE bootstrap package is deployed, cryptographically secured, and fully operational.