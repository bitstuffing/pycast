from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

# Generate our key
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,  # Consider using a larger key size for production use
)

# Write our key to disk for safe keeping
with open("key.pem", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),  # Consider using encryption for production use
    ))

# Various details about who we are. For a self-signed certificate the
# subject and issuer are always the same.
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"ES"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Madrid"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, u"Madrid"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"bitstuffing corp"),
    x509.NameAttribute(NameOID.COMMON_NAME, u"bitstuffing.github.io"),
])
cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    # Our certificate will be valid for 150 days
    datetime.datetime.utcnow() + datetime.timedelta(days=150)
).sign(key, hashes.SHA256())  # SHA-256 is a common choice for RSA

# Write our certificate out to disk.
with open("cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

