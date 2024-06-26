## Contribution
The guidelines below are a set of best practices for managing Git workflows in our development team. Here’s a detailed explanation:

### Branch Naming Conventions

Branch names should be descriptive and follow a specific format:
1. **Feature branches**: `feature/billing`
   - Used for developing new features.
2. **Bug fix branches**: `bug/login-bug`
   - Used for fixing bugs.
3. **Fix branches**: `fix/user-data-leak`
   - Used for quick fixes that don't fit the typical bug fix category, often security-related.
4. **UI update branches**: `ui/login-page-update`
   - Used for user interface updates.
5. **Refactor branches**: `refactor/restructure-database`
   - Used for code refactoring.

### Commit Message Conventions

Commit messages should be clear and follow a specific format:
1. **Add new functionality**: `add(added a new payment functionality): Extended description if there is one`
   - Use `add` for new features or additions.
2. **Fix a bug**: `fix(fixed login bug)`
   - Use `fix` for bug fixes.

### Rebase Workflow

Instead of using merge commits to integrate changes from different branches, the team should use rebasing. Rebasing helps keep a linear project history. Here’s what it means and how to do it:

1. **Rebase against the `dev` branch before submitting a Pull Request (PR)**:
   - Before you create a PR for your branch, make sure it is up-to-date with the `dev` branch. This involves rebasing your branch on top of the latest `dev` branch.
   - This ensures that your branch is compatible with the latest changes and reduces the likelihood of conflicts.

2. **Rebase your branches against `dev`**:
   - Fetch the latest changes from the `dev` branch.
   - Rebase your branch on top of `dev`.

#### Example Workflow:

1. **Creating a Feature Branch**:
   ```sh
   git checkout -b feature/billing
   ```

2. **Making Commits**:
   ```sh
   git add .
   git commit -m "add(added a new payment functionality): Implemented billing module"
   ```

3. **Rebasing Before PR**:
   ```sh
   git fetch origin
   git checkout dev
   git pull origin dev
   git checkout feature/billing
   git rebase dev
   ```

4. **Handling Conflicts During Rebase**:
   - If there are conflicts, Git will pause and allow you to resolve them.
   - After resolving conflicts, continue the rebase:
     ```sh
     git rebase --continue
     ```

5. **Submitting a PR**:
   - Once the rebase is complete and your branch is up-to-date with `dev`, push the changes:
     ```sh
     git push -f origin feature/billing
     ```
   - Create a PR from `feature/billing` to `dev`.

### PR Review Guidelines

1. **No Review Needed for Non-Code Changes**:
   - If your branch doesn't contain changes to existing code (e.g., documentation updates, non-code files), you can rebase and merge without needing a review.

2. **Rebasing Only, No Merge Commits**:
   - The project history should remain linear, so always use rebasing instead of merging.
   - This means avoiding merge commits like "Merge branch 'dev' into feature/billing".
   - If you are in charge of the PR, use `Rebase and merge` option to rebase it with the `Dev` branch.

### Summary

- **Branch names** should follow a specific format based on the type of change.
- **Commit messages** should be clear and follow a specific format.
- **Rebase** your branches against `dev` before creating a PR to keep history linear and conflicts minimal.
- **Always use rebasing**, no merge commits allowed.

Following these guidelines helps maintain a clean and understandable project history, reduces conflicts, and ensures a smooth workflow.