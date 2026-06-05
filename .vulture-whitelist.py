# Vulture whitelist — symbols that are "used" via pytest fixtures or dynamic dispatch.
# flake8: noqa

# pytest fixtures (used for side-effects, not directly referenced in test bodies)
cron_env
sample_job
clean_infra

# Module-level singleton intentionally exported
infra

# Dynamic dispatch / registry patterns
registry
handler
