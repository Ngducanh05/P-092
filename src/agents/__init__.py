"""Self Dev v2 AI package boundary.

The old generic chat/demo LangGraph was removed because it was not part of the
FixIt product contract. Production AI execution is intentionally not faked here:
`src.models.agent_schemas` is the authoritative Backend <-> Agent contract until
the real multimodal extraction graph/worker is implemented.
"""
