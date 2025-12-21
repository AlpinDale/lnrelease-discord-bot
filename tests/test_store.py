from lnrelease.store import amazon, apple, book_walker, viz, yen_press


class TestAmazonStore:
    def test_equal_same_asin(self):
        url1 = "https://www.amazon.com/dp/B08EXAMPLE"
        url2 = "https://www.amazon.com/gp/product/B08EXAMPLE"
        assert amazon.equal(url1, url2)

    def test_equal_different_asin(self):
        url1 = "https://www.amazon.com/dp/B08EXAMPLE"
        url2 = "https://www.amazon.com/dp/B09DIFFERENT"
        assert not amazon.equal(url1, url2)

    def test_hash_link_consistency(self):
        url = "https://www.amazon.com/dp/B08EXAMPLE"
        h1 = amazon.hash_link(url)
        h2 = amazon.hash_link(url)
        assert h1 == h2

    def test_normalise(self):
        from lnrelease.session import Session

        session = Session()
        url = "https://www.amazon.com/Some-Book-Title/dp/B08EXAMPLE/ref=sr_1_1"
        normalized = amazon.normalise(session, url)
        assert normalized == "https://www.amazon.com/dp/B08EXAMPLE"

    def test_normalise_invalid_url(self):
        from lnrelease.session import Session

        session = Session()
        url = "https://www.amazon.com/invalid"
        normalized = amazon.normalise(session, url)
        assert normalized is None


class TestAppleStore:
    def test_equal_same_id(self):
        url1 = "https://books.apple.com/us/book/test/id1234567890"
        url2 = "https://books.apple.com/jp/book/different-title/id1234567890"
        assert apple.equal(url1, url2)

    def test_equal_different_id(self):
        url1 = "https://books.apple.com/us/book/test/id1234567890"
        url2 = "https://books.apple.com/us/book/test/id9876543210"
        assert not apple.equal(url1, url2)

    def test_hash_link_consistency(self):
        url = "https://books.apple.com/us/book/test/id1234567890"
        h1 = apple.hash_link(url)
        h2 = apple.hash_link(url)
        assert h1 == h2


class TestBookWalkerStore:
    def test_equal_same_url(self):
        url = "https://global.bookwalker.jp/de12345678-1234-1234-1234-123456789012/"
        assert book_walker.equal(url, url)

    def test_hash_link_consistency(self):
        url = "https://global.bookwalker.jp/de12345678-1234-1234-1234-123456789012/"
        h1 = book_walker.hash_link(url)
        h2 = book_walker.hash_link(url)
        assert h1 == h2


class TestVizStore:
    def test_equal_same_slug(self):
        url1 = "https://www.viz.com/manga-books/novel/test-series-volume-1/product/1234/ebook"
        url2 = "https://www.viz.com/manga-books/novel/test-series-volume-1/product/1234/ebook"
        assert viz.equal(url1, url2)

    def test_equal_different_slug(self):
        url1 = "https://www.viz.com/manga-books/novel/test-series-volume-1/product/1234/ebook"
        url2 = "https://www.viz.com/manga-books/novel/different-series/product/5678/ebook"
        assert not viz.equal(url1, url2)


class TestYenPressStore:
    def test_equal_same_slug(self):
        url1 = "https://yenpress.com/titles/9781234567890-test-series-vol-1"
        url2 = "https://yenpress.com/titles/9781234567890-test-series-vol-1?tab=info"
        assert yen_press.equal(url1, url2)

    def test_equal_different_slug(self):
        url1 = "https://yenpress.com/titles/9781234567890-test-series-vol-1"
        url2 = "https://yenpress.com/titles/9780987654321-different-book"
        assert not yen_press.equal(url1, url2)

    def test_hash_link_consistency(self):
        url = "https://yenpress.com/titles/9781234567890-test-series-vol-1"
        h1 = yen_press.hash_link(url)
        h2 = yen_press.hash_link(url)
        assert h1 == h2
