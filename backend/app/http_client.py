import ssl
import truststore

SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
