"""Checks for the local textbook catalog and the fuzzy topic search in book_sources.

Two independent concerns, run without a database:

1. book_sources.select_context must never fail a request just because the
   teacher's topic wording doesn't exactly match the book (typo, reworded,
   synonym) -- it should keep finding grounded pages instead of raising
   BookError("topic_not_found").
2. book_library.find_best must resolve a subject + grade pair to a real file
   in the local library folder (grade folders, subject detected from the
   messy filenames), and the book-library endpoints must expose that without
   touching the database.

Run with: .venv/Scripts/python.exe tests/test_book_library_rag.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Isolate private-source storage from whatever lives at the OS default temp
# location -- keeps this test from depending on (or polluting) real uploads.
os.environ.setdefault(
    "DASTYOR_PRIVATE_SOURCES_DIR",
    str(Path(tempfile.gettempdir()) / f"dastyor_test_sources_{os.getpid()}"),
)

FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


def make_record(pages: list[str], title: str = "Test Book") -> dict:
    return {
        "id": "test", "owner_id": "test-user", "title": title,
        "page_count": len(pages), "pages": pages, "chapters": [],
        "ocr_pages": 0, "unreadable_pages": 0,
    }


def test_fuzzy_topic_search():
    print("\n1. select_context never raises topic_not_found on wording drift")
    from app import book_sources

    pages = [
        "Параграф 1. Введение в анатомию человека, общие понятия о теле.",
        "Параграф 2. Скелет человека. Устухон ва скелети бадани инсон "
        "ташкил медиханд. Устухонхо дар бадан гуногунанд.",
        "Параграф 3. Мушакхо ва харакат. Мушак ба устухон пайваст мешавад.",
        "Параграф 4. Хазм ва ғизо. Дастгохи хазм дар бадани инсон.",
    ] * 3  # repeat so scope has >= a handful of candidate pages

    record = make_record(pages)

    def run(topic):
        return book_sources.select_context(record, "all", topic)

    exact = run("Устухон")
    check("exact topic returns pages", len(exact["used_pages"]) > 0)
    check("exact topic hits the bone paragraph", 2 in exact["used_pages"])

    typo = run("Устухан")  # one letter changed
    check("one-letter typo does not raise", True, "no exception")
    check("typo still returns pages", len(typo["used_pages"]) > 0)

    reworded = run("устухонхо дар бадан")  # topic rephrased using real words
    check("reworded topic returns pages", len(reworded["used_pages"]) > 0)
    check("reworded topic hits the bone paragraph", 2 in reworded["used_pages"])

    unrelated = run("совершенно другая неизвестная тема про космос")
    unrelated_ok = True
    try:
        run("совершенно другая неизвестная тема про космос")
    except book_sources.BookError as exc:
        unrelated_ok = str(exc) != "topic_not_found"
    check("unrelated topic never raises topic_not_found", unrelated_ok)
    check("unrelated topic still returns some context", len(unrelated["used_pages"]) > 0)

    empty = run("")
    check("empty topic still returns spread context", len(empty["used_pages"]) > 0)

    none_topic = run(None)
    check("missing topic still returns spread context", len(none_topic["used_pages"]) > 0)


def test_topic_not_found_only_on_truly_empty_scope():
    print("\n2. the old hard failure is gone; only a genuinely empty scope fails")
    from app import book_sources

    # A single page below the 20-char readability floor: no candidates at all.
    record = make_record(["x"])
    try:
        book_sources.select_context(record, "all", "anything")
        check("empty scope raises no_text", False, "expected BookError")
    except book_sources.BookError as exc:
        check("empty scope raises no_text (not topic_not_found)", str(exc) == "no_text", str(exc))


def test_book_library_matching():
    print("\n3. book_library resolves subject + grade across the real catalog")
    from app import book_library

    root = book_library.LIBRARY_ROOT.expanduser()
    if not root.exists():
        print(f"  SKIP  BOOK_LIBRARY_DIR not found on this machine: {root}")
        return

    cases = [
        ("Математика", "5 класс"), ("Биология", "9 класс"), ("Физика", "9 класс"),
        ("Русский язык", "7 класс"), ("Английский язык", "5 класс"),
        ("Алгебра", "10 класс"), ("История Таджикистана", "6 класс"),
        ("Технология", "8 класс"),
    ]
    for subject, grade in cases:
        best = book_library.find_best(subject, grade)
        check(f"{subject} / {grade} resolves to a book", best is not None,
              best["title"] if best else "no match")
        if best:
            check(f"{subject} / {grade} grade_hint matches", best["grade_hint"] == grade.split()[0])

    unknown = book_library.find_best("Не существующий предмет", "5 класс")
    check("unknown subject resolves to None, not an exception", unknown is None)

    # At grade 7+ the curriculum has no single "Математика" textbook (it
    # splits into Алгебра + Геометрия) -- find_best should fall back rather
    # than report nothing.
    math_fallback = book_library.find_best("Математика", "9 класс")
    check("Математика / 9 класс falls back to Алгебра/Геометрия",
          math_fallback is not None and math_fallback["subject"] in ("Алгебра", "Геометрия"),
          math_fallback["title"] if math_fallback else "no match")


def test_book_library_http_endpoints():
    print("\n4. /api/materials/book-library endpoints against a live running backend")
    import httpx
    from app import book_library

    root = book_library.LIBRARY_ROOT.expanduser()
    if not root.exists():
        print(f"  SKIP  BOOK_LIBRARY_DIR not found on this machine: {root}")
        return

    base = os.environ.get("DASTYOR_TEST_BASE", "http://127.0.0.1:8010")
    phone = os.environ.get("DASTYOR_TEST_PHONE", "+992900000001")
    password = os.environ.get("DASTYOR_TEST_PASSWORD", "test12345")
    try:
        login = httpx.post(f"{base}/api/auth/login", json={"phone": phone, "password": password}, timeout=10)
    except httpx.ConnectError as exc:
        print(f"  SKIP  no backend reachable at {base}: {exc}")
        return
    if login.status_code != 200:
        print(f"  SKIP  test login failed against {base} ({login.status_code}): {login.text[:200]}")
        return
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client = httpx.Client(base_url=base, headers=headers, timeout=30)

    resp = client.get("/api/materials/book-library/auto", params={"subject": "Математика", "grade": "5 класс"})
    check("auto endpoint returns 200 for a known combo", resp.status_code == 200, resp.text[:200])
    if resp.status_code == 200:
        data = resp.json()
        check("auto response has a book title", bool(data.get("book", {}).get("title")))
        check("auto response has a loaded source", bool(data.get("source", {}).get("id")))
        check("auto response has topics ready", data.get("topics", {}).get("status") == "ready",
              data.get("topics"))
        check("auto response topics is a non-empty list for this book",
              len(data.get("topics", {}).get("topics") or []) > 0)

    resp2 = client.get("/api/materials/book-library/auto", params={"subject": "Забони фаронсавӣ", "grade": "7 класс"})
    check("auto endpoint returns a clean 404 when nothing matches",
          resp2.status_code == 404 and resp2.json().get("detail") == "book_not_found",
          f"status={resp2.status_code} body={resp2.text[:200]}")

    resp3 = client.get("/api/materials/book-library", params={"subject": "Физика", "grade": "9 класс"})
    check("manual catalog list still works with a grade filter", resp3.status_code == 200, resp3.text[:200])

    if resp.status_code == 200:
        book_id = resp.json()["book"]["id"]
        resp4 = client.get(f"/api/materials/book-library/{book_id}/topics")
        check("dedicated topics endpoint returns the cached result",
              resp4.status_code == 200 and resp4.json().get("status") == "ready", resp4.text[:200])

        resp5 = client.get("/api/materials/book-library/auto", params={"subject": "Математика", "grade": "5 класс"})
        same = resp5.json().get("topics", {}).get("topics") == resp.json().get("topics", {}).get("topics")
        check("re-selecting the same book reuses the cached topics (no re-extraction)", same)


def main():
    test_fuzzy_topic_search()
    test_topic_not_found_only_on_truly_empty_scope()
    test_book_library_matching()
    test_book_library_http_endpoints()
    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED: {FAIL}")
        sys.exit(1)
    print("all book library / RAG checks passed")


if __name__ == "__main__":
    main()
