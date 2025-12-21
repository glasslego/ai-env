---
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
license: Complete terms in LICENSE.txt
---

# Skill Creator

Skills are modular packages that extend Claude's capabilities with specialized knowledge, workflows, and tools.

## Core Principles

- **Concise is key**: Context window is shared. Only add what Claude doesn't already know. Prefer examples over explanations.
- **Degrees of freedom**: Match specificity to fragility. Fragile operations need exact scripts; flexible tasks need text guidance.

## Skill Anatomy

```
skill-name/
├── SKILL.md              # Required: frontmatter + instructions
├── scripts/              # Executable code for deterministic tasks
├── references/           # Documentation loaded as needed
└── assets/               # Files used in output (templates, images)
```

### SKILL.md Structure

```yaml
---
name: skill-name
description: What this skill does and when to use it.
  Include specific triggers (e.g., "Use when user asks to...").
  This is the ONLY field Claude reads to decide when to trigger.
---
```

Body: Instructions loaded AFTER triggering. Keep under 500 lines.

### Progressive Disclosure

1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers
3. **Bundled resources** - As needed (scripts can execute without reading)

**Pattern**: Keep core workflow in SKILL.md. Move variant-specific details to `references/`.

```
# Example: domain-specific organization
bigquery-skill/
├── SKILL.md (overview + navigation)
└── references/
    ├── finance.md
    ├── sales.md
    └── product.md
```

### What NOT to Include

- README.md, CHANGELOG.md, INSTALLATION_GUIDE.md
- Setup/testing procedures, user-facing documentation
- Information Claude already knows

## Creation Process

### Step 1: Understand with Examples

Ask the user for concrete usage examples:
- "What functionality should this skill support?"
- "What would a user say to trigger this skill?"

### Step 2: Plan Reusable Resources

For each example, identify:
- **Scripts**: Code rewritten repeatedly → `scripts/`
- **References**: Schemas, APIs, domain knowledge → `references/`
- **Assets**: Templates, boilerplate → `assets/`

### Step 3: Initialize

```bash
scripts/init_skill.py <skill-name> --path <output-directory>
```

Creates template SKILL.md + example directories.

### Step 4: Implement

1. Create bundled resources (scripts, references, assets)
2. Test scripts by running them
3. Write SKILL.md:
   - Frontmatter: `name` + `description` (include all trigger conditions)
   - Body: Instructions for using the skill and its resources
4. Delete unused example files from init

Design patterns: See `references/workflows.md` and `references/output-patterns.md`.

### Step 5: Package

```bash
scripts/package_skill.py <path/to/skill-folder>
```

Validates (frontmatter, naming, structure) then creates `.skill` zip file.

### Step 6: Iterate

Use the skill on real tasks → notice struggles → update SKILL.md/resources → test again.
