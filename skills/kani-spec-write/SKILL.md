---
name: kani-spec-write
description: How to write Kani specifications using Kani primitives. Use this skill whenever you need to write any kind of Kani spec — function contracts (preconditions, postconditions, write sets, history expressions), type invariants, loop invariants, or memory predicates. Invoke this whenever writing or reviewing Kani proof harnesses or specifications, adding kani::requires/ensures/modifies, implementing kani::Invariant, annotating loops with loop_invariant/loop_modifies, or using kani::mem predicates.
---

# Kani Spec Writing Guide

Kani specifications describe *what* a function, type, or loop must guarantee — separate from *how* the implementation achieves it. Well-written specs let Kani verify safety properties exhaustively over all possible inputs.

There are four kinds of specs in Kani:

| Spec type | What it expresses | Primary primitives |
|-----------|------------------|--------------------|
| **Function contracts** | Preconditions + postconditions on a function | `#[kani::requires]`, `#[kani::ensures]`, `#[kani::modifies]`, `old()` |
| **Type invariants** | Safety invariants for a user-defined type | `impl kani::Invariant` |
| **Loop invariants** | Properties that hold at every iteration | `#[kani::loop_invariant]`, `#[kani::loop_modifies]` |
| **Memory predicates** | Raw pointer/memory validity conditions | `kani::mem::can_dereference`, `can_write`, `is_inbounds`, etc. |

## Choosing the Right Spec Type

- **Verifying a function's input/output contract** → use [function contracts](references/pre-post-conditions.md)
- **Expressing what states are safe for a struct/enum** → use [type invariants](references/type-invariant.md)
- **Helping Kani reason through a loop without unrolling** → use [loop invariants](references/loop-invariant.md)
- **Checking unsafe pointer operations** → use [memory predicates](references/mem-predicate.md)

Read only the reference(s) relevant to the spec you are writing:

- `references/pre-post-conditions.md` — `#[kani::requires]`, `#[kani::ensures]`, `#[kani::modifies]`, `old()`
- `references/type-invariant.md` — `kani::Invariant` trait and `is_safe()`
- `references/loop-invariant.md` — `#[kani::loop_invariant]`, `#[kani::loop_modifies]`
- `references/mem-predicate.md` — `kani::mem::can_dereference`, `can_write`, `same_allocation`, `is_inbounds`, etc.

## General Principles

**Side-effect freedom**: All spec expressions — conditions in `requires`, closures in `ensures`, loop invariant conditions — must be side-effect free. No I/O, no mutation. Kani evaluates these symbolically; mutations would corrupt the proof state.

**Use `old(..)` for change-tracking**: When the postcondition needs to reference the pre-call state of a mutable argument, use `old(expr)` inside `ensures`. This is the only correct way — don't try to save pre-state manually.

**Use `modifies(..)` for writes**:  Identify type definitions to determine which field, element, or subobject is actually modified, and use a pointer expression to specify that location precisely.

**Type invariants encode safety assumptions**: Implementing `kani::Invariant` lets you write `assume(val.is_safe())` to constrain symbolic inputs to states that satisfy the type's safety invariant, and `assert!(val.is_safe())` to prove those invariants are preserved where needed.

**Keep write sets narrow**: When using loop or function contracts, specify the smallest `loop_modifies` or `modifies` set that covers the mutations you expect. Over-approximated write sets make proofs weaker and harder to use.
