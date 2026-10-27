# Use the OS certificate store for TLS (needed behind filtering proxies such as NetFree,
# whose root CA Python 3.13+ rejects by default). Applies to httpx and the anthropic client.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass
