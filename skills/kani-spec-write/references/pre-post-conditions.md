# Kani Contracts: Pre/Post Conditions

## Precondition: `#[kani::requires(cond)]`

Adds a function precondition.

**Constraints:**
- `cond` MUST be a boolean condition over the function inputs
- `cond` MUST hold at function entry
- `cond` MAY use arbitrary Rust expressions and function calls
- All computations in `cond` MUST be side-effect free (no I/O, no mutation)

```rust
#[kani::requires(divisor != 0)]
fn my_div(dividend: usize, divisor: usize) -> usize {
    dividend / divisor
}
```

## Postcondition: `#[kani::ensures(closure)]`

Adds a function postcondition.

**Constraints:**
- `closure` MUST capture the function inputs
- The closure argument is the function return value, passed by reference: `|result: &<ret_type>| { ... }`
- The postcondition MUST hold at function exit
- `closure` MAY use arbitrary Rust expressions and function calls
- All computations in `closure` MUST be side-effect free

```rust
#[kani::requires(divisor != 0)]
#[kani::ensures(|result : &usize| *result <= dividend)]
fn my_div(dividend: usize, divisor: usize) -> usize {
    dividend / divisor
}
```

## Write Sets: `#[kani::modifies(expr)]`

Declares the explicit write-set of the annotated function: each `modifies(expr)` entry identifies a memory location that the function is allowed to write through.

**Constraints:**
- Each `expr` MUST be a pointer expression derived from a function argument
- Each `expr` MUST evaluate to a pointer type (`*const T`, `*mut T`, `&T` or `&mut T`)
- The pointed-to type MUST implement `Arbitrary`
- `expr` MAY use arbitrary Rust expressions and function calls
- All computations in `expr` MUST be side-effect free

Use `modifies` when the contracted function performs writes:
- Inspect the relevant type definitions, identify the field actually modified, and use a pointer expression to identify that location precisely. Use that pointer expression in `modifies`.
- For `&mut` arguments, using the argument directly in `modifies` is valid

```rust
#[kani::modifies(ptr, my_box.as_ref())]
fn a_function(ptr: &mut u32, my_box: &mut Box<u32>) {
    *ptr = 80;
    *my_box.as_mut() = 90;
}
```

## History Expressions: `old(expr)`

Refers to the value of `expr` at function entry.

**Constraints:**
- `old(expr)` MAY appear only in `ensures` clauses
- `expr` MUST be effect free and closed with respect to the function arguments
- `old(expr)` is evaluated before function execution

```rust
#[kani::modifies(a)]
#[kani::ensures(|result| old(*a).wrapping_add(1) == *a)]
#[kani::ensures(|result : &u32| old(*a).wrapping_add(1) == *result)]
fn add1(a : &mut u32) -> u32 {
    *a = a.wrapping_add(1);
    *a
}
```
