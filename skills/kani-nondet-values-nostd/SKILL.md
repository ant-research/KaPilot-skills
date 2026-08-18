---
name: kani-nondet-values-nostd
description: Construct no_std-compatible nondeterministic Rust values for Kani harnesses, including constrained primitives, references, slices, strings, arrays, enums, and structs.
---

# Kani Nondeterministic Value Construction for no_std Harnesses

This guide shows how to build well-typed nondeterministic values for Rust code verified with Kani in no_std-style harnesses.

## Primitives

### `kani::any()`

Basic nondeterministic value generation.

### `kani::any_where(predicate)`

Generate nondeterministic value satisfying a predicate.

```rust
kani::any_where(|n: &T| *n <= max && *n >= min)
```

### `kani::assume(condition)`

Assume condition holds (constrain the nondeterministic value).

## Integer Types

### Signed / Unsigned Integers

```rust
// T: i8, i16, i32, i64, i128, isize, u8, u16, u32, u64, u128, usize
fn __verifier_nondet_int<T>(min: T, max: T) -> T {
    kani::any_where(|n: &T| *n <= max && *n >= min)
}
```

### Booleans

```rust
fn __verifier_nondet_bool() -> bool {
    kani::any()
}
```

### Floats

```rust
// T: f32 or f64
fn __verifier_nondet_float<T>(min: T, max: T) -> T {
    kani::any_where(|n: &T| *n <= max && *n >= min)
}
```

### Char

```rust
fn __verifier_nondet_char() -> char {
    kani::any::<char>()
}
```

## Reference Types

### &T

Create non-deterministic data for T first, then create a reference. Do NOT wrap into a function.

```rust
let non_det_T = __verifier_nondet_<T>();
let var: &T = &non_det_T;
```

## Option and Tuple

### Option<T>

```rust
let non_det_T = __verifier_nondet_<T>();
let option: Option<T> = if __verifier_nondet_bool() { Some(non_det_T) } else { None };
```

### Tuple

```rust
fn __verifier_nondet_tuple<T1, T2, TN>() -> (T1, T2, TN) {
    kani::any()
}
```

## Array Types

### [T; N]

Fixed-size arrays. Use `kani::any()` directly if T implements Arbitrary.

```rust
// [T; N] where T: Arbitrary
let arr: [u8; 16] = kani::any();
```

For custom types, construct element by element:

```rust
fn __verifier_nondet_array<T, const N: usize>() -> [T; N]
where
    T: Default + Copy + kani::Arbitrary,
{
    [kani::any(); N]
}
```

## Slice Types

### &[T] (Slice)

Create nondeterministic array first, then convert to slice. Do NOT wrap into a function.

```rust
let arr: [T; SLICE_MAX_LEN] = kani::any();
let slice: &[T] = &arr;
```

## String Types

### String

Use nondeterministic array of bytes, then convert to String. Note: The `len` parameter is used to create a slice of the nondeterministic array.

```rust
const MAX_STRING_LEN: usize = 256;

fn __verifier_nondet_string(len: usize) -> alloc::string::String {
    assert!(len <= MAX_STRING_LEN);
    // Create nondeterministic bytes array
    let bytes: [u8; MAX_STRING_LEN] = kani::any();
    // Use only the first `len` bytes
    let s = alloc::string::String::from_utf8(bytes[..len].to_vec());
    kani::assume(s.is_ok());
    s.unwrap()
}
```

### &str

Use `Box::leak` to convert String to &'static str. This is the correct way to return a `&str` from a function - `Box::leak` explicitly leaks the allocated memory and returns a reference with `'static` lifetime.

```rust
const MAX_STR_LEN: usize = 256;

pub fn __verifier_nondet_str(len: usize) -> &'static str {
    assert!(len <= MAX_STR_LEN);
    let bytes: [u8; MAX_STR_LEN] = kani::any();
    if let Ok(s) = alloc::string::String::from_utf8(bytes[..len].to_vec()) {
        // Box::leak returns &'static str - this is correct Rust, not returning a local
        Box::leak(s.into_boxed_str())
    } else {
        // Fallback for invalid UTF-8
        Box::leak(alloc::string::String::from("").into_boxed_str())
    }
}
```

## User-Defined Types

### Enum

Use a nondeterministic integer to select variants.

```rust
enum T {
    A,
    B,
    C([u8; 20]),
    D(u8),
}

fn __verifier_nondet_enum_T() -> T {
    let v = [kani::any::<u8>(); 20];
    let u = __verifier_nondet_int::<u8>(0, 10);

    let n: u8 = kani::any(); // Selector for enum variants
    match n {
        0 => T::A,
        1 => T::B,
        2 => T::C(v),
        _ => T::D(u),
    }
}
```

### Struct

Recursive construction - create nondeterministic types for members first.

```rust
struct P { a: usize }
struct U { a: u8, p: P, c: [u8; 4] }
struct T { u: U }

fn __verifier_nondet_struct_P() -> P {
    let a = __verifier_nondet_int::<usize>(0, 10);
    P { a }
}

fn __verifier_nondet_struct_U() -> U {
    let a = __verifier_nondet_int::<u8>(0, 10);
    let p = __verifier_nondet_struct_P();
    let c = [kani::any::<u8>(); 4];
    U { a, p, c }
}

fn __verifier_nondet_struct_T() -> T {
    let u = __verifier_nondet_struct_U();
    T { u }
}
```
