# Kani Loop Invariants

## `#[kani::loop_invariant(cond)]`

Attaches a loop invariant to a loop.

**Constraints:**
- This attribute MUST appear **before** the loop (i.e., before the `while` keyword)
- `cond` MUST hold at the beginning of every loop iteration
- `cond` MAY use arbitrary Rust expressions, including function calls
- All computations in `cond` MUST be side-effect free (no I/O and no mutation of memory)

## `#[kani::loop_modifies(expr)]`

Specifies the set of memory locations that may be modified inside the loop body.

**Constraints:**
- Only the memory described by `expr` is allowed to be mutated in the loop
- Variable names themselves are not valid targets; mutations are tracked via pointers or references
- The expression MUST evaluate to one of the following forms:

### 1. RawPtr (`*const T` or `*mut T`)

Used to specify a single memory location via its address.

```rust
#[kani::proof]
fn main() {
    let mut i = 0;
    #[kani::loop_invariant(i <= 20)]
    #[kani::loop_modifies(&i as *const _)]
    while i < 20 {
        i = i + 1;
    }
}
```

### 2. Reference (`&T` or `&mut T`)

Used to allow mutation of the referenced object.

```rust
#[kani::proof]
fn main() {
    let mut i = 0;
    let mut a: [u8; 20] = kani::any();
    #[kani::loop_invariant(i <= 20)]
    #[kani::loop_modifies(&i, &a)]
    while i < 20 {
        a[i] = 1;
        i = i + 1;
    }
}
```

### 3. FatPtr (Slice)

Used to allow mutation of a contiguous memory range.

```rust
#[kani::proof]
fn main() {
    let mut i = 3;
    let mut a: [u8; 100] = kani::any();
    #[kani::loop_invariant(i >= 3 && i <= 20)]
    #[kani::loop_modifies(&i, &a[3..20])]
    while i < 20 {
        a[i] = 1;
        i = i + 1;
    }
}
```

Or using `core::ptr::slice_from_raw_parts`:

```rust
#[kani::proof]
fn main() {
    let mut i = 0;
    let mut a: [u8; 100] = kani::any();
    #[kani::loop_invariant(i <= 20)]
    #[kani::loop_modifies(&i, core::ptr::slice_from_raw_parts(a.as_ptr(), 20))]
    while i < 20 {
        a[i] = 1;
        i = i + 1;
    }
}
```
