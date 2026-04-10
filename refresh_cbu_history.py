from main import DEFAULT_CBU_HISTORY_DAYS, refresh_cbu_history


def main():
    refresh_cbu_history(days=DEFAULT_CBU_HISTORY_DAYS, verbose=True)


if __name__ == "__main__":
    main()
