"""Run the same CLI when invoked with python -m nilavu."""

from nilavu.cli import main


# A console script performs this conversion too: the return value becomes the
# process exit status that shells and scripts can inspect.
if __name__ == "__main__":
    raise SystemExit(main())
