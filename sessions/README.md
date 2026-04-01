# Sessions

This top-level directory is reserved for shared session artifacts if the system
later needs a cross-user or cross-terminal session registry.

The current preferred model is still:

- user-scoped session history under `users/{user_id}/.../sessions/`

This directory remains available for future global indexes or session lookup
tables if needed.
