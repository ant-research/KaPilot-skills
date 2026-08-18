### Example 1: Split Safety Conditions

Source:
```rust
/// # Safety
/// The pointer must be non-null and properly aligned.
pub const unsafe fn new_unchecked(ptr: *mut T) -> NonNull<T>
```

Output:
```
## Safety Requirements for `new_unchecked`

### RQ-1:
The pointer `ptr` must not be null. [TF-Safety: The pointer must be non-null]

### RQ-2:
The pointer `ptr` must be properly aligned. [TF-Safety: and properly aligned]
```

### Example 2: Safety and Panic Extraction

Source:
```rust
/// # Safety
/// The pointer must be valid for reading.
///
/// # Panics
/// Panics if `index` is out of bounds.
pub unsafe fn read_at(ptr: *const T, index: usize) -> T
```

Output:
```
## Safety Requirements for `read_at`

### RQ-1:
The pointer `ptr` must be valid for reading. [TF-Safety: The pointer must be valid for reading]

### RQ-2:
The index `index` must be within bounds. [TF-Panics: Panics if `index` is out of bounds]
```

### Example 3: Ignore Implementation Comments

Source:
```rust
/// # Safety
/// The pointer must be non-null.
pub unsafe fn write_value(ptr: *mut u32, value: u32) {
	// SAFETY: The caller guarantees `ptr` is properly aligned.
	unsafe { ptr.write(value); }
}
```

Output:
```
## Safety Requirements for `write_value`

### RQ-1:
The pointer `ptr` must not be null. [TF-Safety: The pointer must be non-null.]
```

Why:
- Extract only from the target function's preceding doc comment.
- Do NOT extract "`ptr` must be properly aligned" from the implementation comment `// SAFETY:`.

### Example 4: Read Cross-Referenced Safety Docs

Source:
```rust
/// # Safety
/// See [`Vec::from_raw_parts`] for additional safety requirements.
pub unsafe fn from_raw_parts_in(ptr: *mut T, len: usize, cap: usize) -> Vec<T>
```

Output:
```
## Safety Requirements for `from_raw_parts_in`

### RQ-1:
The pointer `ptr` must have been allocated with the global allocator. [CR-Safety: The allocated memory must have been allocated using the global allocator]

### RQ-2:
The generic type `T` must have the same alignment as the type used to allocate `ptr`. [CR-Safety: `T` needs to have the same alignment as what `ptr` was allocated with]
```

Why:
- Locate and read the referenced documentation for `Vec::from_raw_parts` before extracting any `CR-*` requirement.
- Do NOT infer cross-referenced requirements from the function name alone.
- Extract only the referenced `# Safety`, `# Panics`, and safety-relevant behavior statements.

### Example 5: Map Cross-Referenced Variables

Source:
```rust
/// # Safety
/// See [`slice::from_raw_parts`] for the pointer validity requirements.
pub unsafe fn view_bytes<'a>(buffer: *const u8, count: usize) -> &'a [u8]
```

Output:
```
## Safety Requirements for `view_bytes`

### RQ-1:
The pointer `buffer` must be non-null and valid for reads of `count` bytes. [CR-Safety: `data` must be non-null and valid for reads for `len * size_of::<T>()` many bytes]
```

Why:
- Read the referenced documentation for `slice::from_raw_parts` first.
- Map the referenced variable names to the target function's interface before writing the requirement.
- Use the target function's parameter names, so write `buffer` and `count`, not `data` and `len` from the referenced function.
- The target function is concrete over `u8`, so the rewritten requirement should stay concrete instead of inventing a new generic parameter.
