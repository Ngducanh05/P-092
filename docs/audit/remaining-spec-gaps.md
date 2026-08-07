# Remaining Specification Gap — Technician Phase

## Secure completion evidence

Lead requirements require a Technician to attach a completion photo before marking work complete. The current upload-session contract is Resident-owned, so reusing it would violate ownership and could expose raw Storage paths.

Current safe behavior:

- `AssignmentStatus.COMPLETED` remains part of the domain contract.
- A completion request returns `COMPLETION_EVIDENCE_REQUIRED`.
- Raw object paths and Resident upload IDs are not accepted as Technician evidence.

Required follow-up:

1. create Technician-owned signed upload sessions;
2. verify object ownership, MIME type, size, expiry, and one-time consumption;
3. classify the resulting attachment as completion evidence;
4. atomically transition assignment/ticket state, append history/audit, and notify the Resident.
