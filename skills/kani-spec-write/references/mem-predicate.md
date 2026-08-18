# Kani Memory Safety Primitives

## Validity Rules for Unsafe Memory Accesses in Rust

### Validity Rules

1. **Zero-sized accesses**: For memory accesses of size zero, **all pointers are valid**, including null pointers. All subsequent rules apply **only to non-zero-sized accesses**.

2. **Null pointers**: For non-zero-sized accesses, **null pointers are never valid**.

3. **Dereferenceability and allocation bounds**: A pointer is valid only if the memory range of the accessed size, starting at the pointer, lies entirely **within the bounds of a single allocated object**.
   - This condition is **necessary but not always sufficient**.
   - In Rust, each stack-allocated variable is treated as a **distinct allocated object**.

4. **Concurrency and atomicity**: All memory accesses are **non-atomic**.
   - It is undefined behavior to perform concurrent accesses to the same memory location from different threads unless **all accesses are reads**.
   - This includes `read_volatile` and `write_volatile`.
   - Volatile accesses **do not provide synchronization guarantees**.

5. **Reference-pointer interaction**: A raw pointer obtained by casting from a reference remains valid **only while the referenced object is live** and **no references are used to access the same memory**.
   - Reference accesses and raw pointer accesses **must not be interleaved**.

## Kani Primitives for Expressing Memory Validity

All functions are referred to by their fully qualified names: `kani::mem::<function>`.

### Pointer Validity and Dereferenceability

#### `pub fn can_dereference<T: ?Sized>(ptr: *const T) -> bool`

Returns true iff:
- `ptr` satisfies Validity Rules 1, 2, and 3, and
- the value stored at `ptr` satisfies the validity invariants of type `T`.

Alignment is required.

#### `pub fn can_read_unaligned<T: ?Sized>(ptr: *const T) -> bool`

Same as `can_dereference`, except:
- **alignment is not required.**

### Write Validity

#### `pub fn can_write<T: ?Sized>(ptr: *mut T) -> bool`

Returns true iff:
- `ptr` satisfies Validity Rules 1, 2, and 3, and
- `ptr` is properly aligned for type `T`.

This function **does not** check whether the stored value is valid for type `T`.

#### `pub fn can_write_unaligned<T: ?Sized>(ptr: *const T) -> bool`

Same as `can_write`, except:
- **alignment is not required.**

### Allocation and Layout Queries

#### `pub fn checked_align_of_raw<T: ?Sized>(ptr: *const T) -> Option<usize>`

Returns the alignment of the value pointed to by `ptr` if:
- alignment information is available,
- the alignment is a power of two.

Returns `None` otherwise.

#### `pub fn checked_size_of_raw<T: ?Sized>(ptr: *const T) -> Option<usize>`

Returns the size of the value pointed to by `ptr` if:
- no overflow occurs during size computation,
- the pointer's alignment is a power of two,
- the computed size does not exceed `isize::MAX`.

Returns `None` otherwise.

### Allocation Relationships

#### `pub fn same_allocation<T: ?Sized>(ptr1: *const T, ptr2: *const T) -> bool`

Returns true iff:
- `ptr1` and `ptr2` refer to the same allocated object, and
- both pointers are **in bounds** of that allocation.

A pointer is considered in bounds if it points **at most one byte past** the allocation.

**Restriction**: `T` **MUST NOT** be a zero-sized type (ZST). i.e, `ptr1` and `ptr2` **MUST NOT** point to ZSTs.

#### `pub fn is_inbounds<T: ?Sized>(ptr: *const T) -> bool`

Returns true iff:
- `ptr` points to an allocation that can hold a value of size determined by `T`.

**Behavior notes**:
- Always returns true if `T` is a ZST.
- If `T` is non-ZST, `ptr` **MUST NOT** be derived from a ZST allocation; otherwise Kani reports: `Kani does not support reasoning about pointer to unallocated memory`.
