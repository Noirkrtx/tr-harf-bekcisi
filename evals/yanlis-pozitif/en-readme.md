# Task runner

A small task runner for monorepos. It reads `tasks.yaml`, builds a dependency graph and runs each task once. If a task fails, the runner stops and prints the last fifty lines of its output.

## Install

```bash
pip install task-runner
```

Set `TASK_RUNNER_CACHE` to change the cache folder. On Windows the default is under your user profile. Is it safe to delete the cache? Yes, it will be rebuilt on the next run.
