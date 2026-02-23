enum Constants {
    static let defaultServerURL = "http://YOUR_SERVER_IP:5000"

    /// Sunucuya erişilemediğinde kullanılan yedek bitiş tarihi.
    /// Normalde tarih /api/demo-config endpoint'inden gelir.
    static let demoExpiryFallback: Date = {
        var c = DateComponents()
        c.year = 2026; c.month = 4; c.day = 20
        return Calendar.current.date(from: c) ?? .distantFuture
    }()

    static let demoExpiredMessage =
        "Demo süresi doldu. Pro versiyonu için your-contact@example.com ile iletişime geçebilirsiniz."
}
