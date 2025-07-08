# Git Flow for Odoo Projects

## Purpose

This guide defines the process of preparing tasks for deployment for code review, staging and production environments.

## How to prepare branches without cherry-picks

The cherry-picks is not desired, because they obscure the git history and produce "strange" diffs.
To avoid them we suggest the following workflow when you are starting work on a new feature or bugfix:

1. Make branch from Production (default) branch
2. Implement feature or fix the bug in the new branch
3. Check if there are any conflicts with the Staging branch
4. If NO: prepare a PR into Staging branch
5. If YES: prepare a new branch from the Staging branch and merge your feature branch into it, create a PR for the new branch into Staging branch
6. The PR will be merged to staging and tested
7. If improvement is needed, make fixes in your original feature branch and repeat steps 2-6
8. If everything is OK, prepare a PR into Production branch
9. The task will be merged to production

```mermaid
flowchart TD
    A([Start: Branch from Production]) --> B[Implement feature or bugfix]
    B --> C{Conflicts with Staging?}
    C -- No --> D[Prepare PR into Staging branch]
    C -- Yes --> E1[Branch from Staging]
    E1 --> E2[Merge feature branch]
    E2 --> E3[PR into Staging]
    D & E3 --> F[PR merged & tested in Staging]
    F --> G{Improvement needed?}
    G -- Yes --> B
    G -- No --> H[Prepare PR into Production branch]
    H --> I[Task merged to Production]
