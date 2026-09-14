import ssl
import truststore

# Outbound HTTPS calls (AI provider, Google token verification) were failing
# with CERTIFICATE_VERIFY_FAILED on machines where a local proxy/antivirus
# (e.g. Avast's HTTPS scanning) re-signs TLS traffic with a certificate that
# isn't in Python's bundled `certifi` trust store, even though the OS trusts
# it. truststore verifies against the OS certificate store instead, matching
# what curl/browsers already trust on the machine.
SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
