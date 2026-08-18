# Kani Invariant Trait

The `Invariant` trait specifies **type-level safety invariants** and is used to check whether values of a type are safe.

```rust
pub trait Invariant where Self: Sized {
    // Required method
    fn is_safe(&self) -> bool;
}
```

An implementation of `Invariant` defines the conditions under which a value of the type is considered safe.
This trait is primarily intended for **user-defined types**.

## Required Methods

```rust
fn is_safe(&self) -> bool;
```

Returns `true` iff the value satisfies all safety invariants of the type.

## Example

Let's say you're creating a type that represents a date:

```rust
#[derive(kani::Arbitrary)]
pub struct MyDate {
  day: u8,
  month: u8,
  year: i64,
}
```

You can specify its safety invariant as:

```rust
impl kani::Invariant for MyDate {
  fn is_safe(&self) -> bool {
    self.month > 0
      && self.month <= 12
      && self.day > 0
      && self.day <= days_in_month(self.year, self.month)
  }
}
```

And use it to check that your APIs are safe:

```rust
#[kani::proof]
fn check_increase_date() {
  let mut date: MyDate = kani::any();
  kani::assume(date.is_safe());
  // Increase date by one day
  increase_date(&mut date, 1);
  assert!(date.is_safe());
}
```

## Built-in `Invariant` Implementations

The following types already implement `Invariant`:

`()`, `bool`, `char`, `f16`, `f32`, `f64`, `f128`, `i8`, `i16`, `i32`, `i64`, `i128`, `isize`, `u8`, `u16`, `u32`, `u64`, `u128`, `usize`

For these built-in types, the implementation is trivial: `is_safe()` always returns `true`.
