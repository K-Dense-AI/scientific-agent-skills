# Optional: TLS for localhost screenpipe access

Screenpipe's HTTP server (Axum, binding `localhost:3030`) speaks plain HTTP. For a Python script running as the same user on the same host, plain HTTP is adequate — loopback traffic never hits a network adapter, so TLS provides no additional confidentiality.

TLS on localhost is only useful when:

- A corporate security policy mandates "TLS everywhere" regardless of transport.
- The screenpipe endpoint is tunneled or exposed off-host.
- A browser client requires a "secure context" (Service Workers, WebCrypto).

If you need it, put a one-line Caddy reverse proxy in front. Caddy's `tls internal` generates and trusts a local CA automatically.

## Caddy

Install:

```bash
brew install caddy   # macOS
# or see https://caddyserver.com/docs/install
```

Add to your `Caddyfile`:

```caddyfile
screenpipe.local {
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

No code change is required on the autoskill side. `httpx` handles both HTTP and HTTPS transparently.

## mkcert (alternative)

If you prefer managing the cert yourself instead of Caddy's internal CA:

```bash
brew install mkcert
mkcert -install
mkcert localhost 127.0.0.1
```

Then terminate TLS with nginx, Caddy, or stunnel using the generated cert.
