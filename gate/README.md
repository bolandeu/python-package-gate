# rb-gate

The release gate of the CLI standard: `gate check`, run over the package in the
current directory. A package runs it from a release asset of this repository:

```sh
uvx --from https://github.com/bolandeu/python-package-gate/releases/download/v1.28.0/rb_gate-1.28.0-py3-none-any.whl gate check
```

or, once the distribution is on a package index, `uvx rb-gate gate check`.

`gate check` runs the package's locked install, linters, tests with the coverage
floor, the consumer contracts, a wheel build and install, the mandatory rules of
the Standard, and an osv audit. `gate check --keep-going` runs every step and
lists what failed; `gate check --project DIR` checks another package.

The version of the gate is the template version: this repository is a Copier
template, and both move with one tag.
