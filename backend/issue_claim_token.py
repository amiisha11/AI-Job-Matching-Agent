"""Administrator claim codes are no longer issued.

Account setup sends a verification code to the profile email. This command
does not open the database and does not print a code.
"""


def main(argv: list[str] | None = None) -> int:
    del argv
    print("Administrator claim codes are retired. Use Account setup to verify the email.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
