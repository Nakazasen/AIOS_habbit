# Data Flow

## Main Flow

```text
1. Source discovery
2. Source inventory
3. Evidence record creation
4. Candidate extraction
5. Human/AI review
6. Validated memory promotion
7. Master profile update
8. AI export pack generation
9. Periodic review/deprecation
```

## No-Raw-Chat Flow

```text
Chat transcript
  -> identify useful pattern
  -> create evidence summary
  -> extract candidate memory
  -> discard or local-only raw transcript
```

## Conflict Flow

```text
New evidence contradicts memory
  -> mark memory as conflicted
  -> create conflict entry
  -> review evidence strength
  -> update/deprecate/split memory
```
