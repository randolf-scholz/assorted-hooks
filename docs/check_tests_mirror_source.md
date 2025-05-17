# check-tests-mirror-source

Checks that the folder structure of the `tests/` directory mirrors the folder structure of the `src/` directory.

1. Checks that for each directory in `src/`, there is a corresponding directory in `tests/`.
2. Checks that each directory in `tests/`, whose top level folder is contained in `src/`, has a corresponding directory in `src/`.
