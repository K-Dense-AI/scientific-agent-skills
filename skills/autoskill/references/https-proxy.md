# Optional: TLS for localhost screenpipe access

Screenpipe's HTTP server (Axum, binding `localhost:3030`) speaks plain HTTP. Loopback HTTP is supported for same-host use. Keep the listener on loopback; transport encryption does not replace endpoint authentication or protect against other processes on the host.

TLS on localhost is only useful when:

- A corporate security policy mandates "TLS everywhere" regardless of transport.
- The screenpipe endpoint is tunneled or exposed off-host.
- A browser client requires a "secure context" (Service Workers, WebCrypto).

The example below keeps the proxy loopback-only. Caddy's `tls internal` creates a local CA and attempts to install it into local trust stores when permitted. Python's HTTPX may use a different trust store.

## Caddy

Install:

```bash
brew install caddy   # macOS
# or see https://caddyserver.com/docs/install
```

Add to your `Caddyfile`:

```caddyfile
screenpipe.local {
    bind 127.0.0.1
    tls internal
    reverse_proxy localhost:3030
}
```

Ensure `screenpipe.local` resolves to loopback (add to `/etc/hosts`):

```
127.0.0.1   screenpipe.local
```

Start Caddy:

```bash
caddy run
```

Then update autoskill's `config.yaml`:

```yaml
screenpipe:
  url: https://screenpipe.local
```

HTTPX verifies HTTPS by default and normally uses certifi, which may not include
Caddy's local CA. Set `SSL_CERT_FILE` to a PEM CA bundle trusted for this service
(including the Caddy root, and public roots if the same process calls a cloud LLM).
Do not disable certificate verification to work around trust errors. A Caddy
proxy bound off-host also needs access controls; TLS alone is not authorization.
The Screenpipe bearer token is still required for protected API routes.

This configuration was documentation-reviewed, not deployed during maintenance.
Sources: [Caddy local HTTPS](https://caddyserver.com/docs/automatic-https) and
[HTTPX SSL configuration](https://www.python-httpx.org/advanced/ssl/).

## mkcert (alternative)

If you prefer managing the cert yourself instead of Caddy's internal CA:

```bash
brew install mkcert
mkcert -install
mkcert localhost 127.0.0.1
```

Then terminate TLS with nginx, Caddy, or stunnel using the generated cert.
