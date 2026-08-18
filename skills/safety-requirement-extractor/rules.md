### R1: Atomicity
- Each requirement MUST be exactly ONE sentence
- Each requirement MUST describe EXACTLY ONE safety property
- Split multi-condition statements into separate atomic requirements
- Be more concise than or equal to the original source

### R2: Variable References
- Reference ONLY: function parameters, return value, or generics
- Use backticks: `` `ptr` ``
- Do NOT reference local variables in implementation
- Do NOT replace target-function generics with concrete types
- If the target function already uses concrete types, express the requirement using that concrete target-function interface
- For cross-referenced requirements, map referenced variables to the target function's parameters, return value, or generics before writing the requirement
- Do NOT keep variable names from the referenced function unless they refer to the same target-function symbol
- If a referenced variable cannot be mapped confidently to the target function's interface, do NOT extract that requirement as written

### R3: Memory Safety and Panic Focus
- MUST constrain memory safety or Rust runtime panics
- Exclude compile-time behaviors
- Exclude properties unrelated to safety
- Apply the same focus to cross-referenced material: extract ONLY `# Safety`, `# Panics`, and behavior statements about memory safety or runtime panics

### R4: Source Traceability
- End each requirement with citation: `. [...]`
- See citation formats below for allowed sources
- Citation MUST be findable in source
- Citation MUST come from the target function's preceding doc comment or from an explicit cross-reference mentioned there
- Do NOT cite implementation comments inside the function body such as `// SAFETY:`
- Do NOT cite or summarize a cross-reference based only on its name or surrounding hint text

### R5: Scope and Strength
- Constrain ONLY **safety- or panic-relevant conditions** on the **target function's parameters, return value, or generics**
- Do NOT describe usage patterns, scenarios, purposes, or other non-safety context for the target function
- Do NOT restate Rust type system guarantees, trait bounds, or obligations that are unrelated or apply only after the function returns


### R6: Exclusivity
- No duplicate requirements
- No logical implications between requirements
- No contradictions between requirements

### R7: Completeness
- Cover ALL safety constraints from allowed sources
- Allowed sources are the target function's preceding doc comment and any explicit cross-references required to interpret it
- If the doc comment explicitly points to another source for safety or panic semantics, read that source before deciding whether extraction is complete
- Do NOT extract unrelated semantics from a referenced document just because the document was referenced


#### Citation Formats for R4:

| Source Type | Citation Prefix |
|-------------|----------------|
| Safety section | `TF-Safety:` |
| Panics section | `TF-Panics:` |
| Behavior (safety-related) | `TF-Behavior:` |
| Cross-ref Safety | `CR-Safety:` |
| Cross-ref Panics | `CR-Panics:` |
| Cross-ref Behavior | `CR-Behavior:` |
