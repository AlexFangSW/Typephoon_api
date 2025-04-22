docker run -d --rm --name postgresql \
  -p 5432:5432 \
  -e POSTGRES_USER=typephoon \
  -e POSTGRES_PASSWORD=123 \
  postgres:16 \
  -c ssl=on \
  -c ssl_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem \
  -c ssl_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
