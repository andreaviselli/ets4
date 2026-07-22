# Package and release plan

Last updated: 2026-07-22

ETS4 already has a standard `src/` layout, a `pyproject.toml`, an `ets4` command, packaged prompt files, and a wheel that builds successfully. The next goal is a repeatable install and release process. A public package must not be claimed until every release check below passes.

## Step 1: make local installs clear — done

- Keep end-user setup (`pip install .`) separate from editable developer setup (`pip install -e ".[dev]"`).
- Support both `ets4` and `python -m ets4`.
- Keep package code under `src/ets4/`, tests under `tests/`, and human-scored cases under `evals/`.
- Keep prompt text inside the package and check that every version is present in the wheel.
- Remove tracked placeholders and one-off command notes left by the old product.

## Step 2: finish release metadata

- Choose and add a project licence. This needs an owner decision; do not guess one.
- Add maintainer details and a changelog.
- Use one source for the package version instead of repeating it in `pyproject.toml` and `ets4.__init__`.
- Review lower and upper dependency bounds against a clean Python 3.12 environment.
- Decide which operating systems are supported after testing PDF handling on each one.

## Step 3: test the built package

- Build both a wheel and source archive in CI.
- Inspect them for prompt assets, `py.typed`, and accidental local files.
- Install the wheel into a clean Python 3.12 environment.
- Run `ets4 --help`, `python -m ets4 --help`, config validation, and a full mock review from outside the repository.
- Run the normal test, lint, type, compile, path, secret, and diff checks before every release.

## Step 4: publish safely

- Create a test release first and verify installation by package name.
- Use trusted publishing from a protected release workflow; do not store a long-lived package-registry token in the repository.
- Tag the exact reviewed commit and attach checksums and short release notes.
- Publish to the main package index only after the test release and licence decision are complete.

After publication, the README can replace the checkout instructions with `pip install ets4`. Until then, installing from this repository is the supported package path.
