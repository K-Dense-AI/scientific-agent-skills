---
name: symcli-skill
description: Execute SymCLI to solve math equations, optimize tensor graphs, or analyze C# code for vulnerabilities. Use when you need a deterministic 'System 2' math engine to prevent hallucination.
version: 1.1.0
license: MIT
metadata:
    author: Warren Harding
    project: Sym
---

# SymCLI Skill

SymCLI is a pure C# symbolic computation framework designed to act as an exact mathematical engine and code analyzer. 

## 1. Overview
**Goal:** Provide a deterministic "System 2" thinking brain for AI agents to solve math and analyze code without hallucination.

SymCLI prevents the common pitfalls of LLMs when dealing with complex algebra, calculus, or security-sensitive code analysis. By using formal rewrite rules and an EGraph-based solver, it ensures that every result is mathematically sound and verifiable.

## 2. When to Use This Skill
**Goal:** Identify the correct scenarios for invoking SymCLI.

- **Algebraic Solving:** Solving equations, simplifying expressions, or factoring polynomials.
- **Calculus:** Computing derivatives, integrals, or limits symbolically.
- **Tensor Optimization:** Optimizing expression graphs for deep learning (e.g., matrix chain re-association, scale folding).
- **C# Code Analysis:** Scanning source code for mathematical correctness (`CSMATH`) or security vulnerabilities (`CSSEC`).
- **Exact Results:** When you need `sqrt(2)` or `pi` instead of numerical approximations.

## 3. Primary Workflows
**Goal:** Execute the correct commands for the task at hand.

### Solving ProblemScript (`.ps`)
1. Create a `.ps` file containing your options and equations.
2. Execute: `symcli.bat <input.ps> <output.txt>` (Windows) or `./symcli.sh <input.ps> <output.txt>` (Unix).
3. Read `<output.txt>` for the symbolic solution.

### Analyzing C# Code
1. Execute: `symcli.bat analyze csharp-math <input_path> <output_report> [options]`
2. Use `--json` for machine-readable output.

## 4. Instructions & Examples
**Goal:** Detailed patterns for agent usage.

### Example: Solving a Quadratic Equation
Write `problem.ps`:
```xml
<Options>
  Target: x
  RulePacks: Algebraic
</Options>
x^2 - 5*x + 6 = 0
```
Execute: `symcli.bat problem.ps result.txt` -> Returns `x = 2, x = 3`.

### Example: Symbolic Derivative
Write `calc.ps`:
```xml
<Options>
  Target: diff(sin(x^2), x)
  RulePacks: Calculus
</Options>
```
Execute: `symcli.bat calc.ps result.txt` -> Returns `2*x*cos(x^2)`.

## 5. Exit Codes
**Goal:** Handle runtime results programmatically.

- `0`: Success
- `1`: Configuration/Argument Error
- `2`: Solving failed (diagnostics written)
- `3`: Unexpected runtime exception
- `4`: Findings present (if `--fail-on-findings` used)

## 6. Best Practices
**Goal:** Maximize accuracy and performance.

- **Use RulePacks:** Explicitly specify `Algebraic`, `Calculus`, or `Tensor` in your options to guide the solver.
- **Assumptions:** Specify variable domains (e.g., `real`, `integer`) in the options when possible.
- **JSON Output:** Always use `--json` for automated analysis tasks to prevent parsing errors.
