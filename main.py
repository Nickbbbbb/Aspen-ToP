from aspen_to_top.main import main


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"操作失败: {exc}")
        raise SystemExit(1)
